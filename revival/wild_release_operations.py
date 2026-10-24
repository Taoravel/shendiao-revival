"""Explicit frozen-release preflight/publish; never authenticate a real role."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / 'runtime/accounts.sqlite3'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_pid(pid):
    path=ROOT/'runtime/gateway.pid'
    pending=path.with_suffix('.pid.tmp')
    pending.write_text(str(pid)+'\n',encoding='ascii')
    os.replace(pending,path)


def validate(release):
    manifest = read(release / 'manifest.json')
    assert digest(release / 'run_release.py') == manifest['runner_sha256']
    for name, expected in manifest['sha256'].items():
        assert digest(release / 'source' / name) == expected, name
    return manifest


def backup(target):
    with closing(sqlite3.connect(DATABASE.as_uri() + '?mode=ro', uri=True)) as source:
        with closing(sqlite3.connect(target)) as destination:
            source.backup(destination)


def database_state(path):
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        assert db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
        tables = {}
        for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            quoted = '"' + name.replace('"', '""') + '"'
            rows = sorted(repr(tuple(row)) for row in db.execute('SELECT * FROM ' + quoted))
            tables[name] = dict(count=len(rows), sha256=hashlib.sha256('\n'.join(rows).encode()).hexdigest())
        return tables


def ps(script):
    return subprocess.check_output(['powershell', '-NoProfile', '-NonInteractive', '-Command',
        '[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new();' + script], encoding='utf-8').strip()


def listener():
    raw = ps("$c=Get-NetTCPConnection -State Listen -LocalPort 28993 -ErrorAction SilentlyContinue; "
             "if($c){$ids=@($c.OwningProcess|Sort-Object -Unique); "
             "if($ids.Count -ne 1){throw 'Ambiguous listener'}; "
             "Get-CimInstance Win32_Process -Filter ('ProcessId='+$ids[0]) | "
             "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress}; exit 0")
    return json.loads(raw) if raw else None


def health(release):
    sys.path.insert(0, str(release / 'source'))
    from wire import FrameReader, frame, read_octets
    reader = FrameReader()
    with socket.create_connection(('127.0.0.1', 28993), timeout=3) as sock:
        sock.settimeout(3)
        frames = []
        while not frames:
            data = sock.recv(4096)
            assert data, 'Server closed before challenge'
            frames.extend(reader.feed(data))
        assert frames[0][0] == 101
        challenge, offset = read_octets(frames[0][1])
        assert len(challenge) == 16
        version = struct.unpack_from('>I', frames[0][1], offset)[0]
        assert version == 601
        heartbeat = struct.pack('>I', 0x6172)
        sock.sendall(frame(100, heartbeat))
        while True:
            data = sock.recv(4096)
            assert data, 'Server closed before heartbeat'
            if (100, heartbeat) in reader.feed(data):
                break
    return dict(version=version, unauthenticated_heartbeat='passed')


def preflight(release):
    manifest = validate(release)
    copy = release / 'migration-check.sqlite3'
    backup(copy)
    before = database_state(copy)
    result = subprocess.run([sys.executable, '-B', str(release / 'run_release.py'), '--migration-check'],
                            capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    after = database_state(copy)
    assert all(after.get(name) == value for name, value in before.items()), 'Startup changed existing rows'
    report = dict(recorded_utc=datetime.now(timezone.utc).isoformat(), files=len(manifest['sha256']),
                  runner_hash_verified=True, all_source_hashes_verified=True, quick_check='ok',
                  migration_exit_code=result.returncode, preexisting_tables_preserved=len(before),
                  preexisting_rows_unchanged=True, real_database_modified=False)
    write(release / 'migration-preflight.json', report)
    return report


def publish(release, expected_pid, *, resume_stopped=False):
    manifest = validate(release)
    preflight_record = read(release / 'migration-preflight.json')
    assert preflight_record['preexisting_rows_unchanged']
    tests = read(release / 'preflight.json')
    assert tests['all_checks_passed'] and tests['standards_findings'] == tests['spec_findings'] == 0
    base = Path(manifest['base_release'])
    old_runner = base / 'run_release.py'
    current = listener()
    if resume_stopped:
        assert current is None, ('Listener reappeared',current)
        assert read(release / 'previous-deployment.json')['pid']==expected_pid
    else:
        assert current and current['ProcessId'] == expected_pid, ('Listener changed', current)
        assert str(old_runner).lower() in current['CommandLine'].lower(), ('Wrong release', current)
        established=ps("@(Get-NetTCPConnection -State Established -LocalPort 28993 -ErrorAction SilentlyContinue).Count; exit 0")
        assert int(established)==0, 'Preserve connected player; retry after disconnection'
    assert read(ROOT / 'runtime/deployment.json')['pid'] == expected_pid
    write(release / 'previous-deployment.json', read(ROOT / 'runtime/deployment.json'))
    previous_verification = ROOT / 'evidence/latest-deployment-verification.json'
    if previous_verification.exists():
        write(release / 'previous-deployment-verification.json', read(previous_verification))
    # No runtime/player commands are injected. This authorized switch stops only
    # the exact verified listener; backup occurs after it has exited.
    if not resume_stopped:
        ps(f'Stop-Process -Id {expected_pid} -ErrorAction Stop')
    child = None
    try:
        backup_path = release / 'accounts-at-stop.sqlite3'
        backup(backup_path)
        before = database_state(backup_path)
        with (release / 'server-stdout.log').open('ab') as out, (release / 'server-stderr.log').open('ab') as err:
            child = subprocess.Popen([sys.executable, '-B', str(release / 'run_release.py')],
                cwd=ROOT, stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
        for _ in range(100):
            assert child.poll() is None, (release / 'server-stderr.log').read_text(encoding='utf-8')
            deployed = ROOT / 'runtime/deployment.json'
            try:
                if deployed.exists() and read(deployed)['pid'] == child.pid:
                    result = health(release)
                    break
            except (OSError, AssertionError, json.JSONDecodeError):
                pass
            time.sleep(.2)
        else:
            raise RuntimeError('New release failed readiness')
        current = listener()
        assert current and current['ProcessId'] == child.pid
        assert str(release / 'run_release.py').lower() in current['CommandLine'].lower()
        record_pid(child.pid)
        deployed = read(ROOT / 'runtime/deployment.json')
        for name, expected in deployed['source_sha256_at_startup'].items():
            assert manifest['sha256'][name] == expected, name
        after = database_state(DATABASE)
        assert all(after.get(name) == value for name, value in before.items()), 'Existing rows changed at startup'
        report = dict(pid=child.pid, previous_pid=expected_pid, recorded_utc=datetime.now(timezone.utc).isoformat(),
            release=str(release / 'run_release.py'), source_frozen=True, design_and_catalogs_frozen=True,
            startup_hashes_match=True, manifest_files_verified=len(manifest['sha256']), **result,
            quick_check='ok', preexisting_tables_preserved=len(before), preexisting_rows_unchanged=True,
            real_roles_deleted=0, role_or_task_rewrite=False, automatic_resource_profile_migration=False,
            native_gui_verified=False, live_role_authenticated=False, backup=str(backup_path),
            gateway_pid_matches=True,
            checks='preflight.json: frozen release checks and separate Standards/Spec review',
            data_and_log_root=str(ROOT / 'runtime'))
        write(release / 'deployment-verification.json', report)
        write(previous_verification, report)
        return report
    except BaseException:
        if child is not None and child.poll() is None:
            child.terminate()
            child.wait(timeout=10)
        with (release / 'rollback-stdout.log').open('ab') as out, (release / 'rollback-stderr.log').open('ab') as err:
            restored = subprocess.Popen([sys.executable, '-B', str(old_runner)], cwd=ROOT,
                stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
        record_pid(restored.pid)
        write(release / 'rollback.json', dict(pid=restored.pid, runner=str(old_runner), database_restored=False,
            reason='New release failed verification; original persistent data retained'))
        raise


if __name__ == '__main__':
    release = Path(sys.argv[2]).resolve()
    assert release.parent == (ROOT / 'runtime/deployments').resolve()
    if sys.argv[1] == '--preflight' and len(sys.argv) == 3:
        print(json.dumps(preflight(release), ensure_ascii=False))
    elif sys.argv[1] == '--publish' and len(sys.argv) == 4:
        print(json.dumps(publish(release, int(sys.argv[3])), ensure_ascii=False))
    elif sys.argv[1] == '--resume-stopped' and len(sys.argv) == 4:
        print(json.dumps(publish(release, int(sys.argv[3]),resume_stopped=True), ensure_ascii=False))
    else:
        raise ValueError('Use --preflight RELEASE or --publish RELEASE EXPECTED_PID')

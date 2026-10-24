"""Replay the exact first-battle natural admission candidate, never a release."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--victory', action='store_true', help='Extend only the owned QA scenario with real encrypted attack/ACK commands')
    parser.add_argument('--terminal-recovery', action='store_true', help='True producer + late SQL rollback + real same-runtime disconnect/new login')
    args = parser.parse_args()
    if args.terminal_recovery and not args.victory:
        parser.error('Terminal recovery requires the actual victory driver')
    candidate = args.candidate.resolve(strict=True)
    output = args.output.resolve()
    root = Path(__file__).resolve().parents[2]
    if output.is_relative_to(candidate):
        raise ValueError('Independent output required')
    output.mkdir(parents=True, exist_ok=False)
    manifest = candidate / 'manifest.json'
    record = json.loads(manifest.read_text(encoding='utf-8'))
    before_manifest = sha(manifest)
    source, harness = candidate / 'source', candidate / 'harness'
    base = Path(record['base'])
    baseline = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
    base_record = json.loads((base / 'candidate.json').read_text(encoding='utf-8'))
    sets = ((source, record['source_sha256']), (harness, record['harness_sha256']),
            (base/'source', baseline['sha256']), (base/'harness', base_record['harness_sha256']),
            (base/'harness/workspace', base_record['workspace_sha256']))

    def verify():
        if sha(manifest) != before_manifest:
            raise ValueError('Development manifest changed')
        for directory, entries in sets:
            for name, wanted in entries.items():
                if sha(directory/name) != wanted:
                    raise ValueError('Exact frozen input differs: ' + str(directory/name))

    verify()
    resources = [root/'artres/config.pfs', root/'revival/evidence/native-image.bin']
    before_resources = {str(p): sha(p) for p in resources}
    probe = harness / 'diagnose_growth_first_battle_runtime.py'
    raw = probe.read_bytes()
    (output/probe.name).write_bytes(raw)
    executed = raw
    if args.victory:
        text = raw.decode('utf-8').replace('\r\n', '\n')
        anchor = '            started=owner.battle is not None\n'
        if text.count(anchor) != 1:
            raise ValueError('Fixed natural scenario insertion point changed')
        extension = '''            from research_battle_commands import native_action
            import battle_protocol as bp
            from progression import read_experience
            from currency import read_wallet
            with closing(store.leased(1111,role['id'],owner.epoch).connect()) as before_db:
                before_db.execute('BEGIN')
                xp_before=read_experience(before_db,1111,role['id']).experience
                wallet_before={r.currency:r.balance for r in read_wallet(before_db,1111,role['id'],owner.epoch,store.currency_rules)}
            admitted=owner.battle
            assert admitted is not None and admitted.task_ticket is not None
            battle_id=admitted.key
            command_trace=[]
            for ordinal in range(12):
                if owner.battle is None:break
                state=await admitted.call('snapshot')
                if state.phase=='commands':
                    action=await peer.request(bp.SEND_ACTION,native_action(bp.ATTACK,21))
                    command_trace.append(dict(round=state.round_number,kind='attack',reply=[hex(k) for k,_ in action]))
                elif state.phase=='playback':
                    ack=await peer.request(bp.CLIENT_PLAY_END,b'\\x00')
                    command_trace.append(dict(round=state.round_number,kind='playback_ack',reply=[hex(k) for k,_ in ack]))
                else:raise AssertionError('Unexpected natural battle phase: '+state.phase)
            assert owner.battle is None,'Actual first battle failed to finish within six real rounds'
            with closing(store.leased(1111,role['id'],owner.epoch).connect()) as win_db:
                win_db.execute('BEGIN')
                won_actor,won_state=load_task_state(win_db,1111,role['id'],owner.epoch)
                terminal_row=win_db.execute('SELECT terminal,terminal_hash,status,receipt FROM task_pve_runtime_battles WHERE role_id=? AND battle_id=?',(role['id'],battle_id)).fetchone()
                phase=win_db.execute('SELECT phase FROM task_battle_admissions WHERE role_id=? AND battle_id=?',(role['id'],battle_id)).fetchone()[0]
                xp_after=read_experience(win_db,1111,role['id']).experience
                wallet_after={r.currency:r.balance for r in read_wallet(win_db,1111,role['id'],owner.epoch,store.currency_rules)}
            assert 100107 in won_state.completed and 100107 not in won_state.active and 100179 in won_state.active
            assert phase=='won' and terminal_row[2]=='settled' and terminal_row[3]
            assert json.loads(terminal_row[0])['won'] is True
            assert xp_after-xp_before==120,(xp_before,xp_after)
            assert wallet_after['bound_silver']-wallet_before['bound_silver']==400
            real_victory=dict(battle_id=battle_id,trace=command_trace,task_completed=True,teaching_active=True,
                producer_status=terminal_row[2],terminal_hash=terminal_row[1],xp_delta=xp_after-xp_before,
                bound_silver_delta=wallet_after['bound_silver']-wallet_before['bound_silver'],
                original_terminal=json.loads(terminal_row[0]),consumer_receipt=json.loads(terminal_row[3]))
'''
        if args.terminal_recovery:
            extension=extension.replace('            command_trace=[]\n', '''            import sqlite3
            old_epoch=owner.epoch
            with closing(store.connect()) as fault_db:
                fault_db.execute("CREATE TRIGGER root_late_task_consumer BEFORE UPDATE OF phase ON task_battle_admissions WHEN NEW.phase='won' BEGIN SELECT RAISE(ABORT,'root late task consumer rollback'); END")
            command_trace=[]
''')
            extension=extension.replace("                    ack=await peer.request(bp.CLIENT_PLAY_END,b'\\x00')\n", '''                    try:ack=await peer.request(bp.CLIENT_PLAY_END,b'\\x00')
                    except sqlite3.DatabaseError:
                        command_trace.append(dict(round=state.round_number,kind='playback_ack_late_consumer_rollback'))
                        break
''')
            recovery_anchor="            assert owner.battle is None,'Actual first battle failed to finish within six real rounds'\n"
            recovery='''            assert owner.battle is not None,'Fault must leave the genuine producer awaiting consumer'
            with closing(store.leased(1111,role['id'],old_epoch).connect()) as pending_db:
                pending_db.execute('BEGIN')
                pending_row=pending_db.execute('SELECT terminal,terminal_hash,status,receipt FROM task_pve_runtime_battles WHERE role_id=? AND battle_id=?',(role['id'],battle_id)).fetchone()
                assert pending_row[2]=='terminal' and pending_row[3] is None
                assert json.loads(pending_row[0])['won'] is True
                pending_state=load_task_state(pending_db,1111,role['id'],old_epoch)[1]
                assert 100107 in pending_state.active and 100107 not in pending_state.completed
                assert read_experience(pending_db,1111,role['id']).experience==xp_before
                assert {r.currency:r.balance for r in read_wallet(pending_db,1111,role['id'],old_epoch,store.currency_rules)}==wallet_before
            close_fault=False
            try:await peer.connection.close()
            except sqlite3.DatabaseError:close_fault=True
            assert role['id'] not in runtime.roles and role['id'] not in runtime.connections
            with closing(store.connect()) as fault_db:fault_db.execute('DROP TRIGGER root_late_task_consumer')
            peer=Peer(runtime)
            await peer.login(role)
            owner=runtime.roles[role['id']]
            assert owner.epoch!=old_epoch and owner.battle is None
            with closing(store.leased(1111,role['id'],owner.epoch).connect()) as recovered_db:
                recovered_db.execute('BEGIN')
                recovered=recovered_db.execute('SELECT terminal,terminal_hash,status,receipt FROM task_pve_runtime_battles WHERE role_id=? AND battle_id=?',(role['id'],battle_id)).fetchone()
                assert recovered[:2]==pending_row[:2] and recovered[2]=='settled'
                receipt=json.loads(recovered[3])
                assert receipt['accepted_epoch']==old_epoch and receipt['consumer_epoch']==owner.epoch
            assert owner.battle is None,'Recovery must consume original terminal without opening another battle'
'''
            if extension.count(recovery_anchor)!=1:
                raise ValueError('Exact victory driver recovery insertion changed')
            extension=extension.replace(recovery_anchor,recovery)
            extension=extension.replace('consumer_receipt=json.loads(terminal_row[3]))',
                "consumer_receipt=json.loads(terminal_row[3]),real_terminal_recovery=True,late_sql_fault_verified=True,old_close_sql_fault=close_fault,original_terminal_unchanged=True)")
        text = text.replace(anchor, anchor + extension)
        text = text.replace('return dict(natural_prefix=prefix,', 'return dict(real_victory=real_victory,natural_prefix=prefix,')
        executed = text.encode('utf-8')
        (output/'extended-victory-scenario.py').write_bytes(executed)
    sys.path = [str(source), str(harness)] + [s for s in sys.path if s and not Path(s).resolve().is_relative_to(root)]
    child = output / 'natural-first-battle.json'
    sys.argv = [str(probe), '--source', str(source), '--report', str(child)]
    exec(compile(executed, str(probe), 'exec'), {'__name__':'__main__', '__file__':str(probe)})
    result = json.loads(child.read_text(encoding='utf-8'))
    if (result['level'], result['task_id'], result['private_map_id'], result['npc_id'],
        result['npc_placement_id'], result['first_battle_available'], result['task_still_active'],
        result['task_completed']) != (2,100107,1501,10908,10,True,not args.victory,args.victory):
        raise ValueError('Natural first battle admission did not pass')
    if result['isolated_new_admission_check'] is not None or result['battle_capability_enabled_by_probe']:
        raise ValueError('Natural candidate probe must not inject admission capability')
    verify()
    after_resources = {str(p): sha(p) for p in resources}
    if after_resources != before_resources:
        raise ValueError('Original client resources changed')
    origins = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.is_relative_to(root):
            if not any(path.is_relative_to(d) for d in (source,harness)) and path != Path(__file__).resolve():
                raise ValueError('Hot application import: ' + str(path))
            origins[name] = dict(path=str(path), sha256=sha(path))
    summary = dict(passed=True, scope='Natural creation-to-real-first-battle admission only',
        candidate=str(candidate), manifest_sha256=before_manifest,
        input_counts=[len(entries) for _,entries in sets], frozen_inputs_stable=True,
        resource_sha256=before_resources, actual_import_origins=origins,
        frozen_probe_sha256=sha(output/probe.name), child_report_sha256=sha(child),
        parent_runner_sha256=sha(Path(__file__)), natural_numeric_participant_injected=False,
        actual_task_battle_started=True, actual_ai_victory_verified=args.victory,
        scenario_extension='Owned test-only real encrypted attack/ACK driver; no gameplay patch' if args.victory else None,
        executed_scenario_sha256=hashlib.sha256(executed).hexdigest(),
        complete_terminal_recovery_verified=args.terminal_recovery, first_skill_teaching_verified=False,
        live_database=False, live_socket=False, listener_started=False,
        native_gui_verified=False, service_changed=False, activation_authorized=False)
    (output/'verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('passed','input_counts','actual_task_battle_started','actual_ai_victory_verified')}))


if __name__ == '__main__':
    main()

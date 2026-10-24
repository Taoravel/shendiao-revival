"""Exact candidate replay from an explicitly sealed offline role fixture only."""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import runpy
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--fixture',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case',choices=('win','recover','late-recover','source-drift','notice','defeat','paid-pet'),required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    candidate=args.candidate.resolve(strict=True)
    fixture=args.fixture.resolve(strict=True)
    output=args.output.resolve()
    if not fixture.is_relative_to(root/'evidence/fixtures') or fixture.name!='accounts.sqlite3':
        raise ValueError('Only an explicitly sealed offline QA fixture may be opened')
    if output.is_relative_to(candidate) or output.is_relative_to(fixture.parent):
        raise ValueError('Independent output required')
    output.mkdir(parents=True,exist_ok=False)
    runner=Path(__file__).resolve()
    (output/'executed-runner.py').write_bytes(runner.read_bytes())
    manifest=candidate/'manifest.json'
    record=json.loads(manifest.read_text(encoding='utf-8'))
    fixture_manifest=fixture.parent/'manifest.json'
    frozen_fixture=json.loads(fixture_manifest.read_text(encoding='utf-8'))
    if frozen_fixture['sha256']!=sha(fixture) or frozen_fixture['role_id']!=4:
        raise ValueError('Offline role fixture mismatch')
    source,harness=candidate/'source',candidate/'harness'
    if 'source_sha256' in record:
        sets=[(source,record['source_sha256']),(harness,record['harness_sha256'])]
        base=Path(record['base'])
        base_manifest=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
        base_record=json.loads((base/'candidate.json').read_text(encoding='utf-8'))
        sets.extend(((base/'source',base_manifest['sha256']),(base/'harness',base_record['harness_sha256']),
            (base/'harness/workspace',base_record['workspace_sha256'])))
    else:
        sealed=json.loads((candidate/'candidate.json').read_text(encoding='utf-8'))
        sets=[(source,record['sha256']),(harness,sealed['harness_sha256']),
            (harness,sealed['harness_resource_sha256']),(harness/'workspace',sealed['workspace_sha256'])]
    pinned={str(manifest):sha(manifest),str(fixture_manifest):sha(fixture_manifest),str(fixture):sha(fixture)}
    resources=(root.parent/'artres/config.pfs',root/'evidence/native-image.bin')
    for path in resources:pinned[str(path)]=sha(path)
    if (candidate/'candidate.json').exists():pinned[str(candidate/'candidate.json')]=sha(candidate/'candidate.json')

    def verify():
        for directory,entries in sets:
            for name,expected in entries.items():
                if sha(directory/name)!=expected:
                    raise ValueError('Frozen application input changed: '+str(directory/name))
        for name,expected in pinned.items():
            if sha(Path(name))!=expected:raise ValueError('Frozen manifest/resource/fixture changed: '+name)

    verify()
    probe=harness/'verify_task_pve_current_role.py'
    if 'verify_task_pve_current_role.py' not in dict(sets[1][1]):
        raise ValueError('Existing-role probe is not in the frozen harness')
    (output/'executed-role-scenario.py').write_bytes(probe.read_bytes())
    sys.path=[str(source),str(harness)]+[s for s in sys.path if s and not Path(s).resolve().is_relative_to(root)]
    child=output/'role-scenario.json'
    sys.argv=[str(probe),'--source',str(source),'--seed-db',str(fixture),'--role-id','4',
        '--case',args.case,'--report',str(child)]
    log=io.StringIO()
    failure=None
    try:
        with redirect_stdout(log):
            runpy.run_path(str(probe),run_name='__main__')
    except BaseException as error:
        failure=type(error).__name__+': '+str(error)
    finally:
        verify()
        (output/'stdout.txt').write_text(log.getvalue(),encoding='utf-8')
    origins={}
    for name,module in tuple(sys.modules.items()):
        filename=getattr(module,'__file__',None)
        if not filename:continue
        path=Path(filename).resolve()
        if path.is_relative_to(root):
            if not any(path.is_relative_to(d) for d in (source,harness)) and path!=runner:
                raise ValueError('Unfrozen application import: '+str(path))
            origins[name]=dict(path=str(path),sha256=sha(path))
    result=json.loads(child.read_text(encoding='utf-8')) if child.exists() else None
    if failure is None:
        if not result or result.get('source_role_task_or_profile_seeded') is not (args.case=='paid-pet'):
            raise ValueError('Copied-role versus controlled paid-pet fixture scope differs')
        if args.case in ('win','recover','late-recover'):
            if not (result['existing_role_id']==4 and result['battle_awarded_xp']==120
                    and result['battle_awarded_bound_silver']==400 and result['teaching_awarded_xp']==120
                    and result['teaching_successor']==100190 and result['native_skill_consumer_verified']
                    and result['reconnect_and_paid_preserve_current']):
                raise ValueError('Required existing-role victory/teaching/native results missing')
        elif args.case=='source-drift':
            if not all(result[k] for k in ('source_drift_refused','original_producer_pending','late_consumer_failure_rolled_back_all_assets')):
                raise ValueError('Complete source drift was not fenced')
        elif args.case=='paid-pet':
            if not all(result[k] for k in ('actual_owned_pet_participated','actual_free_pet_request',
                    'paid_reads_current_without_requiring_released_pet','controlled_owned_pet_and_uselevel_fixture')):
                raise ValueError('Released original owned pet still blocks paid current read')
        elif args.case=='defeat':
            if not all(result[k] for k in ('actual_raw_role_hp_zero','dream_recovery_to_current_caps','no_task_reward','subsequent_real_damage_preserved_on_old_paid_replay')):
                raise ValueError('Actual defeat/dream recovery/current replay not verified')
        elif not result['normal_request_has_visible_refusal']:
            raise ValueError('Current-connection refusal message missing')
    summary=dict(passed=failure is None,case=args.case,candidate=str(candidate),
        input_counts=[len(entries) for _,entries in sets],frozen_inputs_stable=True,
        pinned_input_sha256=pinned,actual_import_origins=origins,
        probe_sha256=sha(probe),parent_runner_sha256=sha(runner),failure=failure,
        child_report=str(child),child_report_sha256=sha(child) if child.exists() else None,
        fixture_only=True,actual_human_origin_copy_verified=failure is None and args.case!='paid-pet',
        controlled_owned_pet_eligibility_fixture=args.case=='paid-pet',
        actual_original_live_database_opened=False,original_live_database_written=False,
        source_role_task_or_profile_seeded=args.case=='paid-pet',native_gui_verified=False,
        live_socket=False,listener_started=False,service_changed=False,activation_authorized=False)
    (output/'verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('passed','case','input_counts','failure','fixture_only','native_gui_verified')}))
    if failure:raise SystemExit(1)


if __name__=='__main__':
    main()

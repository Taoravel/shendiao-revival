"""Replay frozen teaching/ledger contracts; no AI or shared-runtime claim."""
import argparse
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def files(directory):
    return {str(p.relative_to(directory)):sha(p) for p in directory.rglob('*') if p.is_file()}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--helper-companion',type=Path)
    parser.add_argument('--native-skill-helper',type=Path)
    parser.add_argument('--probe-reward-audit-gap',action='store_true',help='Expected RED: reproduce broken historical reward acceptance using only temporary SQL savepoints')
    parser.add_argument('--kind',choices=('first_skill','terminal_recovery','local_ledger','local_teaching'),default='first_skill')
    args=parser.parse_args()
    review=args.review.resolve(strict=True)
    base=args.base.resolve(strict=True)
    output=args.output.resolve()
    root=Path(__file__).resolve().parents[2]
    check_name={'first_skill':'verify_task_first_skill.py','terminal_recovery':'verify_task_battle_recovery.py',
        'local_ledger':'verify_local_prologue_skill_baseline.py','local_teaching':'verify_local_prologue_teaching.py'}[args.kind]
    report_name={'first_skill':'evidence/task-first-skill-verification.json',
        'terminal_recovery':'evidence/task-battle-recovery-verification.json',
        'local_ledger':'evidence/parent-local-ledger.json',
        'local_teaching':'evidence/local-prologue-teaching-verification.json'}[args.kind]
    if output.is_relative_to(review) or output.is_relative_to(base):
        raise ValueError('Independent output required')
    record=json.loads((review/'manifest.json').read_text(encoding='utf-8'))
    manifest=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
    candidate=json.loads((base/'candidate.json').read_text(encoding='utf-8'))
    companion=args.helper_companion.resolve(strict=True) if args.helper_companion else None
    companion_info=None
    companion_helpers={}
    native_helper_info=None
    if args.native_skill_helper:
        path=args.native_skill_helper.resolve(strict=True)
        fixed=json.loads((path.parent.parent/'manifest.json').read_text(encoding='utf-8'))
        if path.name!='research_other_skill_snapshot.py' or sha(path)!=fixed['files'][path.name]['source_sha256']:
            raise ValueError('Exact reviewed native-skill test helper required')
        native_helper_info=dict(path=str(path),sha256=sha(path),scope='Original OtherSkills test consumer only')
    if companion:
        companion_manifest=companion.parent.parent/'manifest.json'
        cm=json.loads(companion_manifest.read_text(encoding='utf-8'))
        if companion.name!='task_prologue_puzzle.py' or sha(companion)!=cm['files'][companion.name]['source_sha256']:
            raise ValueError('Exact reviewed helper-only companion required')
        companion_info=dict(path=str(companion),sha256=sha(companion),
            manifest=str(companion_manifest),manifest_sha256=sha(companion_manifest),
            scope='Only needed by imported DB snapshot helper; puzzle gameplay not executed')
        for name in ('verify_world_committed_transfer_read.py','verify_task_prologue_puzzle.py'):
            path=companion.parent.parent/'dependencies'/name
            wanted=cm['dependencies'][name]
            if sha(path)!=wanted:
                raise ValueError('Reviewed companion helper mismatch: '+name)
            companion_helpers[name]=dict(path=str(path),sha256=wanted)
    sets=((base/'source',manifest['sha256']), (base/'harness',candidate['harness_sha256']),
          (base/'harness/workspace',candidate['workspace_sha256']),
          (review/'inputs',record['dependencies']))
    def verify():
        if companion and (sha(companion)!=companion_info['sha256']
                or sha(Path(companion_info['manifest']))!=companion_info['manifest_sha256']):
            raise ValueError('Helper companion changed')
        if any(sha(Path(v['path']))!=v['sha256'] for v in companion_helpers.values()):
            raise ValueError('Reviewed helper source changed')
        if native_helper_info and sha(Path(native_helper_info['path']))!=native_helper_info['sha256']:
            raise ValueError('Reviewed native skill helper changed')
        for directory,expected in sets:
            for name,wanted in expected.items():
                if sha(directory/name)!=wanted:
                    raise ValueError('Frozen input changed: '+str(directory/name))
        for name,entry in record['files'].items():
            if sha(review/'source'/name)!=entry['source_sha256']:
                raise ValueError('Teaching source changed: '+name)
    verify()
    before=files(review)
    harness=output/'harness'
    own={}
    for directory,entries in ((review/'source',{n:v['source_sha256'] for n,v in record['files'].items()}),
                              (review/'inputs',record['dependencies'])):
        for name,wanted in entries.items():
            if not name.endswith('.py'):
                continue
            target=harness/name
            raw=(directory/name).read_bytes()
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and target.read_bytes()!=raw:
                raise ValueError('Conflicting frozen selected source: '+name)
            target.write_bytes(raw)
            own[name]=wanted
    if companion:
        target=harness/companion.name
        target.write_bytes(companion.read_bytes())
        own[companion.name]=companion_info['sha256']
        for name,entry in companion_helpers.items():
            target=harness/name
            target.write_bytes(Path(entry['path']).read_bytes())
            own[name]=entry['sha256']
    if native_helper_info:
        target=harness/'research_other_skill_snapshot.py'
        target.write_bytes(Path(native_helper_info['path']).read_bytes())
        own[target.name]=native_helper_info['sha256']
    # The later teaching policy is intentionally absent from the older BASE.
    # Materialize an owned config composition and leave every frozen file alone.
    config=output/'configuration'
    config_inputs={}
    for name,wanted in manifest['sha256'].items():
        if name.endswith('.py') or name==report_name:
            continue
        if Path(name).suffix.lower() in ('.db','.sqlite','.sqlite3'):
            raise ValueError('A game database is not a configuration input')
        target=config/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((base/'source'/name).read_bytes())
        config_inputs[name]=wanted
    for name,wanted in record['dependencies'].items():
        if name.startswith(('design/','catalogs/')):
            target=config/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((review/'inputs'/name).read_bytes())
            config_inputs[name]=wanted
    if 'training_battle.py' in own:
        # That frozen module resolves two startup files relative to __file__.
        # Supply exact data copies rather than altering its globals or code.
        for name in ('design/recovery-baseline.json','catalogs/knight.gsp.pet.cpetattr.json'):
            target=harness/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((config/name).read_bytes())
            own[name]=sha(target)
    sys.path=[str(harness),str(base/'source'),str(base/'harness')]+[s for s in sys.path
        if s and not Path(s).resolve().is_relative_to(root)]
    import inspect_client
    inspect_client.ROOT,inspect_client.OUT=root,config
    child=config/report_name
    scenario_adaptations=[]
    if args.kind=='local_teaching':
        for name in ('newbie-first-skill-v1.json','local-prologue-other-skills-baseline-v1.json','task-pve-ai8001-v1.json'):
            target=harness/'design'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((config/'design'/name).read_bytes())
            own['design/'+name]=sha(target)
        # Only this test's original resource root and final import audit change.
        # It still copies all selected gameplay bytes from the owned harness.
        original=(harness/check_name).read_bytes()
        (output/'original-local-teaching-check.py').write_bytes(original)
        text=original.decode('utf-8').replace('\r\n','\n')
        old='inspect_client.ROOT=workspace.parent;inspect_client.OUT=base'
        if text.count(old)!=1:
            raise ValueError('Frozen teaching test resource binding changed')
        text=text.replace(old,"inspect_client.ROOT=Path('D:/神雕侠侣');inspect_client.OUT=base")
        anchor="        result.update(candidate_sources=before,base=str(base),database='new disposable only',live_server_changed=False)"
        if text.count(anchor)!=1:
            raise ValueError('Teaching import-audit insertion point changed')
        extra="""        result['temporary_candidate_imports']={name:dict(path=str(Path(module.__file__).resolve()),sha256=h(Path(module.__file__)))
            for name,module in tuple(sys.modules.items()) if getattr(module,'__file__',None)
            and Path(module.__file__).resolve().is_relative_to(layer)}
"""
        text=text.replace(anchor,extra+anchor)
        if args.probe_reward_audit_gap:
            audit_anchor="                    changes=db.execute('SELECT total_changes()').fetchone()[0]"
            if text.count(audit_anchor)!=1:
                raise ValueError('Fixed teaching reward-audit insertion point changed')
            audit="""                    control=opening()
                    gap_cases=[]
                    for mode in ('missing_character_exp','null_character_exp_receipt'):
                        db.execute('SAVEPOINT root_reward_gap')
                        if mode=='missing_character_exp':
                            changed=db.execute("DELETE FROM task_reward_channels WHERE role_id=? AND task_id=100105 AND channel='character_exp'",(rid,)).rowcount
                        else:
                            changed=db.execute("UPDATE task_reward_channels SET receipt='null' WHERE role_id=? AND task_id=100105 AND channel='character_exp'",(rid,)).rowcount
                        assert changed==1,'Expected actual original reward receipt row'
                        accepted=False;taught=False
                        try:
                            corrupt=opening();accepted=True
                            command=decode_task_intent(C_COMMIT_SCENARIO_QUEST,struct.pack('>iQi',100179,key,0))
                            committed=complete_first_skill_transaction(db,1111,rid,epoch,resources,first,corrupt.ticket,command,inv,
                                proof=proof,location=current,generation=generation,map_generation=projection,now_ms=2001,
                                movement_state=0,baseline_policy=policy,**rewards)
                            taught=committed.skills.entries==((100008,1),)
                        except ValueError:pass
                        gap_cases.append(dict(mode=mode,menu_accepted=accepted,teaching_committed_inside_savepoint=taught))
                        db.execute('ROLLBACK TO root_reward_gap');db.execute('RELEASE root_reward_gap')
                    report.parent.mkdir(parents=True,exist_ok=True)
                    report.write_text(json.dumps(dict(expected_bug_reproduced=all(v['menu_accepted'] and v['teaching_committed_inside_savepoint'] for v in gap_cases),
                        cases=gap_cases,unmodified_control_menu_valid=True,real_engine_victory=True,
                        corruption_and_teaching_rolled_back=True,live_database=False)),encoding='utf8')
                    assert all(v['menu_accepted'] and v['teaching_committed_inside_savepoint'] for v in gap_cases),'Expected historical broken-reward bug differs'
                    raise AssertionError('Known broken-reward source accepted and taught by r1')
"""
            text=text.replace(audit_anchor,audit+audit_anchor)
            scenario_adaptations.append('Expected RED only: missing/null historical reward rows inside temporary savepoints; genuine preceding engine event unchanged')
        (harness/check_name).write_text(text,encoding='utf-8')
        own[check_name]=sha(harness/check_name)
        scenario_adaptations=['Only QA artres ROOT explicitly bound to original game root',
            'Only QA records temporary selected-source import SHA before automatic cleanup; gameplay untouched']
    spec=importlib.util.spec_from_file_location(Path(check_name).stem,harness/check_name)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    log=io.StringIO()
    try:
        with redirect_stdout(log):
            if args.kind=='local_teaching':
                sys.argv=[str(harness/check_name),'--source',str(base/'source'),'--report',str(child)]
            try:module.main()
            except AssertionError as error:
                if not args.probe_reward_audit_gap or str(error)!='Known broken-reward source accepted and taught by r1':raise
    finally:
        verify()
    (output/'stdout.txt').write_text(log.getvalue(),encoding='utf-8')
    if args.kind=='local_ledger':
        child.parent.mkdir(parents=True,exist_ok=True)
        child.write_text(json.dumps(dict(completed=True,scope='Explicit trusted-caller Permit fixture; not actual Task cohort',
            isolated_same_new_lease_current_read=True)),encoding='utf-8')
    result=json.loads(child.read_text(encoding='utf-8'))
    after=files(review)
    stable=(all(after.get(n)==h for n,h in before.items()) and all(sha(harness/n)==h for n,h in own.items())
        and all(sha(config/n)==h for n,h in config_inputs.items()))
    if args.kind=='first_skill':
        passed=(len(result['passed'])==8 and result['inputs_stable']
            and result['native_skill_consumer_verified'] and not result['actual_ai_victory_verified']
            and not result['production_reachable'] and stable)
    elif args.kind=='terminal_recovery':
        passed=(len(result['passed'])==6 and result['original_event_unchanged']
            and not result['actual_ai_executed'] and not result['real_producer_source_cas_verified']
            and result['participant_and_terminal_are_contract_fixtures'] and stable)
    elif args.kind=='local_ledger':
        passed=result['completed'] and stable
    elif args.probe_reward_audit_gap:
        passed=result['expected_bug_reproduced'] and result['corruption_and_teaching_rolled_back'] and stable
    else:
        passed=(result['real_task_pve_engine_victory'] and result['old_local_role_unknown_before_commit']
            and not result['enrollment_on_visit'] and result['original_teaching_reward']==120
            and result['original_successor']==100190 and result['late_failure_keeps_baseline_unknown']
            and result['missing_policy_creation_or_command_and_paid_reward_refused']
            and result['paid_after_later_skill_and_growth_is_pure_current']
            and not result['battle_resource_and_outbox_consumer_verified'] and stable)
    origins={}
    for name,loaded in tuple(sys.modules.items()):
        filename=getattr(loaded,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(root):
                own_main=name=='__main__' and path==Path(__file__).resolve()
                if not own_main and not any(path.is_relative_to(d) for d in (harness,base/'source',base/'harness')):
                    raise ValueError('Unapproved application import: '+str(path))
                origins[name]=dict(path=str(path),sha256=sha(path))
    summary=dict(passed=bool(passed),kind=args.kind,groups=len(result.get('passed',[args.kind])),review=str(review),
        review_sha256=before,selected_source_sha256=own,frozen_inputs_stable=stable,
        base_input_counts=[len(x) for _,x in sets[:3]],actual_import_origins=origins,
        child_report=str(child),child_report_sha256=sha(child),
        configuration_sha256=config_inputs,
        helper_only_companion=companion_info,
        helper_only_dependencies=companion_helpers,
        native_skill_helper=native_helper_info,
        scenario_adaptations=scenario_adaptations,
        temporary_candidate_imports=result.get('temporary_candidate_imports',{}),
        non_input_review_files_added=sorted(set(after)-set(before)),
        output_adapter='Unmodified write_json writes to owned config composition; gameplay code untouched',
        root_harness_sha256=sha(Path(__file__)),artificial_terminal_fixture=args.kind in ('first_skill','terminal_recovery'),
        native_skill_consumer_verified=args.kind=='first_skill',actual_ai_victory_verified=args.kind=='local_teaching',
        explicit_snapshot_version_fixture=args.kind=='local_teaching',
        actual_resource_outbox_consumer_verified=False,
        designed_local_compatibility_verified=args.kind=='local_teaching' and not args.probe_reward_audit_gap,
        expected_reward_audit_bug_reproduced=bool(args.probe_reward_audit_gap and passed),shared_runtime_wired=False,
        live_database=False,live_socket=False,service_changed=False,native_gui_verified=False)
    (output/'verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',
        encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in
        ('review_sha256','selected_source_sha256','actual_import_origins','configuration_sha256')},ensure_ascii=False))
    if not passed:
        raise SystemExit(1)


if __name__=='__main__':
    main()

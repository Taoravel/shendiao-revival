"""Run current scoped acceptance harnesses against frozen candidate code/config."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=('research_task_existing_quest.py','verify_task_master_card.py','verify_first_master_runtime.py',
    'verify_exit_initialization_runtime.py','verify_role_exit_native.py','verify_role_lifecycle_runtime.py',
    'research_first_master_dialogue_end.py','verify_master_commit_card_runtime.py',
    'verify_newbie_cart_runtime.py','verify_npc_services.py','verify_npc_depot_close.py',
    'verify_npc_pet_recovery_runtime.py','verify_npc_shop_runtime.py','verify_npc_depot_money_runtime.py',
    'verify_npc_bound_shop_runtime.py','verify_npc_bound_shop_sources.py','verify_currency_bound_shop.py',
    'verify_role_resource_healing.py','verify_npc_role_healing.py','verify_npc_role_healing_runtime.py',
    'verify_npc_role_healing_guards.py','verify_npc_transport_runtime.py')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('script',choices=SCRIPTS)
    parser.add_argument('--candidate-record',type=Path,default=ROOT/'staging/master-ready-candidate.json')
    parser.add_argument('--base-only',action='store_true')
    args=parser.parse_args();script=args.script
    record=json.loads(args.candidate_record.read_text(encoding='utf-8'))
    release=Path(record['release'])
    production=Path(record['base_release']) if args.base_only else release
    source=production/'source'
    manifest=json.loads((production/'manifest.json').read_text(encoding='utf-8'))['sha256']
    def verify():
        for name,expected in manifest.items():
            if hashlib.sha256((source/name).read_bytes()).hexdigest()!=expected:
                raise ValueError('Immutable candidate changed: '+name)
    verify()
    checks=release/'checks';checks.mkdir(exist_ok=True)
    workspace=checks/(script.removesuffix('.py')+('-base-workspace' if args.base_only else '-workspace'))
    if workspace.exists():workspace=workspace.with_name(workspace.name+'-'+str(time.monotonic_ns()))
    workspace.mkdir(exist_ok=False)
    for name in ('design','catalogs','decoded','extracted'):
        if (source/name).exists():shutil.copytree(source/name,workspace/name)
    shutil.copytree(source/'evidence',workspace/'evidence')
    for name in SCRIPTS:
        target=checks/name
        frozen_harness=Path(record.get('harness_sources',{}).get(name,ROOT/name))
        if not target.exists():shutil.copy2(frozen_harness,target)
    # Only verification/research harnesses live in checks. Prefer their frozen
    # updated helpers over obsolete verifiers inherited from the live baseline;
    # all production modules are still required to resolve inside source.
    sys.path[:0]=[str(checks),str(source)]
    import inspect_client
    inspect_client.ROOT=ROOT.parent
    inspect_client.OUT=workspace
    sys.argv=[str(checks/script)]
    try:runpy.run_path(str(checks/script),run_name='__main__')
    except SystemExit as error:
        if error.code not in (None,0):raise
    modules={name:str(sys.modules[name].__file__) for name in
        ('task_master_card','task_cart_dialogue','game_runtime','runtime_storage','npc_services','npc_gameplay',
         'npc_shop_payments','currency','npc_role_healing','role_resource_plan') if name in sys.modules}
    for path in modules.values():
        if Path(path).parent!=source:raise ValueError('Acceptance used current workspace runtime')
    verify()
    result={'script':script,'passed':True,'production_modules':modules,'configuration':str(workspace),
        'configuration_copied_from':str(source),'candidate_hashes_preserved':len(manifest),
        'live_server_changed':False,'native_gui_verified':False}
    (checks/(script+'.result.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()

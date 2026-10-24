"""Exact-input query review: two actual REDs, public reader and original Peer."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import sys
from unittest.mock import patch


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('check');parser.add_argument('--label',required=True)
    args=parser.parse_args();review=Path(__file__).resolve().parent
    manifest=json.loads((review/'manifest.json').read_text(encoding='utf8'))
    assert args.check in manifest['checks'] and args.label.replace('_','').isalnum()
    def verify():
        for name,digest in manifest['local_inputs'].items():assert sha(review/name)==digest,name
        for name,digest in manifest['external_inputs'].items():assert sha(Path(name))==digest,name
    verify();output=review/'verification'/args.label/args.check
    assert not output.exists(),'Use a new label';output.mkdir(parents=True)
    root=Path(manifest['workspace_root']);release=Path(manifest['release']);passed=False;origins={};detail={}
    try:
        if args.check!='legacy_sale_runtime':
            label='review_buyback_'+args.label+'_'+args.check
            command=[sys.executable,'-X','utf8','-B',str(review/'current/staging/verify_npc_buyback_query.py'),
                '--workspace-root',str(root),'--label',label]
            module=review/'current/npc_shop_sales.py'
            if args.check=='bad_record_red':module=review/'prototypes/npc_shop_sales_bad_record.py'
            if args.check!='missing_query_red':command+=['--npc-module',str(module)]
            result=subprocess.run(command,capture_output=True,text=True,encoding='utf8',timeout=100)
            (output/'stdout.txt').write_text(result.stdout,encoding='utf8')
            (output/'stderr.txt').write_text(result.stderr,encoding='utf8')
            probe_report=root/'evidence/npc-buyback-query-verification'/label/'result.json'
            record=json.loads(probe_report.read_text(encoding='utf8'))
            if args.check=='missing_query_red':
                assert result.returncode==1 and "has no attribute 'plan_query'" in result.stderr
                assert not record['passed']
            elif args.check=='bad_record_red':
                assert result.returncode==1 and 'argument after ** must be a mapping, not list' in result.stderr
                assert not record['passed']
            else:
                assert result.returncode==0,result.stdout+result.stderr
                assert record['passed'] and len(record['checked'])==13
                assert record['candidate_sha256']==manifest['scope']['npc_shop_sales.py']['current_sha256']
            assert record['probe_sha256']==sha(review/'current/staging/verify_npc_buyback_query.py')
            detail=dict(actual_probe_exit=result.returncode,probe_result=str(probe_report),
                probe_result_sha256=sha(probe_report),feature_pass_claimed=args.check=='readonly_query')
            origins=record['actual_project_module_origins']
        else:
            source,harness=release/'source',release/'harness';sys.path[:0]=[str(harness),str(source)]
            import inspect_client
            inspect_client.ROOT,inspect_client.OUT=root.parent,harness/'workspace'
            module=review/'current/npc_shop_sales.py'
            spec=importlib.util.spec_from_file_location('npc_shop_sales',module)
            imported=importlib.util.module_from_spec(spec);sys.modules['npc_shop_sales']=imported;spec.loader.exec_module(imported)
            script=harness/'verify_npc_sale_runtime.py';original_write=Path.write_text
            def sink(path,data,*values,**keywords):
                if path.parent==inspect_client.OUT/'evidence' and path.suffix=='.json':
                    return original_write(output/path.name,data,*values,**keywords)
                assert not path.is_relative_to(release),str(path)
                return original_write(path,data,*values,**keywords)
            sys.argv=[str(script)]
            with patch.object(Path,'write_text',sink):runpy.run_path(str(script),run_name='__main__')
            for name,loaded in tuple(sys.modules.items()):
                if name=='__main__':continue
                file=getattr(loaded,'__file__',None)
                if file and Path(file).resolve().is_relative_to(root):
                    actual=Path(file).resolve()
                    assert actual.parent in (source,harness) or (name=='npc_shop_sales' and actual==module),str(actual)
                    origins[name]=str(actual)
            detail=dict(original_exact_published_Peer_fixture=True,feature_pass_claimed=True)
        passed=True
    finally:
        verify()
        result=dict(check=args.check,passed=passed,fixed_local_inputs=len(manifest['local_inputs']),
            fixed_external_inputs=len(manifest['external_inputs']),details=detail,actual_project_module_origins=origins,
            display_debit_policy_changed=False,shared_or_service_or_real_database_or_GUI_changed=False)
        (output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PASS frozen buyback query:',args.check,args.label)


if __name__=='__main__':main()

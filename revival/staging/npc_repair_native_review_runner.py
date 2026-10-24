"""Run the immutable current-provider probe under a fixed two-axis review."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True)
    parser.add_argument('--red',action='store_true');args=parser.parse_args()
    assert args.label.replace('_','').isalnum()
    review=Path(__file__).resolve().parent
    manifest=json.loads((review/'manifest.json').read_text(encoding='utf8'))
    def verify():
        for name,digest in manifest['local_inputs'].items():assert sha(review/name)==digest,name
        for name,digest in manifest['external_inputs'].items():assert sha(Path(name))==digest,name
    verify()
    check='native_red' if args.red else 'native_messages'
    output=review/'verification'/args.label/check
    assert not output.exists(),'Preserve previous runs';output.mkdir(parents=True)
    label='native_r2_'+args.label+('_red' if args.red else '_green')
    command=[sys.executable,'-X','utf8','-B',str(review/'current/staging/run_npc_repair_native_check.py'),
        '--workspace-root',manifest['workspace_root'],'--label',label,
        '--probe',str(review/'current/staging/verify_npc_repair_native_messages.py'),
        '--npc-module',str(review/('base/npc_repairs.py' if args.red else 'current/npc_repairs.py'))]
    if args.red:command.append('--expect-red')
    result=subprocess.run(command,capture_output=True,text=True,encoding='utf8',timeout=180)
    (output/'stdout.txt').write_text(result.stdout,encoding='utf8')
    (output/'stderr.txt').write_text(result.stderr,encoding='utf8')
    verify()
    report=dict(check=check,passed=result.returncode==0,red_feature_pass_claimed=False,
        fixed_local_inputs=len(manifest['local_inputs']),fixed_external_inputs=len(manifest['external_inputs']),
        command=command,actual_exit_code=result.returncode,
        original_probe_result=str(Path(manifest['workspace_root'])/'evidence/npc-repair-native-verification'/label/'result.json'),
        service_or_real_database_or_GUI_access=False)
    (output/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    assert result.returncode==0,result.stdout+result.stderr
    print('PASS frozen current-native repair:',check,args.label)


if __name__=='__main__':main()

"""Two real processes: published paid receipt, then selected repair/Asset read.

Every label is append-only; actual RED is retained separately from positive runs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workspace-root',type=Path,default=ROOT)
    parser.add_argument('--probe',type=Path)
    parser.add_argument('--label',required=True)
    parser.add_argument('--npc-module',type=Path)
    parser.add_argument('--expect-red',action='store_true')
    args=parser.parse_args();root=args.workspace_root.resolve()
    assert args.label.replace('_','').isalnum()
    probe=(args.probe or root/'staging/verify_npc_repair_native_messages.py').resolve()
    context=root/'staging/npc-repair-native-context-v1/context'
    seed=root/'evidence/reviews/npc-repair-columns-20261024-r1/current/staging/verify_npc_repair_column_candidate.py'
    output=root/'evidence/npc-repair-native-verification'/args.label
    assert not output.exists(),'Use a fresh label to preserve previous evidence'
    output.mkdir(parents=True)
    tracked=(probe,seed,context.parent/'manifest.json')+((args.npc_module.resolve(),) if args.npc_module else ())
    hashes={str(path):sha(path) for path in tracked}
    common=[sys.executable,'-X','utf8','-B']
    steps=[]
    def run(name,command):
        result=subprocess.run(common+list(map(str,command)),capture_output=True,text=True,encoding='utf8',timeout=120)
        (output/(name+'.stdout.txt')).write_text(result.stdout,encoding='utf8')
        (output/(name+'.stderr.txt')).write_text(result.stderr,encoding='utf8')
        steps.append(dict(name=name,command=common+list(map(str,command)),exit_code=result.returncode))
        return result
    result=run('legacy',[seed,'--workspace-root',root,'--phase','legacy',
        '--database',output/'disposable.sqlite3','--report',output/'legacy.json'])
    assert result.returncode==0,result.stdout+result.stderr
    command=[probe,'--workspace-root',root,'--context',context,'--database',output/'disposable.sqlite3',
        '--report',output/'candidate.json']
    if args.npc_module:command+=['--npc-module',args.npc_module.resolve()]
    result=run('candidate',command)
    if args.expect_red:
        passed=result.returncode!=0 and "unexpected keyword argument 'equipment_messages'" in result.stderr
    else:passed=result.returncode==0
    for name,digest in hashes.items():assert sha(Path(name))==digest,name
    report=dict(passed=passed,expected_red=args.expect_red,feature_pass_claimed=passed and not args.expect_red,
        inputs_sha256=hashes,steps=steps,live_database_or_service_or_GUI_access=False)
    (output/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    assert passed,result.stdout+result.stderr
    print('PASS actual missing-provider RED' if args.expect_red else 'PASS public NPC/native provider check',args.label)


if __name__=='__main__':main()

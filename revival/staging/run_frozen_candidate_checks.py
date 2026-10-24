"""Run only the sealed candidate's named checks, recording complete diagnostics."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('record',type=Path)
    args=parser.parse_args()
    record=json.loads(args.record.read_text(encoding='utf-8'))
    release=Path(record['release']);logs=release/'check-logs';logs.mkdir(exist_ok=True)
    checker=Path(__file__).with_name('check_private_story_release.py')
    def run(name):
        report=release/'checks'/(name+'.result.json')
        if report.exists() and json.loads(report.read_text(encoding='utf-8')).get('passed'):
            return name,0,'already passed'
        command=[sys.executable,'-B',str(checker),name,'--candidate-record',str(args.record.resolve())]
        try:
            result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=1200)
            (logs/(name+'.txt')).write_bytes(result.stdout)
            return name,result.returncode,result.stdout.decode('utf-8',errors='replace')[-1000:]
        except subprocess.TimeoutExpired as error:
            (logs/(name+'.txt')).write_bytes(error.stdout or b'')
            return name,-1,'timeout'
    results=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(run,name) for name in record['checks_required']]
        for future in as_completed(futures):
            name,code,tail=future.result();results.append(dict(script=name,returncode=code,tail=tail))
            print(json.dumps(dict(script=name,returncode=code,tail=tail if code else None)),flush=True)
    (release/'check-run-summary.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    if any(row['returncode'] for row in results):raise SystemExit(1)


if __name__=='__main__':main()

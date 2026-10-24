"""Independent exact candidate acceptance; redirect only external report sinks."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('script',choices=('verify_npc_loyalty_quote.py','verify_npc_loyalty_quote_runtime.py'))
    parser.add_argument('--candidate-record',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    record=json.loads(args.candidate_record.read_text(encoding='utf8'))
    release=Path(record['release']);base=Path(record['base_release'])
    manifest=json.loads((release/'manifest.json').read_text(encoding='utf8'))['sha256']
    original=json.loads((base/'manifest.json').read_text(encoding='utf8'))['sha256']
    changed={name for name in manifest if original.get(name)!=manifest[name]}
    assert changed=={'npc_recovery.py','runtime_storage.py','design/npc-pet-loyalty-v2.json'}
    assert not set(original)-set(manifest)
    ready=json.loads((root/'evidence/npc-pet-loyalty-v2-ready.json').read_text(encoding='utf8'))
    assert all(manifest[name]==digest for name,digest in ready['production_inputs'].items())
    source=(base/'source/runtime_storage.py').read_bytes()
    newline=b'\r\n' if b'\r\n' in source else b'\n'
    guard=(b'    if intent.kind!=1:'+newline+
        b"        _require_unmigrated_operation(accounts,inventory,'Pet recovery awaits inventory resource-source integration')"+newline)
    assert source.count(guard)==1
    assert source.replace(guard,b'')==(release/'source/runtime_storage.py').read_bytes()
    output=root/'evidence/npc-loyalty-candidate-owner-20261024'
    output.mkdir(exist_ok=True)
    checker=root/'staging/check_private_story_release.py'
    original_write=Path.write_text
    evidence=release/'harness/workspace/evidence'
    reports={evidence/'npc-loyalty-quote-verification.json',evidence/'npc-loyalty-quote-runtime.json'}
    def write_report(path,data,*arguments,**keywords):
        if path.parent==release/'checks' or path in reports:
            return original_write(output/path.name,data,*arguments,**keywords)
        if path.is_relative_to(release):raise AssertionError('Attempt to modify frozen candidate: '+str(path))
        return original_write(path,data,*arguments,**keywords)
    sys.argv=[str(checker),args.script,'--candidate-record',str(args.candidate_record)]
    with patch.object(Path,'write_text',write_report):
        runpy.run_path(str(checker),run_name='__main__')
    result=json.loads((output/(args.script+'.result.json')).read_text(encoding='utf8'))
    assert result['passed']
    summary=dict(exact_base=str(base),exact_release=str(release),script=args.script,
        changed_inputs={name:manifest[name] for name in sorted(changed)},removed_inputs=[],
        shared_delta='only two pet guard lines; all other bytes and repair gate preserved',
        acceptance_input_sha256=record['acceptance_input_sha256'],
        production_and_harness_preserved=True,output_sinks_only_redirected=True,
        real_database_opened=False,live_server_changed=False,native_gui_verified=False)
    (output/(args.script+'.owner.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    print('PASS independent exact three-input candidate:',args.script)


if __name__=='__main__':main()

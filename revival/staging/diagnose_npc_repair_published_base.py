"""Run the same single-owner repair probe against immutable published imports."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--release',default='npc-loyalty-20261023T193742Z')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    if Path(args.release).name!=args.release:raise ValueError('Exact release directory name required')
    release=root/'runtime/deployments'/args.release
    record=json.loads((release/'candidate.json').read_text(encoding='utf8'))
    source,harness=release/'source',release/'harness'
    manifest=json.loads((release/'manifest.json').read_text(encoding='utf8'))['sha256']
    def verify():
        for name,digest in manifest.items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest,name
        for name,digest in record['harness_sha256'].items():assert hashlib.sha256((harness/name).read_bytes()).hexdigest()==digest,name
        for name,digest in record.get('harness_resource_sha256',{}).items():assert hashlib.sha256((harness/name).read_bytes()).hexdigest()==digest,name
        for name,digest in record['workspace_sha256'].items():assert hashlib.sha256((harness/'workspace'/name).read_bytes()).hexdigest()==digest,name
    verify();sys.path[:0]=[str(harness),str(source)]
    import inspect_client
    inspect_client.ROOT=root.parent;inspect_client.OUT=harness/'workspace'
    output=root/'evidence/npc-repair-published-base-diagnosis-20261024'/release.name
    output.mkdir(parents=True,exist_ok=True)
    frozen_probe=output/'verify_npc_repair_resource_runtime.py'
    probe_bytes=(root/frozen_probe.name).read_bytes()
    if frozen_probe.exists():assert frozen_probe.read_bytes()==probe_bytes,'Preserve previous frozen diagnostic'
    else:frozen_probe.write_bytes(probe_bytes)
    original_write=Path.write_text
    def sink(path,data,*args,**kwargs):
        if path.parent==harness/'workspace/evidence' and path.name.startswith('npc-repair-resource-runtime-'):
            return original_write(output/path.name,data,*args,**kwargs)
        if path.is_relative_to(release):raise AssertionError('Unexpected frozen release write: '+str(path))
        return original_write(path,data,*args,**kwargs)
    failure=None
    try:
        with patch.object(Path,'write_text',sink):runpy.run_path(str(frozen_probe),run_name='__main__')
    except (ValueError,AssertionError) as error:failure=str(error)
    finally:verify()
    origins={}
    for name,module in tuple(sys.modules.items()):
        file=getattr(module,'__file__',None)
        if not file or name=='__main__':continue
        path=Path(file).resolve()
        if root in path.parents:
            assert path.parent in (source,harness),str(path)
            origins[name]=str(path)
    assert failure=='repair resource contract awaits its receipt-aware Interface',failure
    report={'published_base':str(release),'failure':failure,'production_inputs_preserved':len(manifest),
        'harness_inputs_preserved':len(record['harness_sha256']),
        'harness_resources_preserved':len(record.get('harness_resource_sha256',{})),
        'actual_config_inputs_preserved':len(record['workspace_sha256']),
        'project_module_origins':origins,'probe_sha256':hashlib.sha256((root/'verify_npc_repair_resource_runtime.py').read_bytes()).hexdigest(),
        'output_sinks_only_redirected':True,'live_database_modified':False,'live_server_changed':False}
    (output/'diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('REPRODUCED exact published BASE NPC repair gate:',failure)


if __name__=='__main__':main()

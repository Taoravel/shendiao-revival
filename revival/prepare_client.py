"""Prepare a fully copied client, with a loopback-only server list."""
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
from inspect_client import ROOT, OUT, sha256, write_json


def main():
    baseline = json.loads((OUT / 'evidence/original-manifest.json').read_text(encoding='utf-8'))
    target = OUT / 'runtime/client'
    if target.exists():
        raise SystemExit('Runtime already exists; refusing to overwrite it')
    for name, metadata in baseline.items():
        source = ROOT / name
        if sha256(source) != metadata['sha256']:
            raise SystemExit(f'Original changed: {name}')
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    config = ET.Element('root')
    area = ET.SubElement(config, 'area', name='本地复原', desc='登录协议尚在恢复')
    ET.SubElement(area, 'server', servername='本地测试', ip='127.0.0.1', ip2='127.0.0.1', port='28993', portnum='1', desc='尚未实现登录服务', mainserver='', mainarea='本地复原')
    ET.ElementTree(config).write(target / 'cfg/serverconfig.xml', encoding='utf-8', xml_declaration=True)
    write_json(OUT / 'evidence/runtime-preparation.json', {
        'copied_original_files': len(baseline), 'hardlinks_used': False,
        'modified_copy_files': ['cfg/serverconfig.xml'], 'runtime': str(target),
        'server_implemented': False})
    print(str(target))


if __name__ == '__main__':
    main()

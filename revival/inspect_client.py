"""Inventory and recover original client data. Never launch game executables."""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from pfs import PfsArchive
from bxml import decode

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'revival'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def tree_record(element):
    return {'tag': element.tag, 'attributes': dict(element.attrib),
            'text': element.text, 'tail': element.tail,
            'children': [tree_record(child) for child in element]}


def catalog_rows(root):
    return [{'attributes': dict(child.attrib),
             'lists': {part.tag: [n.text for n in part] for part in child},
             'children': [tree_record(part) for part in child]} for child in root]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-all', action='store_true', help='CRC-check every payload in all nine archives')
    args = parser.parse_args()
    originals = sorted(p for p in ROOT.rglob('*') if p.is_file() and OUT not in p.parents)
    manifest = OUT / 'evidence/original-manifest.json'
    current = {str(p.relative_to(ROOT)): {'size': p.stat().st_size, 'sha256': sha256(p)} for p in originals}
    if manifest.exists():
        baseline = json.loads(manifest.read_text(encoding='utf-8'))
        changed = [name for name, meta in baseline.items() if current.get(name) != meta]
        if changed:
            raise SystemExit(f'Original files differ from preserved baseline: {changed}')
    else:
        baseline = current
        write_json(manifest, baseline)
    summary = {'archives': [], 'bxml_decoded': 0, 'xml_plain': 0, 'decode_failures': [], 'catalogs': {}}
    for path in sorted((ROOT / 'artres').glob('*.pfs')):
        archive = PfsArchive(path)
        entries = []
        verified = 0
        for name, entry in archive.entries.items():
            metadata = asdict(entry)
            del metadata['raw_name']
            entries.append(metadata)
            if name.endswith('/'):
                if args.verify_all:
                    archive.read(name)
                    verified += 1
                continue
            needed = path.name == 'config.pfs' or name.lower().endswith(('.xml', '.xsd', '.sxml'))
            if not (needed or args.verify_all):
                continue
            data = archive.read(name)
            verified += 1
            if path.name == 'config.pfs':
                target = OUT / 'extracted/config' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            if not name.lower().endswith(('.xml', '.xsd', '.sxml')):
                continue
            try:
                root = decode(data)
                ET.indent(root)
                target = OUT / 'decoded' / path.stem / name
                target.parent.mkdir(parents=True, exist_ok=True)
                ET.ElementTree(root).write(target, encoding='utf-8', xml_declaration=True)
                # Ensure generated XML is valid, including mixed text nodes.
                ET.parse(target)
                key = 'bxml_decoded' if data.startswith(bytes.fromhex('89abcdef')) else 'xml_plain'
                summary[key] += 1
                if path.name == 'config.pfs' and name.startswith('autoconfig/'):
                    rows = catalog_rows(root)
                    write_json(OUT / 'catalogs' / (Path(name).stem + '.json'), rows)
                    summary['catalogs'][name] = len(rows)
            except (ValueError, ET.ParseError, UnicodeError) as error:
                summary['decode_failures'].append({'archive': path.name, 'name': name, 'error': str(error)})
        write_json(OUT / 'evidence' / (path.stem + '-index.json'), entries)
        summary['archives'].append({'name': path.name, 'entries': len(entries), 'size': path.stat().st_size, 'expanded_size': sum(e.size for e in archive.entries.values()), 'verified': verified})
        print(f'{path.name}: {len(entries)} entries, {verified} CRC checked', flush=True)
    changed = [name for name, meta in baseline.items() if sha256(ROOT / name) != meta['sha256']]
    summary['original_files'] = len(baseline)
    summary['original_changed'] = changed
    write_json(OUT / 'evidence/inspection.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('archives', 'catalogs', 'decode_failures')}, ensure_ascii=False))
    print(f"decode failures: {len(summary['decode_failures'])}; catalogs: {len(summary['catalogs'])}")
    if changed:
        raise SystemExit('Original files changed during inspection')


if __name__ == '__main__':
    main()

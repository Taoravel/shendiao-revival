"""Recover native CEGUI layout descriptions for inspection, without launching."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from pfs import PfsArchive
from bxml import decode
from inspect_client import ROOT, OUT, write_json


def main():
    archive = PfsArchive(ROOT / 'artres/ui.pfs')
    decoded, errors = 0, []
    for name in archive.entries:
        if Path(name).suffix not in {'.layout', '.imageset', '.font', '.looknfeel', '.scheme'}:
            continue
        try:
            root = decode(archive.read(name))
            ET.indent(root)
            target = OUT / 'decoded/ui' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            ET.ElementTree(root).write(target, encoding='utf-8', xml_declaration=True)
            ET.parse(target)
            decoded += 1
        except (ValueError, ET.ParseError, UnicodeError) as error:
            errors.append({'file': name, 'error': str(error)})
    report = {'decoded': decoded, 'errors': errors}
    write_json(OUT / 'evidence/ui-recovery.json', report)
    print(json.dumps(report))


if __name__ == '__main__':
    main()

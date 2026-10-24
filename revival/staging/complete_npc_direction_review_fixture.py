"""Preserve R1's missing historical fixture failure and create a complete R2."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'evidence/reviews/npc-placement-direction-20261024-r1'
NEW = ROOT / 'evidence/reviews/npc-placement-direction-20261024-r2'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    record = json.loads((OLD / 'manifest.json').read_text(encoding='utf8'))
    assert not NEW.exists()
    for name, digest in record['files'].items():
        source, target = OLD / name, NEW / name
        assert sha(source) == digest, name
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix in ('.bin', '.pfs'):
            target.hardlink_to(source)
        else:
            shutil.copy2(source, target)
    fixture = ROOT / 'design/npc-interaction-v1.json'
    target = NEW / 'current/revival/design/npc-interaction-v1.json'
    assert not target.exists()
    shutil.copy2(fixture, target)
    record['files'][str(target.relative_to(NEW)).replace('\\', '/')] = sha(fixture)
    record['supersedes'] = dict(review=str(OLD), reason='Missing historical v1 interaction test fixture; unchanged production and test scope',
        failed_check='verify_npc_lifecycle_rules.py', added_fixture_sha256=sha(fixture))
    for name, digest in record['files'].items():
        assert sha(NEW / name) == digest, name
    (NEW / 'manifest.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('R2 fixed inputs:', len(record['files']), 'unchanged scope:', record['scope'])


if __name__ == '__main__':
    main()

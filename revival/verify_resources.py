"""Independent standard-ZIP comparison and fault probes on disposable copies."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pfs import PfsArchive
from bxml import decode

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / 'artres/config.pfs'
    archive = PfsArchive(path)
    data = bytearray(path.read_bytes())
    # Translate signatures at structurally identified headers only.
    for entry in archive.entries.values():
        data[entry.offset:entry.offset+4] = b'PK\x03\x04'
    end = len(data) - 22
    offset = struct.unpack_from('<I', data, end + 16)[0]
    for _ in archive.entries:
        assert data[offset:offset+4] == b'PFSF'
        data[offset:offset+4] = b'PK\x01\x02'
        nl, el, cl = struct.unpack_from('<3H', data, offset + 28)
        offset += 46 + nl + el + cl
    assert offset == end
    data[end:end+4] = b'PK\x05\x06'
    compared = 0
    faults = []
    with tempfile.TemporaryDirectory(prefix='sdxl-resource-verify-') as temp:
        translated = Path(temp) / 'config.zip'
        translated.write_bytes(data)
        with zipfile.ZipFile(translated) as oracle:
            for info, entry in zip(oracle.infolist(), archive.entries.values(), strict=True):
                if entry.name.endswith('/'):
                    continue
                expected = oracle.read(info)
                assert expected == archive.read(entry.name)
                compared += 1
        source = path.read_bytes()
        candidate = next(e for e in archive.entries.values() if e.stored > 30 and not e.name.endswith('/'))
        corrupt = bytearray(source)
        nl, el = struct.unpack_from('<HH', corrupt, candidate.offset + 26)
        corrupt[candidate.offset + 30 + nl + el + candidate.stored // 2] ^= 1
        broken = Path(temp) / 'broken.pfs'
        broken.write_bytes(corrupt)
        try:
            PfsArchive(broken).read(candidate.name)
        except (ValueError, __import__('zlib').error):
            faults.append('payload corruption rejected')
        else:
            raise AssertionError('Corrupt payload accepted')
        assert PfsArchive(ROOT / 'artres/3deffect.pfs').read('buff/') == b''
        faults.append('zero-byte deflate directory accepted')
        name = 'autoconfig/knight.gsp.role.schoolinfo.xml'
        original = archive.read(name)
        for altered in (original[:-1], original + b'\0'):
            try:
                decode(altered)
            except ValueError:
                faults.append('truncated/trailing BXML rejected')
            else:
                raise AssertionError('Invalid BXML accepted')
    result = {'config_payloads_compared_to_python_zipfile': compared, 'fault_probes': faults,
              'bxml_native_semantics_verified': False,
              'config_sha256': hashlib.sha256(source).hexdigest()}
    target = ROOT / 'revival/evidence/resource-verification.json'
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()

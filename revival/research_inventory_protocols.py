"""Index native item/pet protocol entrypoints; mapping is not implementation."""
import hashlib
import re
from collections import Counter
from native_inspect import DATA, BASE, vtables, u32, refs
from inventory import INVENTORY_TYPES
from inspect_client import OUT, write_json


def main():
    names = sorted(set(re.findall(rb'\.\?AV[CS][^\0]{1,110}@(?:item|pet)@gsp@knight@@\0', DATA)))
    rows = []
    for raw in names:
        name = raw[:-1].decode('ascii')
        if 'Table@' in name:
            continue
        tables = vtables(name)
        if not tables:
            continue
        table = tables[0]
        votes = Counter()
        for ref in list(refs(table))[:5]:
            for match in re.finditer(rb'\xc7[\x40-\x47]\x04(.{4})', DATA[ref-BASE:ref-BASE+45], re.DOTALL):
                value = int.from_bytes(match[1], 'little')
                if 0xc0000 <= value < 0xd0000:
                    votes[value] += 1
                    break
        # Four-slot data beans are not network messages.
        if not votes:
            continue
        ranked = votes.most_common()
        kind = ranked[0][0] if len(ranked) == 1 or ranked[0][1] > ranked[1][1] else None
        rows.append({'class': name, 'protocol_id': kind, 'candidate_ids': sorted(votes),
                     'vtable': hex(table), 'marshal': hex(u32(table)),
                     'unmarshal': hex(u32(table+4)), 'process': hex(u32(table+24)),
                     'domain_receive_implemented': kind in INVENTORY_TYPES if kind else False,
                     'native_ui_verified': False})
    result = {'source_sha256': hashlib.sha256(DATA).hexdigest(), 'entrypoints': rows,
              'count': len(rows), 'mapping_is_not_implementation': True}
    write_json(OUT / 'evidence/inventory-protocol-catalog.json', result)
    print('Native inventory/pet protocol entrypoints:', len(rows),
          'domain handlers:', sum(r['domain_receive_implemented'] for r in rows))


if __name__ == '__main__':
    main()

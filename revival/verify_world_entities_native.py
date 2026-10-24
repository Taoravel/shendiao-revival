"""Execute original constructors and codecs; no running game or network writes."""
import json
import struct
from pathlib import Path
import native_gameplay_probe
# Keep the shared probe unchanged. Add only the CRT memmove_s host adapter used
# by original nonempty vector insertion; all wire instructions remain original.
_source = Path(native_gameplay_probe.__file__).read_text(encoding='utf-8')
_source = _source.replace("imports[0x1919178]='alloc'", "imports[0x1919178]='alloc'\n    imports[u32(0x22448a4)]='memmove_s'")
_source = _source.replace("elif kind=='free':ret(uc)", """elif kind=='free':ret(uc)
        elif kind=='memmove_s':
            dst,capacity,src,count=read(sp+4),read(sp+8),read(sp+12),read(sp+16)
            assert count<=capacity
            if count:uc.mem_write(dst,bytes(uc.mem_read(src,count)))
            ret(uc,value=0)""")
_namespace = {}
_source = _source.replace('sp=uc.reg_read(UC_X86_REG_ESP)\n        if addr==stop',
                         'TRACE.append(addr)\n        if len(TRACE)>20:TRACE.pop(0)\n        sp=uc.reg_read(UC_X86_REG_ESP)\n        if addr==stop')
_namespace['TRACE'] = []
exec(compile(_source, native_gameplay_probe.__file__, 'exec'), _namespace)
probe = _namespace['probe']
from world_entity_protocol import NpcBasic, npc_basic, activity_npcs, remove_activity_npcs


def main():
    out = Path(__file__).parent / 'evidence'
    results = []
    # Original constructor contains a std::map head; native decoder exercises it.
    fixture = NpcBasic(0x123456789, 500001, '测试侠客', 8480, 6976,
                       7, 12, 34, 101, 102, 103, 104)
    fields = {8: struct.pack('<Q', fixture.key), 0x10: struct.pack('<i', fixture.config_id),
              0x18: fixture.name.encode('utf-16-le') + b'\0\0',
              0x28: struct.pack('<I', len(fixture.name)),
              0x34: struct.pack('<hh', fixture.x, fixture.y), 0x38: bytes([7]),
              0x40: struct.pack('<hh4i', 12, 34, 101, 102, 103, 104)}
    payload, decoded = probe(0xfc71e0, 0xfc6f70, 0xfc73a0, fields=fields)
    assert payload == npc_basic(fixture), payload.hex()
    for off in (8, 0x10, 0x34, 0x38, 0x40):
        assert decoded[off:off+len(fields[off])] == fields[off]
    results.append({'class': 'NpcBasic', 'bytes': len(payload), 'hex': payload.hex(),
                    'native_serializer': True, 'native_decoder': True})
    from world_entity_protocol import npc_screen
    # One-node std::list fixture around the separately verified native bean.
    node, head, props = 0x5001440, 0x5001400, 0x5001500
    screen_fields = {0x18: struct.pack('<II', head, 1),
                     0x400: struct.pack('<II', node, node),
                     0x440: struct.pack('<II', head, head),
                     0x448: struct.pack('<I', 0x2286850),
                     0x478: struct.pack('<I', 0x2278e54),
                     0x484: struct.pack('<I', 0x2278e54),
                     0x4a0: struct.pack('<II', props, 0),
                     0x500: struct.pack('<III', props, props, props),
                     0x515: b'\1'}
    screen_fields.update({0x448+k:v for k,v in fields.items()})
    try:
        payload, decoded = probe(0xfc5f40, 0xfc68f0, 0xfc69a0, fields=screen_fields)
    except Exception:
        print('last original addresses', [hex(a) for a in _namespace['TRACE']])
        raise
    assert payload == npc_screen((fixture,)), payload.hex()
    assert struct.unpack_from('<I', decoded, 0x1c)[0] == 1
    results.append({'class': 'SAddUserScreen-one-npc', 'hex': payload.hex(),
                    'native_serializer': True, 'native_decoder': True})
    from world_entity_protocol import remove_npc_screen
    payload, decoded = probe(0xe6e9e0, 0xe6ea90, 0xe6eb20,
                            fields={0x18: struct.pack('<II', head, 1),
                                    0x400: struct.pack('<II', node, node),
                                    0x440: struct.pack('<IIq', head, head, fixture.key)})
    assert payload == remove_npc_screen((fixture.key,))
    results.append({'class': 'SRemoveUserScreen-one-npc', 'hex': payload.hex(),
                    'native_serializer': True, 'native_decoder': True})
    # Heap fixture in object +0x400: ordinary vector and native Pos objects.
    ids, positions = (10001, 10002), ((8480, 6976), (-12, 27))
    add = activity_npcs(tuple((i, *p) for i, p in zip(ids, positions)))
    fields = {0xc: struct.pack('<III', 0x5001400, 0x5001408, 0x5001408),
              0x400: struct.pack('<ii', *ids),
              0x1c: struct.pack('<III', 0x5001420, 0x5001430, 0x5001430),
              0x420: b''.join(struct.pack('<Ihh', 0x2278e54, *p) for p in positions)}
    payload, decoded = probe(0xf0f740, 0xf0fef0, 0xf0ffa0, fields=fields)
    assert payload == add, payload.hex()
    results.append({'class': 'SAddActivityNpc', 'bytes': len(payload), 'hex': payload.hex(),
                    'native_serializer': True, 'native_decoder': True})
    payload, decoded = probe(0xe6e6c0, 0xe6e740, 0xe6e7a0,
                            fields={k:v for k,v in fields.items() if k in (0xc, 0x400)})
    assert payload == remove_activity_npcs(ids), payload.hex()
    results.append({'class': 'SRemoveActivityNpc', 'bytes': len(payload), 'hex': payload.hex(),
                    'native_serializer': True, 'native_decoder': True})
    # Nonempty property map decoded by original code (serializer tested empty).
    rich = NpcBasic(42, 500001, '甲', 1, 2, properties=((1, 88), (7, -3)))
    payload, decoded = probe(0xfc71e0, 0xfc6f70, 0xfc73a0, payload=npc_basic(rich))
    assert struct.unpack_from('<I', decoded, 0x5c)[0] == 2
    results.append({'class': 'NpcBasic-property-map', 'bytes': len(payload),
                    'native_decoder': True, 'native_serializer': False})
    from world_entity_protocol import read_visit_npc, read_npc_service
    for name, ctor, marshal, unmarshal, values in (
            ('CVisitNpc', 0xdb3450, 0xe52020, 0xdb3500, {8: struct.pack('<q', 10001)}),
            ('CNpcService', 0xdb1710, 0x83b5a0, 0x8392d0,
             {8: struct.pack('<q', 10001), 0x10: struct.pack('<i', 77)})):
        payload, decoded = probe(ctor, marshal, unmarshal, fields=values)
        if name == 'CVisitNpc': assert read_visit_npc(payload) == 10001
        else: assert read_npc_service(payload) == (10001, 77)
        results.append({'class': name, 'hex': payload.hex(),
                        'native_serializer': True, 'native_decoder': True})
    from world_entity_protocol import visit_npc_reply
    payload, decoded = probe(0xe70050, 0xe701b0, 0xe700f0,
                            fields={8: struct.pack('<q', 10001),
                                    0x14: struct.pack('<III', 0x5001400, 0x5001408, 0x5001408),
                                    0x24: struct.pack('<III', 0x5001420, 0x5001424, 0x5001424),
                                    0x400: struct.pack('<ii', 2, 3),
                                    0x420: struct.pack('<i', 77)})
    assert payload == visit_npc_reply(10001, (2, 3), (77,))
    results.append({'class': 'SVisitNpc', 'hex': payload.hex(),
                    'native_serializer': True, 'native_decoder': True})
    (out / 'world-entities-native.json').write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

"""Bounded offline SSendOtherSkills decoder/Process/consumer feedback.

Only this installation's original x86 instructions change the synthetic skill
map. Reuses research_battle's allocation/CRT adapters; no GUI, network or DB.
The integer values used below are fixtures, never approved skill grant levels.
"""
from collections.abc import Mapping
import hashlib
import json
import struct

from research_battle import NativeBattleDecoder
from native_inspect import DATA


IMAGE_SHA256 = '2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'
CONSTRUCTOR = 0xf30da0
DECODER = 0xf30e50
PROCESS = 0x12d6810
CONSUMER = 0x12d60f0
VALUE_QUERY = 0x12d1d50
MAX_ITEMS = 512


def _fixture_payload(values):
    """Encode only the initial synthetic map; caller payload is never decoded here."""
    items = tuple(sorted(values.items()))
    if len(items) > MAX_ITEMS:
        raise ValueError('Bounded offline fixture supports at most 512 skills')
    for key, value in items:
        if type(key) is not int or type(value) is not int:
            raise TypeError('Synthetic skill key/value must be signed i32 integers')
        if not (-2**31 <= key < 2**31 and -2**31 <= value < 2**31):
            raise ValueError('Synthetic skill key/value outside signed i32')
    count = bytes([len(items)]) if len(items) < 128 else struct.pack('>H', 0x8000 | len(items))
    return count + b''.join(struct.pack('>ii', key, value) for key, value in items) + b'\x01'


def _native_map(probe, container):
    """Read actual MSVC tree nodes, without predicting the consumer's result."""
    head = probe.read(container + 4)
    count = probe.read(container + 8)
    if count > MAX_ITEMS:
        raise ValueError('Native snapshot exceeds this offline probe budget')
    result = {}
    seen = set()
    pending = [probe.read(head + 4)]
    while pending:
        node = pending.pop()
        if node == head:
            continue
        if node in seen or len(seen) >= MAX_ITEMS:
            raise AssertionError('Invalid or oversized native map tree')
        seen.add(node)
        key, value = struct.unpack('<ii', probe.u.mem_read(node + 12, 8))
        if key in result:
            raise AssertionError('Duplicate key in native map tree')
        result[key] = value
        pending.extend((probe.read(node), probe.read(node + 8)))
    if len(result) != count:
        raise AssertionError('Native map tree size mismatch')
    return dict(sorted(result.items()))


def native_other_skills(payload: bytes, existing: Mapping[int, int] | None = None) -> dict[int, int]:
    """Return the actual isolated native manager's complete other-skill map.

    payload is an SSendOtherSkills body (compact map<i32,i32> + byte flag), not
    an outer frame. existing is a synthetic initial map, copied by value. Both
    the initial map and payload pass the original decoder, Process and consumer.
    Flag1 supports new/update/delete; flag0 coverage is existing-key updates and
    removals only. Flag0 new-key shortcut presentation needs another GUI fixture
    and is explicitly refused here. This function grants no real character skill.
    """
    from unicorn import UC_HOOK_CODE

    if type(payload) is not bytes or not 2 <= len(payload) <= 8192:
        raise ValueError('A bounded immutable SSendOtherSkills body is required')
    if existing is not None and not isinstance(existing, Mapping):
        raise TypeError('existing must be a mapping of synthetic i32 values')
    initial = dict(existing or {})
    initial_payload = _fixture_payload(initial)
    if hashlib.sha256(DATA).hexdigest() != IMAGE_SHA256:
        raise ValueError('Original native image differs from the researched build')
    probe = NativeBattleDecoder()
    manager = probe.allocate(0x200)
    probe.decode('SSendOtherSkills', b'\x00\x01')
    # Bootstrap an empty map with the original constructor's own sentinel. A
    # fresh constructor for each later packet prevents aliasing that sentinel.
    probe.u.mem_write(manager + 0x40, bytes(probe.u.mem_read(probe.obj + 8, 12)))
    probe.write(0x29448a4, manager)
    probe.write(0x2945610, 0)  # No shortcut/UI singleton; flag1 bypasses new-key UI.
    probe.write(0x2944564, 0)  # No live scene.
    hits = {DECODER: 0, PROCESS: 0, CONSUMER: 0}

    def record_native_call(_uc, address, _size, _user):
        if address in hits:
            hits[address] += 1

    probe.u.hook_add(UC_HOOK_CODE, record_native_call)
    probe.decode('SSendOtherSkills', initial_payload)
    probe.call(PROCESS, 0, 0)
    assert _native_map(probe, manager + 0x40) == initial
    probe.decode('SSendOtherSkills', payload)
    decoded = _native_map(probe, probe.obj + 8)
    flag = bytes(probe.u.mem_read(probe.obj + 0x14, 1))[0]
    if flag not in (0, 1):
        raise ValueError('This fixture covers only flags 0 and 1')
    if flag == 0 and decoded.keys() - initial.keys():
        raise NotImplementedError('Flag0 new-key shortcut presentation is outside this native fixture')
    probe.call(PROCESS, 0, 0)
    actual = _native_map(probe, manager + 0x40)
    packet_object = probe.obj
    try:
        probe.obj = manager
        for key in initial.keys() | decoded.keys():
            probe.call(VALUE_QUERY, key)
            value = struct.unpack('<i', struct.pack('<I', probe.u.reg_read(probe.ax)))[0]
            assert value == actual.get(key, 0), 'Native value query disagrees with native tree'
    finally:
        probe.obj = packet_object
    assert hits == {DECODER: 2, PROCESS: 2, CONSUMER: 2}, hits
    return actual


def main():
    initial = {100001: 2, 100002: 9, 100008: 7}
    complete = {100001: 2, 100002: 9, 100008: 2**31 - 1}
    missing = {100001: 2, 100008: 2**31 - 1}
    flag0 = {100001: 3, 100008: 11}
    cases = (
        ('flag1_adds_100008_without_losing_old_keys', _fixture_payload(complete), {100001: 2, 100002: 9}, complete),
        ('flag1_complete_preserves_old_and_high_value', _fixture_payload(complete), initial, complete),
        ('flag1_missing_old_key_really_deletes_it', _fixture_payload(missing), initial, missing),
        ('flag1_empty_really_clears_all', b'\x00\x01', initial, {}),
        ('flag1_identical_snapshot_keeps_values', _fixture_payload(complete), complete, complete),
        ('flag0_updates_and_removes_existing_keys', _fixture_payload(flag0)[:-1] + b'\x00', initial, flag0),
    )
    results = []
    for name, payload, before, expected in cases:
        result = native_other_skills(payload, before)
        assert result == expected, (name, result)
        results.append(dict(name=name, payload_hex=payload.hex(), before=before, actual=result))
    print(json.dumps(dict(image_sha256=IMAGE_SHA256,
        addresses={name: hex(value) for name, value in (
            ('constructor', CONSTRUCTOR), ('decoder', DECODER), ('process', PROCESS),
            ('consumer', CONSUMER), ('query', VALUE_QUERY))},
        native_cases=results, gui_verified=False, real_grant_authorized=False), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

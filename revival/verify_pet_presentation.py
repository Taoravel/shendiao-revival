"""Real pet record/refresh, original consumer math, color lookup and persistence."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import struct

from accounts import AccountStore
from inventory import Inventory, pet_record, USE_ITEM, REFRESH_PET, ADD_PET_POINT
from inventory_test_support import known_cash_context
from native_gameplay_probe import probe
from research_pet_presentation import NativePetPresentation
from inspect_client import OUT, write_json


def native_message(pet):
    body = pet_record(pet)
    _, raw = probe(0xf9d7b0, 0xf9d840, 0xf9d880, payload=body)
    return raw


def main():
    native = NativePetPresentation()
    with TemporaryDirectory() as tmp:
        store = AccountStore(Path(tmp) / 'state.sqlite3')
        role = store.create_role(1111, '召唤兽显示', 12, 1010101)
        config = Inventory.prepare(store)
        inv = Inventory(store, 1111, role['id'], config,
                        **known_cash_context(store, 1111, role['id']))
        key = inv.grant_pet(500001)
        pet = next(p for p in inv.snapshot()['pets'] if p['id'] == key)
        assert native.consume(native_message(pet)) == (1006, 1), 'Known growth/color still encoded as constructor zero'
        assert native.color_skill_slots() == 4
        # Every original positive growth tier must project back to the same raw
        # integer through both original CPU conversion paths, including 996.
        from pet_protocol import growth_wire_float
        rows = json.loads((OUT / 'catalogs/knight.gsp.pet.cpetattr.json').read_text(encoding='utf-8'))
        raw_values = sorted({int(v) for row in rows for v in row['lists'].get('growrate', ()) if int(v) >= 500})
        for raw in sorted(set(raw_values) | set(range(500, 5001))):
            value = growth_wire_float(raw)
            native.uc.mem_write(native.pet + 0x30, struct.pack('<f', value))
            assert native.growth_integer() == raw
            assert native.growth_integer(cpu_sse=False) == raw
        # Layout is independently checked against original serialization using
        # the projected scalar in its native bean field, not a fake host parser.
        for raw in (986, 996, 1006, 1256):
            progress = replace(pet['progress'], profile=replace(pet['progress'].profile, growth_raw=raw))
            displayed = dict(pet, progress=progress)
            message = native_message(displayed)
            assert native.consume(message)[0] == raw
            assert struct.unpack_from('<f', message, 8 + 0xac)[0] == growth_wire_float(raw)
        for grade, slots in ((1,4), (2,4), (3,6), (4,8), (5,10), (6,12)):
            shown = dict(pet, care=replace(pet['care'], grade=grade))
            assert native.consume(native_message(shown)) == (1006, grade)
            assert native.color_skill_slots() == slots
        # World refresh after actual feeding retains growth and color.
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            inv.change_pet_care(db, key, 'presentation:death', 0, 'defeat', 1)
        inv.grant_item(31000)
        item = inv.snapshot()['items'][0]['id']
        replies = inv.receive(USE_ITEM, struct.pack('>iiQ', item, 1, key))
        _, raw = probe(0xf9d7b0, 0xf9d840, 0xf9d880, payload=next(b for k,b in replies if k == REFRESH_PET))
        assert native.consume(raw) == (1006, 1)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            inv.change_pet_growth(db, key, 'presentation:xp', 0, 'experience', 50)
        # A controlled legacy profile whose automatic points cannot fit the
        # original signed-short fields drives the real encoder failure. No
        # inventory collaborator is replaced by a mock.
        with closing(store.connect()) as db, db:
            original_profile = db.execute('SELECT profile FROM inventory_pet_growth WHERE pet_id=?', (key,)).fetchone()[0]
            oversized_profile = json.loads(original_profile)
            oversized_profile['growth_raw'] = 2**31-1
            db.execute('UPDATE inventory_pet_growth SET profile=? WHERE pet_id=?',
                       (json.dumps(oversized_profile),key))
        before = inv.immutable_snapshot()
        try:
            inv.receive(ADD_PET_POINT, struct.pack('>6i', key, 1, 0, 0, 0, 0))
        except ValueError as exc:
            assert 'signed-short' in str(exc)
        else:
            raise AssertionError('Injected presentation error did not execute')
        assert inv.immutable_snapshot() == before, 'Point allocation committed before pet reply validation'
        with closing(store.connect()) as db, db:
            db.execute('UPDATE inventory_pet_growth SET profile=? WHERE pet_id=?', (original_profile,key))
        replies = inv.receive(ADD_PET_POINT, struct.pack('>6i', key, 1, 0, 0, 0, 0))
        _, raw = probe(0xf9d7b0, 0xf9d840, 0xf9d880, payload=next(b for k,b in replies if k == REFRESH_PET))
        assert native.consume(raw) == (1006, 1)
        reopened = Inventory(AccountStore(store.path), 1111, role['id'], config)
        current = next(p for p in reopened.snapshot()['pets'] if p['id'] == key)
        assert native.consume(native_message(current)) == (1006, 1)
        # Missing legacy knowledge remains a zero placeholder in this protocol;
        # the DB is not initialized by a display query.
        with closing(store.connect()) as db, db:
            old = db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                             (role['id'],500001,'旧未知宠')).lastrowid
        old_pet = next(p for p in inv.snapshot()['pets'] if p['id'] == old)
        assert 'care' not in old_pet and 'progress' not in old_pet
        assert native.consume(native_message(old_pet)) == (0, 0)
        for value in (True, -1, 0, 499, 2**31, 1.2, '1006'):
            try:
                growth_wire_float(value)
            except ValueError:
                pass
            else:
                raise AssertionError('Invalid raw growth encoded')
    report = {'passed': ['known growth/color no longer use native constructor zero',
        'full original Pet/SRefreshPetData decode and original field stores',
        'all original positive growth tiers and integers500..5000 survive original SSE and x87 UI math',
        '996 projection avoids nearest-float32 truncation to995',
        'six original blood-color keys select4/4/6/8/10/12 native skill-grid slots',
        'actual food and allocation refresh retain growth/color; reopen retains exact raw source',
        'pet reply encoding failure rolls allocation/version/receipt back',
        'old unknown profile/care remains uninitialized'],
        'original_growth_values_tested': raw_values, 'native_gui_tested': False,
        'skill_gameplay_restored': False, 'live_server_changed': False}
    write_json(OUT / 'evidence/pet-presentation-verification.json', report)
    print('PASS:', ', '.join(report['passed']))


if __name__ == '__main__':
    main()

"""Designed growth conservation and atomic, idempotent pet progression."""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from accounts import AccountStore
from inventory import Inventory
from inventory import pet_record
from native_gameplay_probe import probe
from research_pet_stones_native import native_pet_stones
import struct
from inspect_client import OUT, write_json


def rejects(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('Invalid pet progression accepted')


def main():
    with TemporaryDirectory() as tmp:
        store = AccountStore(Path(tmp)/'state.sqlite3')
        role = store.create_role(1111,'宠物成长',12,1010101)
        store.inventory_config = Inventory.prepare(store)
        inv = Inventory(store,1111,role['id'])
        rules = inv.growth_rules
        profile = inv.pet_profiles[500001]
        assert profile.growth_raw == 1006 and profile.aptitudes == (1130,1235,960,657,1122)
        state = rules.generate(profile)
        assert (state.hp,state.mp) == (146,62)
        for level in range(151):
            attr = rules.attributes(profile,level)
            total = sum(attr.five_stats)-50+attr.potential
            assert total == profile.growth_raw*level//100
        total_xp = sum(rules.thresholds[i] for i in range(150))
        capped = rules.award(profile,state,total_xp+123)
        assert (capped.level,capped.experience) == (150,123)
        state1 = rules.award(profile,state,50)
        assert (state1.level,state1.experience) == (1,0)
        allocated = rules.allocate(profile,state1,(5,0,0,0,0))
        assert rules.attributes(profile,1,allocated.allocated).potential == 0
        rejects(lambda: rules.allocate(profile,allocated,(1,0,0,0,0)))
        rejects(lambda: rules.award(profile,state,-1))
        rejects(lambda: rules.award(profile,state,0x80000000))
        assert rules.award(profile,replace(state,hp=0),50).hp == 0
        missing = replace(rules,thresholds={})
        rejects(lambda: missing.award(profile,state,50))
        pet = inv.grant_pet(500001)
        def change(key, version, operation, value):
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                return inv.change_pet_growth(db,pet,key,version,operation,value)
        first = change('battle:1',0,'experience',50)
        assert first.state.level == 1
        encoded = pet_record({'id':pet,'template_id':500001,'name':'成长验证','progress':first})
        fields = {4:struct.pack('<i',500001),8:struct.pack('<i',pet),
                  0x10:'成长验证'.encode('utf-16le'),0x20:struct.pack('<i',4),
                  0x28:struct.pack('<i',1),
                  0x34:struct.pack('<i',1139),  # Known new ordinary white cap: original level3 upper bound.
                  0x40:struct.pack('<9i',first.state.hp,first.attributes.max_hp,
                                   first.state.mp,first.attributes.max_mp,
                                   first.attributes.physical_attack,first.attributes.physical_defense,
                                   first.attributes.speed,first.attributes.magic_attack,first.attributes.magic_defense),
                  0x6c:struct.pack('<5h',*first.attributes.five_stats),
                  0x78:struct.pack('<h',first.attributes.potential),
                  0x80:struct.pack('<Q',first.state.experience),
                  0x94:struct.pack('<5i',*first.profile.aptitudes),
                  0xac:struct.pack('<f',1.006)}  # Known1006 original display scale; tested independently.
        native,_ = probe(0xf89ba0,0xf5df70,0xf5f1f0,fields)
        # Known new stone sources add the final six-entry map. Independent
        # original scalar serialization remains byte-identical; execute the
        # original Pet map decoder/constructor to check the added source too.
        assert native[:-1] == encoded[:-49] and native[-1:]==b'\0', 'Growth scalars differ from independent original serializer'
        assert native_pet_stones(encoded)==((1930,0),(1940,0),(1950,0),(1960,0),(1970,0),(1980,0))
        assert change('battle:1',0,'experience',50) == first
        rejects(lambda: change('battle:1',0,'experience',51))
        rejects(lambda: change('battle:2',0,'experience',50))
        before = inv.snapshot()
        try:
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                inv.change_pet_growth(db,pet,'battle:rollback',1,'experience',200)
                raise ValueError('Injected shared settlement failure')
        except ValueError:
            pass
        assert inv.snapshot() == before
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            assert inv.pet_progress(db,pet) == first
        # Explicit legacy migration only; startup itself leaves old pets untouched.
        with closing(store.connect()) as db, db:
            legacy = db.execute('INSERT INTO inventory_pets(role_id,template_id,name) VALUES(?,?,?)',
                                (role['id'],500001,'旧宠物')).lastrowid
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            rejects(lambda: inv.pet_progress(db,legacy))
            migrated = inv.initialize_pet_growth(db,legacy)
            rejects(lambda: inv.initialize_pet_growth(db,legacy))
        assert migrated.state.level == 0
        reopened = Inventory(AccountStore(store.path),1111,role['id'],store.inventory_config)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN')
            assert reopened.pet_progress(db,pet) == first
    result = {'rules':'designed 2026-10-23.pet.1', 'passed':[
              'original midpoint aptitudes and raw growth retained', '0..150 point conservation',
              'original current-level XP thresholds and cap carry', 'allocation budget',
              'overflow and missing threshold refusal', 'dead pet stays dead on upgrade',
              'same-transaction progression and version rollback', 'idempotent per-pet settlement',
              'stale version refusal', 'explicit legacy migration without reroll', 'reopen snapshot'],
              'native_attribute_fields_encoded':['level','HP/MP','physical/magic attack/defense','speed','five stats','potential','growth display float'],
              'native_growth_packet_matches_original_serializer':True,
              'battle_attribute_scale_checked':False}
    write_json(OUT/'evidence/pet-growth-verification.json',result)
    print('PASS:', ', '.join(result['passed']))


if __name__ == '__main__':
    main()

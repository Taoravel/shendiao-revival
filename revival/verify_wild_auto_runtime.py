"""Actual encrypted wild automatic command must advance without timeout."""
import asyncio
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
import battle_protocol as p
import runtime_storage
from research_battle_auto import native_auto_action
from verify_wild_runtime import start,encounter
from research_battle import NativeBattleDecoder
from inventory import AssetChange


async def check(store,prepared,role,*,with_pet=False):
    rt,peer,owner=await start(store,prepared,role)
    try:
        store.wild_rules=replace(store.wild_rules,chance=10000,grace_ms=0,cooldown_ms=0)
        if with_pet:
            def owned_pet():
                from progression import credit_experience
                with closing(owner.inventory.accounts.connect()) as db,db:
                    db.execute('BEGIN IMMEDIATE')
                    credit_experience(db,1111,owner.id,sum(store.growth_rules.costs[level] for level in range(1,5)),
                        store.growth_rules,store.attribute_rules,owner.epoch)
                    owner.inventory.apply_settlement(db,AssetChange('auto-owned-pet-fixture',pets=(500001,)))
                    key=db.execute('SELECT id FROM inventory_pets WHERE role_id=?',(owner.id,)).fetchone()[0]
                    owner.inventory.change_pet_growth(db,key,'auto-pet-level-fixture',0,'experience',owner.inventory.growth_rules.thresholds[0])
                    db.execute('UPDATE inventory_pets SET fighting=1 WHERE id=?',(key,))
            await owner.io(owned_pet)
        await encounter(peer,owner)
        battle=owner.battle;bid=battle.key
        command=native_auto_action()
        assert p.parse_action(command)==(p.ATTACK,0,0,1,1)
        before=await battle.call('snapshot')
        # Only the verified automatic attack sentinel gains target selection.
        for bad in (native_auto_action(automatic=False,cached_target=0),
                    struct.pack('>iiiBB',p.ATTACK,0,0,1,2),
                    struct.pack('>iiiBB',p.ATTACK,1,0,1,1)):
            assert await peer.request(p.SEND_ACTION,bad)==[]
            assert await battle.call('snapshot')==before
        rounds=0
        while owner.battle is not None:
            rounds+=1;assert rounds<=20
            replies=await peer.request(p.SEND_ACTION,command)
            if with_pet:
                assert replies==[] and battle.domain.snapshot().phase=='commands'
                replies=await peer.request(p.SEND_ACTION,native_auto_action(is_role=False))
            assert replies and replies[0][0]==p.ROUND_SCRIPT,(
                'Native auto attack was ignored until timeout',battle.domain._training.last_rejection)
            NativeBattleDecoder().decode('SSendRoundScript',replies[0][1])
            after=await battle.call('snapshot')
            assert after.phase=='playback'
            replies=await peer.request(p.CLIENT_PLAY_END,b'\0')
            if owner.battle is not None:
                assert [kind for kind,body in replies[:2]]==[p.SERVER_PLAY_END,p.ROUND_START]
                assert (await battle.call('snapshot')).round_number==rounds+1
            else:assert replies[0][0]==p.BATTLE_END
        assert not rt.battles and battle.mailbox.task.done()
        with closing(store.connect()) as db:
            receipt=json.loads(db.execute('SELECT receipt FROM wild_reward_admissions WHERE battle_id=?',(bid,)).fetchone()[0])
        assert receipt['outcome']=='victory' and receipt['experience_awarded']>0
        return [dict(scope='owned role and pet' if with_pet else 'owned role',rounds=rounds,
            immediate_automatic_rounds=True,native_downlink_decoded=True,settled_once=True,
            malformed_manual_and_friendly_targets_rejected=True)]
    finally:await rt.close()


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='wild-auto-') as temporary:
        store=AccountStore(Path(temporary)/'auto.sqlite3')
        role=store.create_role(1111,'自动回归甲',11,1010109)
        with closing(store.connect()) as db,db:
            db.execute('INSERT OR REPLACE INTO role_positions VALUES(?,?,?,?)',(role['id'],1014,896,3776))
        pet_role=store.create_role(1111,'自动宠物乙',11,1010109)
        with closing(store.connect()) as db,db:
            db.execute('INSERT OR REPLACE INTO role_positions VALUES(?,?,?,?)',(pet_role['id'],1014,896,3776))
        prepared=runtime_storage.prepare(store)
        passed=asyncio.run(check(store,prepared,role))
        passed+=asyncio.run(check(store,prepared,pet_role,with_pet=True))
    report=dict(passed=passed,live_server_changed=False,native_gui_verified=False)
    from inspect_client import OUT
    (OUT/'evidence/wild-auto-runtime-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

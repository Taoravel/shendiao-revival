"""Encrypted production movement -> native wild battle -> atomic real assets.

Temporary roles have explicit known profiles. Only encounter grace/chance and
drop rolls are deterministic fixtures; real routers/owners/storage stay intact.
"""
import asyncio
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import struct
import tempfile
import threading
from unittest.mock import patch
from accounts import AccountStore
from game_runtime import GameRuntime
from verify_runtime import Peer
from verify_npc_equipped_repair_runtime import seed_profile
from research_battle import NativeBattleDecoder
from inventory import AssetChange
from battle import Fighter
from wild_battle import WildBattle
from world_movement import CHECK_MOVE,ROLE_MOVE
import battle_protocol as p
import runtime_storage
import wild_runtime_storage as storage


def db_read(store,sql,args=()):
    with closing(store.connect()) as db:return db.execute(sql,args).fetchall()


async def start(store,prepared,role):
    class Log:
        def __init__(self):self.events=[]
        def emit(self,**event):self.events.append(event)
    rt=GameRuntime(store,prepared,logger=Log());peer=Peer(rt);await peer.login(role);owner=rt.roles[role['id']]
    await owner.io(seed_profile,store,owner.inventory)
    await owner.mailbox.call('initialize_wallet',(0,0,0,0),'explicit_migration')
    return rt,peer,owner


async def encounter(peer,owner):
    x,y=owner.position.value[1:]
    target=960 if x==896 else 896
    peer.encounter_sequence=getattr(peer,'encounter_sequence',0)+1
    # Accepted native MOVE intention alone cannot roll.
    assert await peer.request(ROLE_MOVE,struct.pack('>hhhhQ',x,y,target,y,0))==[]
    assert owner.battle is None
    opening=await peer.request(CHECK_MOVE,struct.pack('>hhBQ',target,y,0,peer.encounter_sequence))
    assert owner.battle is not None,('Accepted authoritative displacement did not open wild battle',owner.rt.logger.events[-4:])
    for kind,body in opening:
        if kind in (p.BATTLE_START,p.ADD_FIGHTERS,p.ROUND_START):
            NativeBattleDecoder().decode({p.BATTLE_START:'SSendBattleStart',p.ADD_FIGHTERS:'SSendAddFighters',p.ROUND_START:'SSendRoundStart'}[kind],body)
    assert [k for k,b in opening if k in (p.BATTLE_START,p.ADD_FIGHTERS,p.ROUND_START)]==[p.BATTLE_START,p.ADD_FIGHTERS,p.ROUND_START]
    return owner.battle.key


async def win(peer,owner):
    packets=[]
    for _ in range(20):
        messages=await peer.request(p.SEND_ACTION,struct.pack('>iiiBB',p.ATTACK,21,0,1,0))
        if owner.battle and owner.battle.domain.participant.pet:
            assert messages==[]
            messages=await peer.request(p.SEND_ACTION,struct.pack('>iiiBB',p.ATTACK,21,0,0,0))
        assert messages and messages[0][0]==p.ROUND_SCRIPT
        NativeBattleDecoder().decode('SSendRoundScript',messages[0][1])
        messages=await peer.request(p.CLIENT_PLAY_END,b'\0');packets.extend(messages)
        if p.BATTLE_END in [k for k,b in messages]:return packets
    raise AssertionError('Wild battle did not finish')


async def defer_victory(peer,owner):
    """Use native combat, save its actual terminal, stop at failed payout."""
    for _ in range(20):
        script=await peer.request(p.SEND_ACTION,struct.pack('>iiiBB',p.ATTACK,21,0,1,0))
        if owner.battle.domain.participant.pet:
            assert script==[]
            script=await peer.request(p.SEND_ACTION,struct.pack('>iiiBB',p.ATTACK,21,0,0,0))
        assert script and script[0][0]==p.ROUND_SCRIPT
        snapshot=await owner.battle.call('snapshot')
        if next(f.hp for f in snapshot.fighters if f.id==21)==0:
            with patch.object(storage,'settle',side_effect=ValueError('crash before payout')):
                assert await peer.request(p.CLIENT_PLAY_END,b'\0')==[]
            return snapshot
        await peer.request(p.CLIENT_PLAY_END,b'\0')
    raise AssertionError('Native battle did not reach terminal')


async def check(store,prepared,a,b):
    rt,peer,owner=await start(store,prepared,a);checks=[]
    try:
        # Explicit deterministic fixture; production source keeps20% and5sec.
        assert store.wild_rules.chance==2000 and store.wild_rules.grace_ms==5000
        store.wild_rules=replace(store.wild_rules,chance=10000,grace_ms=0,cooldown_ms=0)
        before=await owner.io(owner.inventory.snapshot)
        with patch('wild_rewards._roll',return_value=0):bid=await encounter(peer,owner)
        assert isinstance(owner.battle.domain._training,WildBattle)
        assert owner.battle.domain.participant.stats.hp==70
        assert owner.battle.wild_ticket.monster in store.wild_rules.maps[1014].monsters
        assert (await owner.io(owner.inventory.snapshot))==before,'Preflight leaked items or versions'
        saved=json.loads(db_read(store,'SELECT plan FROM wild_reward_admissions WHERE role_id=? AND battle_id=?',(owner.id,bid))[0][0])
        assert len(saved['grants'])==3
        # Normal world inventory and move packets cannot mutate during combat.
        pos=owner.position
        assert await peer.request(CHECK_MOVE,struct.pack('>hhBQ',1024,3776,0,2))==[]
        assert owner.position==pos
        messages=await win(peer,owner)
        assert owner.battle is None and not rt.battles
        row=db_read(store,'SELECT status FROM wild_runtime_battles WHERE role_id=? AND battle_id=?',(owner.id,bid))[0]
        assert row==('settled',)
        receipt=json.loads(db_read(store,'SELECT receipt FROM wild_reward_admissions WHERE role_id=? AND battle_id=?',(owner.id,bid))[0][0])
        assert receipt['experience_awarded']>0 and receipt['cash_awarded']==10 and receipt['silver_awarded']==10
        after=await owner.io(owner.inventory.snapshot)
        assert sum(i['quantity'] for i in after['items'])==3
        assert {k for k,v in messages}>={p.BATTLE_END,0xc000d,0xc32c8,0xc03fa,0xc0012,0xc03f3}
        state=await owner.io(runtime_storage.role_load_profile,store,1111,owner.id,owner.epoch)
        assert 0<state.attributes.vitals.hp<70
        assert owner.role['experience']==state.role.experience==receipt['experience_awarded']
        committed=await owner.io(storage.settle,store,1111,owner.id,owner.epoch,bid)
        assert committed.replayed and await owner.io(owner.inventory.snapshot)==after
        checks.append('real encrypted accepted move -> original monster -> native battle -> XP/cash/bound silver/three fixed drops/role HP committed once')
        await peer.connection.close();peer=Peer(rt);await peer.login(a);owner=rt.roles[a['id']]
        assert (await owner.io(owner.inventory.snapshot))==after
        assert owner.role['experience']==receipt['experience_awarded']
        checks.append('reconnect reads committed current resources, inventory and experience without replay reward')
        # Another role's heartbeat proceeds while actual wild settlement I/O waits.
        other=Peer(rt);await other.login(b)
        assert await other.request(100,b'wild')==[(100,b'wild')]
        checks.append('second encrypted role remains independent')
        # Abort after real damage persists the latest copy without victory pay.
        await encounter(peer,owner)
        await peer.request(p.SEND_ACTION,struct.pack('>iiiBB',p.ATTACK,21,0,1,0))
        saved_hp=next(f.hp for f in (await owner.battle.call('snapshot')).fighters if f.id==1)
        prior_xp=owner.role['experience'];abort_id=owner.battle.key
        await peer.connection.close();peer=Peer(rt);await peer.login(a);owner=rt.roles[a['id']]
        profile=await owner.io(runtime_storage.role_load_profile,store,1111,owner.id,owner.epoch)
        assert profile.attributes.vitals.hp==saved_hp
        abort=json.loads(db_read(store,'SELECT receipt FROM wild_reward_admissions WHERE role_id=? AND battle_id=?',(owner.id,abort_id))[0][0])
        assert abort['outcome']=='draw' and abort['experience_awarded']==0 and owner.role['experience']==prior_xp
        checks.append('disconnect during playback persists actual damage and aborts with zero victory awards')
        # Restore only the explicit fixture resources, not production HP policy.
        def fixture_heal():
            from role_attribute_storage import read_attribute_snapshot,update_role_vitals
            with closing(owner.inventory.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');current=read_attribute_snapshot(db,1111,owner.id,owner.epoch)
                update_role_vitals(db,1111,owner.id,owner.epoch,current.vitals,
                    replace(current.vitals,version=current.vitals.version+1,hp=70))
        # A failed nonterminal checkpoint must not swallow a later disconnect.
        await owner.io(fixture_heal)
        await encounter(peer,owner);closing_battle=owner.battle
        with patch.object(storage,'checkpoint',side_effect=ValueError('controlled round checkpoint failure')) as failed_checkpoint:
            assert await peer.request(p.SEND_ACTION,struct.pack('>iiiBB',p.ATTACK,21,0,1,0))==[]
            assert failed_checkpoint.call_count==1
        assert owner.pending_battle_delivery and owner.pending_battle_delivery[1] is None
        actual_hp=next(f.hp for f in (await closing_battle.call('snapshot')).fighters if f.id==1)
        await peer.connection.close()
        assert not rt.battles and closing_battle.mailbox.task.done(),'Disconnect left the old BattleOwner alive'
        peer=Peer(rt);await peer.login(a);owner=rt.roles[a['id']]
        profile=await owner.io(runtime_storage.role_load_profile,store,1111,owner.id,owner.epoch)
        assert profile.attributes.vitals.hp==actual_hp
        checks.append('failed nonterminal checkpoint retries before disconnect, then closes battle mailbox and persists exact abort damage')
        await owner.io(fixture_heal)
        await encounter(peer,owner);closing_battle=owner.battle;unpaid_id=closing_battle.key
        with patch.object(storage,'checkpoint',side_effect=ValueError('persistent checkpoint outage')):
            assert await peer.request(p.SEND_ACTION,struct.pack('>iiiBB',p.ATTACK,21,0,1,0))==[]
            await peer.connection.close()
        assert not rt.battles and closing_battle.mailbox.task.done()
        assert db_read(store,'SELECT status FROM wild_runtime_battles WHERE battle_id=?',(unpaid_id,))[0]==('active',)
        peer=Peer(rt);await peer.login(a);owner=rt.roles[a['id']]
        recovered=json.loads(db_read(store,'SELECT receipt FROM wild_reward_admissions WHERE battle_id=?',(unpaid_id,))[0][0])
        assert recovered['outcome']=='draw' and recovered['experience_awarded']==0
        checks.append('persistent checkpoint outage releases disconnected owner; next lease recovers last durable active copy with zero victory payout')
        await owner.io(fixture_heal)
        with patch('wild_rewards._roll',return_value=0):await encounter(peer,owner)
        before_failure=await owner.io(owner.inventory.snapshot);old_xp=owner.role['experience']
        injected=False
        for _ in range(10):
            await peer.request(p.SEND_ACTION,struct.pack('>iiiBB',p.ATTACK,21,0,1,0))
            snapshot=await owner.battle.call('snapshot')
            dead=next(f.hp for f in snapshot.fighters if f.id==21)==0
            if dead:
                with patch.object(storage,'settle',side_effect=ValueError('controlled settlement failure')):
                    assert await peer.request(p.CLIENT_PLAY_END,b'\0')==[]
                injected=True;break
            await peer.request(p.CLIENT_PLAY_END,b'\0')
        assert injected and owner.battle is not None and owner.pending_battle_delivery
        assert (await owner.io(owner.inventory.snapshot))==before_failure and owner.role['experience']==old_xp
        retry=await owner.mailbox.call('tick')
        assert retry[0][0]==p.BATTLE_END and owner.battle is None
        checks.append('persisted terminal survives payout failure; retry releases battle only after one atomic payout')
        await owner.io(fixture_heal)
        # The real role DB wait does not occupy another role or connection.
        await encounter(peer,owner)
        entered,release=threading.Event(),threading.Event();original=storage.settle
        def slow(*args):
            entered.set()
            if not release.wait(4):raise TimeoutError('fixture release missing')
            return original(*args)
        with patch.object(storage,'settle',slow):
            pending=asyncio.create_task(win(peer,owner))
            try:
                assert await asyncio.to_thread(entered.wait,2)
                assert await asyncio.wait_for(other.request(100,b'free'),.8)==[(100,b'free')]
            finally:release.set()
            await pending
        checks.append('controlled blocking actual wild payout leaves other encrypted role heartbeat runnable')
    finally:await rt.close()
    return checks


async def recovery_check(store,prepared,role):
    rt,peer,owner=await start(store,prepared,role)
    bid=None;old_battle=None
    try:
        def fixture():
            from role_resource_storage import migrate_role_resources
            from role_equipment_storage import current_equipment_totals
            from role_equipment import resource_caps_from_projection
            from role_attribute_storage import read_attribute_snapshot
            from progression import credit_experience
            with closing(owner.inventory.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE')
                credit_experience(db,1111,owner.id,sum(store.growth_rules.costs[level] for level in range(1,5))+
                    store.growth_rules.costs[5]-1,store.growth_rules,store.attribute_rules,owner.epoch)
                owner.inventory.apply_settlement(db,AssetChange('owned-pet-fixture',pets=(500001,)))
                pet=owner.inventory.selected_fighting_pet(db)
                key=db.execute('SELECT id FROM inventory_pets WHERE role_id=?',(owner.id,)).fetchone()[0]
                owner.inventory.change_pet_growth(db,key,'pet-level1-fixture',0,'experience',owner.inventory.growth_rules.thresholds[0])
                db.execute('UPDATE inventory_pets SET fighting=1 WHERE id=?',(key,))
                snapshot=owner.inventory.immutable_snapshot_transaction(db,epoch=owner.epoch)
                before=read_attribute_snapshot(db,1111,owner.id,owner.epoch)
                totals=current_equipment_totals(db,1111,owner.id,owner.epoch,snapshot,store.equipment_attribute_rules)
                migrate_role_resources(db,1111,owner.id,owner.epoch,before.vitals,resource_caps_from_projection(totals),
                    origin='explicit_migration',migration_id='explicit-migrated-wild-fixture',rules=store.resource_rules,
                    equipment_rules=store.equipment_attribute_rules)
                return key
        pet_key=await owner.io(fixture)
        with patch('wild_rewards._roll',return_value=0):bid=await encounter(peer,owner)
        old_battle=owner.battle;participant=old_battle.domain.participant
        assert participant.pet.key==pet_key
        # Persist the real terminal, deliberately stop before payout (crash seam).
        snapshot=await defer_victory(peer,owner)
        assert db_read(store,'SELECT status FROM wild_runtime_battles WHERE role_id=? AND battle_id=?',(owner.id,bid))==[('terminal',)]
        new_epoch=await asyncio.to_thread(store.acquire_lease,1111,owner.id)
        await asyncio.to_thread(storage.recover,store,1111,owner.id,new_epoch)
        receipt=json.loads(db_read(store,'SELECT receipt FROM wild_reward_admissions WHERE role_id=? AND battle_id=?',(owner.id,bid))[0][0])
        assert receipt['pet_experience']['recipient']==pet_key and receipt['pet_experience']['awarded']>0
        state=await asyncio.to_thread(runtime_storage.role_load_profile,store,1111,owner.id,new_epoch)
        assert state.role.level==participant.level+1 and state.role.experience==receipt['experience_awarded']-1
        hp=next(f.hp for f in snapshot.fighters if f.id==1)
        assert state.attributes.vitals.hp==hp+state.attributes.vitals.max_hp-participant.stats.max_hp
        replay=await asyncio.to_thread(storage.settle,store,1111,owner.id,new_epoch,bid)
        assert replay.replayed and replay.role==state.role
        await asyncio.to_thread(storage.recover,store,1111,owner.id,new_epoch)
        assert await asyncio.to_thread(runtime_storage.role_load_profile,store,1111,owner.id,new_epoch)==state
        return ['explicit migrated role + actual owned pet participates; durable victory recovers under new lease once',
                'role auto-level uses same resource transaction preserving combat wounds; original pet XP and three drops settle atomically']
    finally:
        # Simulated dead process cleanup: only its volatile mailbox is discarded.
        if old_battle:
            await old_battle.close();rt.battles.pop(old_battle.key,None);owner.battle=None
        await rt.close()


async def source_check(store,prepared,role):
    from role_resource_storage import migrate_role_resources,read_role_resources
    from role_equipment_storage import current_equipment_totals
    from role_equipment import resource_caps_from_projection
    from role_attribute_storage import read_attribute_snapshot
    rt,peer,owner=await start(store,prepared,role)
    try:
        def migrate():
            with closing(owner.inventory.accounts.connect()) as db,db:
                db.execute('BEGIN IMMEDIATE');snapshot=owner.inventory.immutable_snapshot_transaction(db)
                before=read_attribute_snapshot(db,1111,owner.id,owner.epoch)
                totals=current_equipment_totals(db,1111,owner.id,owner.epoch,snapshot,store.equipment_attribute_rules)
                migrate_role_resources(db,1111,owner.id,owner.epoch,before.vitals,resource_caps_from_projection(totals),
                    origin='explicit_migration',migration_id='explicit-source-guard-fixture',rules=store.resource_rules,
                    equipment_rules=store.equipment_attribute_rules)
        await owner.io(migrate)
        with patch('wild_rewards._roll',return_value=0):bid=await encounter(peer,owner)
        await defer_victory(peer,owner)
        def unrelated_source():
            with closing(owner.inventory.accounts.connect()) as db:
                db.execute('BEGIN IMMEDIATE')
                try:
                    original=read_role_resources(db,1111,owner.id,owner.epoch,store.resource_rules)
                    plan=json.loads(db.execute('SELECT plan FROM wild_reward_admissions WHERE battle_id=?',(bid,)).fetchone()[0])
                    owner.inventory.apply_settlement(db,AssetChange('unrelated-source-fixture',(tuple(plan['grants'][0]),)))
                    runtime_storage._synchronize_source(db,store,owner.inventory,'unrelated-source-fixture',replayed=False)
                    changed=read_role_resources(db,1111,owner.id,owner.epoch,store.resource_rules)
                    assert (original.version,original.hp,original.mp,original.caps.hp_max,original.caps.mp_max)==(
                        changed.version,changed.hp,changed.mp,changed.caps.hp_max,changed.caps.mp_max)
                    assert original.caps.source!=changed.caps.source
                    try:storage._settle(db,store,1111,owner.id,owner.epoch,bid)
                    except ValueError as error:
                        assert 'admission resource source' in str(error),str(error)
                    else:raise AssertionError('Accepted unrelated source-only change against old combat admission')
                finally:db.rollback()
        await owner.io(unrelated_source)
        assert owner.battle is not None
        await owner.mailbox.call('tick')
        assert owner.battle is None
        return ['frozen full admission resource source rejects real unrelated inventory-source change even with identical resource version/HP/MP/caps; rejected transaction leaves original terminal payable once']
    finally:await rt.close()


def main():
    with tempfile.TemporaryDirectory(prefix='wild-runtime-') as tmp:
        store=AccountStore(Path(tmp)/'test.sqlite3')
        a=store.create_role(1111,'暗雷实路甲',11,1010109);b=store.create_role(1111,'暗雷实路乙',12,1010101)
        c=store.create_role(1111,'暗雷恢复丙',11,1010109)
        with closing(store.connect()) as db,db:
            db.execute('INSERT OR REPLACE INTO role_positions VALUES(?,?,?,?)',(a['id'],1014,896,3776))
            db.execute('INSERT OR REPLACE INTO role_positions VALUES(?,?,?,?)',(c['id'],1014,896,3776))
        prepared=runtime_storage.prepare(store)
        checks=asyncio.run(check(store,prepared,a,b))
        checks+=asyncio.run(recovery_check(store,prepared,c))
        guard=AccountStore(Path(tmp)/'source-guard.sqlite3')
        d=guard.create_role(1111,'暗雷来源丁',11,1010109)
        with closing(guard.connect()) as db,db:
            db.execute('INSERT OR REPLACE INTO role_positions VALUES(?,?,?,?)',(d['id'],1014,896,3776))
        guard_prepared=runtime_storage.prepare(guard)
        guard.wild_rules=replace(guard.wild_rules,chance=10000,grace_ms=0,cooldown_ms=0)
        checks+=asyncio.run(source_check(guard,guard_prepared,d))
    report=dict(passed=checks,actual_runtime_path=True,native_downlink_decoded=True,live_server_changed=False,native_gui_verified=False)
    (Path(__file__).parent/'evidence/wild-runtime-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()

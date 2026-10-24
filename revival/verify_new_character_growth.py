"""Historical growth-only creation provenance -> task growth -> reconnect.

Existing characters are deliberately separate fixtures. No manual growth or
attribute initialization is allowed for the profile redemption slice under test.
Natural current creation and school intros are covered by verify_newbie_runtime.
"""
import asyncio
from contextlib import closing
from dataclasses import asdict
import json
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from task_protocol import C_COMMIT_SCENARIO_QUEST
from verify_growth_runtime import GrowthPeer,role_values,world_vitals
from world_entity_protocol import VISIT_NPC
import runtime_storage


async def check(store,prepared,legacy,old_origin,new,npc):
    runtime=GameRuntime(store,prepared)
    try:
        old_peer=GrowthPeer(runtime);await old_peer.login(legacy)
        assert world_vitals(old_peer)[0]==7
        assert 490 not in role_values(old_peer.initial)
        await old_peer.connection.close()
        origin_peer=GrowthPeer(runtime);await origin_peer.login(old_origin)
        assert 490 not in role_values(origin_peer.initial)
        await origin_peer.connection.close()
        peer=GrowthPeer(runtime);await peer.login(new)
        assert world_vitals(peer)==(1,(100,100,100,100,100))
        values=role_values(peer.initial)
        assert {k:values[k] for k in (490,500,10,20,30,40,50,80)}=={
            490:1,500:0,10:10,20:10,30:10,40:10,50:10,80:20}
        owner=runtime.roles[new['id']]
        with closing(store.connect()) as db:
            assert db.execute('SELECT COUNT(*) FROM role_growth WHERE role_id IN (?,?)',
                              (legacy['id'],old_origin['id'])).fetchone()[0]==0
            assert db.execute('SELECT level FROM roles WHERE id=?',(legacy['id'],)).fetchone()==(7,)
            assert db.execute('SELECT experience FROM role_progress WHERE role_id=?',(legacy['id'],)).fetchone()==(42,)
            receipt=db.execute('SELECT creation_profile_receipt FROM role_restoration_origins WHERE role_id=?',
                               (new['id'],)).fetchone()[0]
            assert receipt and len(receipt)==64
        key=(npc.map_id<<32)|npc.placement_id
        body=struct.pack('>iQi',100192,key,0)
        await owner.mailbox.call('offer_task',100192)
        await peer.request(VISIT_NPC,struct.pack('>q',key))
        await peer.request(C_COMMIT_SCENARIO_QUEST,body)
        completion=await peer.request(C_COMMIT_SCENARIO_QUEST,body)
        values=role_values(completion)
        assert {k:values[k] for k in (490,500,60,70,140,150)}=={
            490:2,500:5,60:110,70:106,140:110,150:106}
        assert owner.role['level']==2 and owner.role['experience']==61
        assert await peer.request(C_COMMIT_SCENARIO_QUEST,body)==[]
        await peer.connection.close()
    finally:
        await runtime.close()
    runtime=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(runtime);await peer.login(new)
        assert world_vitals(peer)==(2,(110,110,110,106,106))
        assert role_values(peer.initial)[500]==5
        with closing(store.connect()) as db:
            assert db.execute('SELECT creation_profile_receipt FROM role_restoration_origins WHERE role_id=?',
                              (new['id'],)).fetchone()==(receipt,)
            assert db.execute('SELECT COUNT(*) FROM role_attribute_baselines WHERE role_id=?',(new['id'],)).fetchone()==(1,)
            assert db.execute('SELECT COUNT(*) FROM role_growth WHERE role_id=?',(new['id'],)).fetchone()==(1,)
            assert db.execute('SELECT experience FROM role_progress WHERE role_id=?',(new['id'],)).fetchone()==(61,)
    finally:
        await runtime.close()
    return {'passed':['historical growth-only creation fixture has a designed versioned template before first login',
        'first valid login creates ordinary growth/attributes once without a test initialization call',
        'old role and old wallet-only origin get no invented growth/attribute profile',
        'original NPC task100192 grants150XP -> level2/XP61/free5 and current19-field refresh',
        'duplicate task submission cannot grant more experience or points',
        'recreated runtime/reconnect preserves level2 attributes and single creation receipt'],
        'initialization_provenance':'designed historical growth-only creation fixture; no newbie chapter origin',
        'task_activation':'trusted offer fixture; current natural creation separately covered by verify_newbie_runtime.py',
        'database':'disposable','manual_new_role_growth_initialization':False,
        'live_server_changed':False,'battle_executed':False,'native_gui_tested':False}


def main():
    with tempfile.TemporaryDirectory(prefix='new-character-growth-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3')
        legacy=store.create_role(1111,'原有角色',11,1010109)
        old_origin=store.create_role(1111,'旧钱包档',11,1010109)
        new=store.create_role(1111,'成长来源档',11,1010109)
        with closing(store.connect()) as db,db:
            db.execute('UPDATE roles SET level=7 WHERE id=?',(legacy['id'],))
            db.execute('INSERT INTO role_progress VALUES(?,42)',(legacy['id'],))
        prepared=runtime_storage.prepare(store)
        with closing(store.connect()) as db,db:
            db.execute('INSERT INTO role_restoration_origins(role_id,origin,wallet_policy) VALUES(?,?,?)',
                       (old_origin['id'],'new_restoration_role',store.currency_rules.revision))
            # A durable pre-newbie creation record, as produced by the previous
            # creation policy. Do not remove a current chapter to bypass its gate.
            template=json.dumps(dict(format=1,source='design/role-attributes-v1.json#new_role_designed_baseline',
                provenance='designed',growth_policy=store.growth_rules.revision,
                attribute_policy=store.attribute_rules.revision,
                profile=asdict(store.attribute_rules.initial_profile)),sort_keys=True,separators=(',',':'))
            db.execute('INSERT INTO role_restoration_origins '
                       '(role_id,origin,wallet_policy,creation_profile) VALUES(?,?,?,?)',
                       (new['id'],'new_restoration_role',store.currency_rules.revision,template))
        with closing(store.connect()) as db:
            template,receipt=db.execute('SELECT creation_profile,creation_profile_receipt FROM role_restoration_origins WHERE role_id=?',
                                       (new['id'],)).fetchone()
            assert json.loads(template)['provenance']=='designed' and receipt is None
            assert db.execute('SELECT COUNT(*) FROM role_growth WHERE role_id=?',(new['id'],)).fetchone()==(0,)
        npc=next(p for p in store.npc_resources[0][1006] if p.npc_id==10899)
        store.save_position(1111,new['id'],(npc.map_id,npc.x,npc.y))
        result=asyncio.run(check(store,prepared,legacy,old_origin,new,npc))
    write_json(OUT/'evidence/new-character-growth-verification.json',result)
    print(result)


if __name__=='__main__':main()

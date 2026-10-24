"""Natural first master: Start's CCommit must open the original weapon card.

No synthetic CQuestDialogEnd, direct grant, live listener, client or battle.
Audited movement reports exercise the actual owner, not client pathfinding.
"""
import asyncio
import json
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT
from task_protocol import C_COMMIT_SCENARIO_QUEST
from world_card_protocol import S_PLAY_CARD_EFFECT,C_GET_CARD_ITEM
from world_entity_protocol import VISIT_NPC
from world_movement import ROLE_MOVE,ROLE_STOP
from world_newbie import load_newbie_routes,END_PLAY_CG
from inventory import EQUIP_ITEM
from verify_growth_runtime import GrowthPeer
from verify_first_master_runtime import state
from research_first_master_dialogue_end import native_start_completion
from wire import compact
import runtime_storage


async def check(store,prepared,role,route,witness):
    runtime=GameRuntime(store,prepared)
    try:
        peer=GrowthPeer(runtime);await peer.login(role)
        await peer.request(END_PLAY_CG,struct.pack('>i',route.intro_movie_id))
        path=tuple(tuple(p) for p in witness['path'])
        await peer.request(ROLE_MOVE,struct.pack('>hhhhQ',*path[0],*path[-1],0))
        await peer.request(ROLE_STOP,compact(len(path))+b''.join(struct.pack('>hh',*p) for p in path)
            +struct.pack('>hhQ',*path[-1],0))
        key=(route.home_map_id<<32)|witness['placement_id']
        await peer.request(VISIT_NPC,struct.pack('>q',key))
        before=state(store,role['id'])
        choice=struct.pack('>ii',route.successor_card_effect_id,49009)
        await peer.request(C_GET_CARD_ITEM,choice)
        assert state(store,role['id'])==before,'Unsolicited choice granted a weapon'
        # Original phase2 Start ends with this request. No phase3/End packet is
        # inserted to conceal a server waiting for the wrong client event.
        native_messages,native_trace,native_phase=native_start_completion(route.successor_task_id,key)
        assert native_phase==2 and len(native_messages)==1
        kind,body=native_messages[0]
        assert kind==C_COMMIT_SCENARIO_QUEST
        replies=await peer.request(kind,body)
        card=(S_PLAY_CARD_EFFECT,struct.pack('>i',route.successor_card_effect_id))
        assert card in replies,'First-master Start finished with CCommit but server never opened the weapon card'
        assert state(store,role['id'])==before,'Opening the card completed/rewarded the task early'
        await peer.request(C_GET_CARD_ITEM,choice)
        awarded=state(store,role['id'])
        assert len(awarded[1])==1 and awarded[1][0][1:]==(49009,1,1,None)
        item_key=awarded[1][0][0]
        await peer.request(C_GET_CARD_ITEM,choice)
        await peer.request(kind,body)
        assert state(store,role['id'])==awarded,'Repeated final sentence/card choice duplicated reward'
        await peer.request(EQUIP_ITEM,struct.pack('>ii',item_key,0))
        equipped=state(store,role['id'])
        assert dict(equipped[0])[100188]=='completed' and dict(equipped[0])[100104]=='active'
        await peer.connection.close()
        peer=GrowthPeer(runtime);await peer.login(role)
        assert state(store,role['id'])==equipped and not any(k==S_PLAY_CARD_EFFECT for k,_ in peer.initial)
        await peer.connection.close()
    finally:
        await runtime.close()
    return dict(messages=[(hex(k),b.hex()) for k,b in native_messages],trace=native_trace,phase=native_phase)


def main():
    route=load_newbie_routes()[(9,11)]
    audit=json.loads((OUT/'evidence/newbie-birth-sites-audit.json').read_text(encoding='utf-8'))
    witness=next(r for r in audit['routes'] if (r['character_id'],r['school_id'])==(9,11))
    with tempfile.TemporaryDirectory(prefix='master-commit-card-') as folder:
        store=AccountStore(Path(folder)/'state.sqlite3');prepared=runtime_storage.prepare(store)
        role=store.create_role(1111,'对白后领武器',11,1010109)
        native=asyncio.run(check(store,prepared,role,route,witness))
    result=dict(passed=['natural intro/clear wire path/master NPC through actual Owner',
        'Start CCommit alone opens the original card without synthetic DialogEnd',
        'choice grants one bound original weapon; actual equip activates cart; retries/reconnect preserve it'],
        native_start_output=native,database='disposable',native_gui_verified=False,live_server_changed=False,battle_executed=False)
    (OUT/'evidence/master-commit-card-runtime-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(result)


if __name__=='__main__':main()

"""Existing native wild battle terminal must restore explicit normal walking.

This exercises the already enabled ordinary wild battle, not paused story AI.
Only its chance/grace are deterministic; actual owners/settlement/send remain.
"""
import asyncio
from dataclasses import replace
from pathlib import Path
import struct
import tempfile
from accounts import AccountStore
from inspect_client import OUT,write_json
import runtime_storage
import battle_protocol as p
from runtime_movement import SET_ROLE_LOCATION
from verify_wild_runtime import start,encounter
from verify_world_resource_runtime import checkpoint_fixture
from research_battle_auto import native_auto_action
from research_battle import NativeBattleDecoder


async def check(store,prepared,role):
    runtime,peer,owner=await start(store,prepared,role)
    try:
        store.wild_rules=replace(store.wild_rules,chance=10000,grace_ms=0,cooldown_ms=0)
        await encounter(peer,owner)
        before=owner.position
        stop=b'\0'+struct.pack('>hhQ',*before.value[1:],1014)
        try:
            await runtime.map(owner.map_address).mailbox.call('move',owner.id,owner.epoch,
                before.version,0xc0faa,stop)
        except ValueError as error:
            assert str(error)=='Movement waits for exact normal-state delivery',str(error)
        else:raise AssertionError('Battle entry retained normal map movement context')
        assert owner.position==before
        terminal=None
        for _ in range(20):
            replies=await peer.request(p.SEND_ACTION,native_auto_action())
            assert replies[0][0]==p.ROUND_SCRIPT
            NativeBattleDecoder().decode('SSendRoundScript',replies[0][1])
            replies=await peer.request(p.CLIENT_PLAY_END,b'\0')
            if owner.battle is None:
                terminal=replies;break
        assert terminal is not None and not runtime.battles
        expected=(SET_ROLE_LOCATION,struct.pack('>QhhB',owner.id,*owner.position.value[1:],0))
        assert terminal.count(expected)==1 and terminal[-1]==expected
        before=owner.position
        await peer.request(0xc0faa,stop)
        assert owner.position.version>before.version and owner.position.value==before.value
        grid=store.movement_grids[1014]
        wall=next((i%grid.width*16,i//grid.width*16) for i,value in enumerate(grid.cells)
            if value&1 and i%grid.width*16<32768 and i//grid.width*16<32768)
        before=owner.position
        await peer.request(0xc0faa,b'\0'+struct.pack('>hhQ',*wall,1014))
        assert owner.position==before and store.position(1111,owner.id)==before.value
        return dict(battle_entry_map_context_revoked=True,actual_terminal_location0=True,
            normal_clear_after_delivery=True,original_wall_after_battle_rejected=True,
            battle_scope='existing ordinary wild rules; no paused formal story AI',
            native_gui_verified=False,live_service_changed=False)
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='runtime-movement-battle-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        role=store.create_role(1111,'战后行走回归',11,1010109)
        prepared=runtime_storage.prepare(store)
        checkpoint_fixture(store,role,(1014,896,3776))
        result=asyncio.run(asyncio.wait_for(check(store,prepared,role),45))
    write_json(OUT/'evidence/runtime-movement-battle-verification.json',result);print(result)


if __name__=='__main__':main()

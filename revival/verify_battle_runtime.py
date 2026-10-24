"""Encrypted connection -> role -> scheduled battle integration in a temp store."""
import asyncio
import json
from pathlib import Path
import struct
import tempfile
from unittest.mock import patch
from accounts import AccountStore
from game_runtime import GameRuntime
import runtime_storage
from verify_runtime import Peer
from battle_owner import BattleOwner
from research_battle import NativeBattleDecoder
from research_battle_commands import native_action
import battle_protocol as p


class RecordingPeer(Peer):
    def __init__(self, runtime):
        super().__init__(runtime)
        self.received=[]

    async def request(self,kind,body):
        replies=await super().request(kind,body)
        self.received.append((kind,tuple(replies)))
        return replies


class ShortPlayback(BattleOwner):
    """Only change the explicit deployment policy, not the state machine."""
    def __init__(self,*args,**kwargs):
        kwargs['playback_timeout_ms']=5
        super().__init__(*args,**kwargs)


async def check(store,prepared):
    runtime=GameRuntime(store,prepared,training=True)
    results=[]
    try:
        a,b=store.roles(1111)
        pa=RecordingPeer(runtime)
        await pa.login(a)
        opening=[(k,body) for request,replies in pa.received if request==0xc003d
                 for k,body in replies if k in (p.BATTLE_START,p.ADD_FIGHTERS,p.ROUND_START)]
        assert [k for k,body in opening]==[p.BATTLE_START,p.ADD_FIGHTERS,p.ROUND_START]
        assert struct.unpack_from('>i',opening[-1][1])[0]==30
        for name,(_,body) in zip(('SSendBattleStart','SSendAddFighters','SSendRoundStart'),opening):
            NativeBattleDecoder().decode(name,body)
        actor=runtime.roles[a['id']]
        for turn in range(1,5):
            replies=await pa.request(p.SEND_ACTION,native_action(1,21))
            assert [k for k,body in replies]==[p.ROUND_SCRIPT]
            NativeBattleDecoder().decode('SSendRoundScript',replies[0][1])
            replies=await pa.request(p.CLIENT_PLAY_END,b'\0')
            assert [k for k,body in replies]==([p.BATTLE_END] if turn==4 else [p.SERVER_PLAY_END,p.ROUND_START])
        assert actor.battle is None and not runtime.battles
        assert (await pa.request(100,b'live'))==[(100,b'live')]
        results.append('native sender attacks win in four rounds through continuous encrypted connection; battle released')

        with patch('game_runtime.BattleOwner',ShortPlayback):
            pb=RecordingPeer(runtime)
            await pb.login(b)
        actor=runtime.roles[b['id']]
        replies=await pb.request(p.SEND_ACTION,native_action(4,0))
        assert [k for k,body in replies]==[p.ROUND_SCRIPT]
        NativeBattleDecoder().decode('SSendRoundScript',replies[0][1])
        await asyncio.sleep(.02)
        replies=await actor.mailbox.call('tick')
        assert replies and replies[0][0]==p.BATTLE_END
        assert actor.battle is None and not runtime.battles, 'Playback timeout left role trapped in ended battle'
        results.append('playback timeout sends battle end and releases role; no victory event')
    finally:
        await runtime.close()
    return results


if __name__=='__main__':
    with tempfile.TemporaryDirectory() as temporary:
        store=AccountStore(Path(temporary)/'battle.sqlite3')
        store.create_role(1111,'战斗验证甲',12,1010101)
        store.create_role(1111,'战斗验证乙',11,1010109)
        results=asyncio.run(check(store,runtime_storage.prepare(store)))
    report={'passed':results,'actual_runtime_path':True,'native_downlink_decoder':True,
            'live_server_changed':False,'live_client_presentation_verified':False}
    (Path(__file__).parent/'evidence/battle-runtime-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))

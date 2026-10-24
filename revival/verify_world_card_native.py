"""Original card codecs, Process dispatch and both actual button send paths."""
import json
import struct
from pathlib import Path
from contextlib import redirect_stdout
from native_inspect import disasm
from native_gameplay_probe import probe
from verify_world_intro_black_native import Replay
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_ESP
from world_card_protocol import play_card_effect, decode_get_card_item

OUT=Path(__file__).parent/'evidence'


class CardReplay(Replay):
    def __init__(self,effect_id=20044):
        super().__init__()
        self.effect_id=effect_id
        self.ui,self.net,self.netvt,self.factory,self.factoryvt,self.record=(
            0x500a000,0x500b000,0x500c000,0x500d000,0x500e000,0x5010000)
        self.w(self.net,self.netvt);self.w(self.netvt+0x3c,0x500f080)
        self.w(self.factory,self.factoryvt);self.w(self.factoryvt+8,0x500f090)
        self.w(self.record,effect_id)

    def hook(self,e,a,size,user):
        sp=e.reg_read(UC_X86_REG_ESP)
        if a==0x813860:self.ret(value=self.net)
        elif a==0x500f080:
            msg=self.r(sp+4)
            if self.r(msg+4)==0xc4a52:
                self.calls.append({'sent_type':'0xc4a52','quest_id':self.r(msg+8)})
            else:
                self.calls.append({'sent_type':hex(self.r(msg+4)),
                                   'effect_id':self.r(msg+8),'item_id':self.r(msg+12)})
            self.ret(4)
        elif a==0x1743740:
            self.calls.append({'card_ui_close_boundary':True});self.ret()
        elif a==0x89eb50:self.ret(value=self.factory)
        elif a==0x89ebd0:self.ret(value=self.factory)
        elif a==0x500f090:
            assert self.r(sp+4) in (self.effect_id,103286,100186)
            self.ret(4,self.record)
        elif a==0x17444a0:self.ret(value=self.ui)
        elif a==0x1744070:
            self.calls.append({'card_UI_1744070_effect_id':self.r(sp+4)})
            self.ret(4)
        elif a==0x1743540:self.ret(value=self.ui)
        elif a==0x1753ec0:
            self.calls.append({'other_card_UI_1753ec0_effect_id':self.r(sp+4)})
            self.ret(4)
        elif a==0x11ca790:
            self.calls.append({'local_generic_effect_request':self.r(self.r(sp+4))})
            self.ret(4)
        elif a==0x11d1870:self.ret(4,0)
        else:super().hook(e,a,size,user)


def button(effect_id,item_id,address):
    r=CardReplay(effect_id);r.w(r.ui+0x40,effect_id,49009,49006)
    r.run(address,r.ui,0)
    expected={'sent_type':'0xc041f','effect_id':effect_id,'item_id':item_id}
    assert r.calls==[expected,{'card_ui_close_boundary':True}],r.calls
    return {'original_button_callback':hex(address),'calls':r.calls}


def process(effect_id):
    r=CardReplay(effect_id);r.w(r.packet+8,effect_id)
    r.run(0x1744540,r.packet,0,0)
    kind='card_UI_1744070_effect_id' if effect_id<40000 else 'other_card_UI_1753ec0_effect_id'
    assert r.calls==[{kind:effect_id}],r.calls
    return {'original_SPlayCardEffect_Process':True,'effect_id':effect_id,'calls':r.calls}


def local_animation(effect_id):
    r=CardReplay(effect_id);manager=0x5011000
    r.w(r.record+0x2ac,effect_id);r.w(r.record+0xc8,0)
    r.run(0x1255e70,manager,r.record)
    assert r.calls==[{'local_generic_effect_request':effect_id}],r.calls
    return {'original_task_animation_function':'0x1255e70','effect_id':effect_id,
            'calls':r.calls,'SPlayCardEffect_UI_not_called':True}


def codecs():
    results=[]
    for effect in (20044,20006):
        body,target=probe(0xd54b80,0xe40e40,0xd54c10,{8:struct.pack('<i',effect)})
        assert body==play_card_effect(effect) and struct.unpack_from('<i',target,8)[0]==effect
        results.append({'SPlayCardEffect':effect,'wire':body.hex(),'native_encode_decode':True})
        for item in (49009,49006):
            b,t=probe(0xd919d0,0xe4c480,0xd91a70,
                      {8:struct.pack('<ii',effect,item)})
            assert decode_get_card_item(b)==(effect,item)
            assert struct.unpack_from('<ii',t,8)==(effect,item)
            results.append({'CGetCardItem':[effect,item],'wire':b.hex(),'native_encode_decode':True})
    return results


def dialogue_end(quest_id,effect_id):
    r=CardReplay(effect_id)
    r.w(r.ui+0x44,quest_id,0);r.w(r.ui+0x60,3)
    r.w(r.record+0x2ac,effect_id);r.w(0x2945584,0x5011000)
    r.e.reg_write(UC_X86_REG_ESI,r.ui)
    r.run(0x1644c1a,r.ui,end=0x1644cf8)
    assert r.calls==[{'local_generic_effect_request':effect_id},
                     {'sent_type':'0xc4a52','quest_id':quest_id}],r.calls
    return {'original_finished_dialogue_span':'0x1644c1a..0x1644cf8',
            'UI_stage_60':3,'quest_id':quest_id,'effect_id':effect_id,'calls':r.calls}


if __name__=='__main__':
    results=codecs()
    for effect in (20044,20006):
        results += [process(effect),button(effect,49009,0x1743990),
                    button(effect,49006,0x1743a10),local_animation(effect)]
    results += [dialogue_end(103286,20044),dialogue_end(100186,20006)]
    (OUT/'world-card-native.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    with (OUT/'world-card-native-disassembly.txt').open('w',encoding='utf-8') as stream:
        with redirect_stdout(stream):
            for address,size in ((0xbb6751,64),(0x1255e70,90),(0x12550c0,94),
                                 (0x1744540,74),(0x1743990,120),(0x1743a10,120),
                                 (0x17443ce,43),(0xd54b80,23),(0xd54c10,100),
                                 (0xd919d0,24),(0xd91a70,140),(0x1644c1a,225)):
                print('\n',hex(address));disasm(address,size)
    print(json.dumps({'passed':len(results),'results':results},indent=2))

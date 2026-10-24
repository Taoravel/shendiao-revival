"""Original automatic-command sender and marshal; no running client access."""
import hashlib
import json
from research_battle import NativeBattleDecoder,CLASSES
from native_inspect import DATA


def native_auto_action(operation=1,operation_id=0,*,is_role=True,automatic=True,cached_target=21):
    n=NativeBattleDecoder()
    n.call(CLASSES['CSendAction'][0])
    manager=n.obj-(0x9c if is_role else 0xb8)
    n.write(manager+0x54,3 if is_role else 4)
    n.write(manager+0x5c,0 if is_role else 0x5003000)
    n.write(manager+(0xfc if is_role else 0x108),cached_target,operation,operation_id)
    n.write(n.stack,n.stop,int(automatic))
    n.u.reg_write(n.sp,n.stack);n.u.reg_write(n.cx,manager)
    # Execute the entire real role/pet branch through its field assignments,
    # stopping before the unrelated native network singleton lookup.
    n.u.emu_start(0x1195aa0,0x813860,count=200)
    assert n.u.reg_read(n.ip)==0x813860
    n.write(n.stream,0x224c100,n.buf,0);n.write(n.buf-12,4096,0,1)
    n.call(0xe41550,n.stream)
    return bytes(n.u.mem_read(n.buf,n.read(n.buf-8)))


if __name__=='__main__':
    import battle_protocol as p
    cases={}
    for role in (True,False):
        packet=native_auto_action(is_role=role)
        assert p.parse_action(packet)==(p.ATTACK,0,0,int(role),1)
        manual=native_auto_action(is_role=role,automatic=False)
        assert p.parse_action(manual)==(p.ATTACK,21,0,int(role),0)
        cases['role' if role else 'pet']=dict(automatic=packet.hex(),manual=manual.hex())
    print(json.dumps(dict(image_sha256=hashlib.sha256(DATA).hexdigest(),sender='0x1195aa0',
        marshal='0xe41550',cases=cases,actual_client_accessed=False),indent=2))

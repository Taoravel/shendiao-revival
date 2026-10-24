"""Original endurance request/list/max codecs and real inventory query."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
from accounts import AccountStore
from inventory import Inventory
from equipment_protocol import REQUEST_ENDURES,endurance_refresh,maximum_refresh
from native_gameplay_probe import probe
from inspect_client import OUT,write_json
from native_inspect import BASE,DATA


def native_consumer():
    """Original handlers/setters execute; adapter supplies the item lookup.

    GUI observers are absent, so this checks keyed data mutation without claiming
    actual window refresh or access to the running client.
    """
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EAX,UC_X86_REG_EIP
    emu=Uc(UC_ARCH_X86,UC_MODE_32)
    emu.mem_map(0,0x1000);emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
    emu.mem_map(0x5000000,0x200000)
    msg,rows,stack,stop=0x5001000,0x5002000,0x5100000,0x500f000
    wrappers={7:0x5003000,9:0x5004000};objects={7:0x5005000,9:0x5006000}
    def w(a,*v):emu.mem_write(a,struct.pack('<'+'I'*len(v),*v))
    def read(a):return struct.unpack('<I',emu.mem_read(a,4))[0]
    w(0x2944628,0x5007000)
    for ptr in (0x29457d0,0x294ab50,0x294ab54):w(ptr,0)
    for key in wrappers:w(wrappers[key],objects[key]);w(wrappers[key]+8,8)
    calls=[]
    def hook(uc,address,size,user):
        if address==stop:uc.emu_stop()
        elif address==0x1091670:
            sp=uc.reg_read(UC_X86_REG_ESP);key,column=read(sp+4),read(sp+8)
            assert column==4 and key in wrappers
            calls.append(key);uc.reg_write(UC_X86_REG_EAX,wrappers[key])
            uc.reg_write(UC_X86_REG_ESP,sp+12);uc.reg_write(UC_X86_REG_EIP,read(sp))
    emu.hook_add(UC_HOOK_CODE,hook)
    w(msg+8,4);w(msg+0x10,rows,rows+24,rows+24)
    w(rows,0x2284380,7,80,0x2284380,9,0)
    w(stack,stop,0,0);emu.reg_write(UC_X86_REG_ESP,stack);emu.reg_write(UC_X86_REG_ECX,msg)
    emu.emu_start(0x1093380,stop,count=10000)
    assert emu.reg_read(UC_X86_REG_EIP)==stop and calls==[7,9]
    assert read(objects[7]+0xc8)==80 and read(objects[9]+0xc8)==0
    w(msg+8,4,7,90);w(stack,stop,0,0)
    emu.reg_write(UC_X86_REG_ESP,stack);emu.reg_write(UC_X86_REG_ECX,msg)
    emu.emu_start(0x1093470,stop,count=10000)
    assert emu.reg_read(UC_X86_REG_EIP)==stop and calls==[7,9,7]
    assert read(objects[7]+0xcc)==90 and read(objects[7]+0xc8)==80


def main():
    native_consumer()
    body=struct.pack('>i',4)
    native,_=probe(0xd96020,0xe4d070,0xd960c0,{8:body[::-1]})
    assert native==body
    entries=((7,80),(9,0))
    kind,reply=endurance_refresh(4,entries)
    obj=0x5001000;begin=obj+0x100
    native,_=probe(0xef9850,0xefa210,0xefa2a0,{8:struct.pack('<i',4),
        0x10:struct.pack('<III',begin,begin+24,begin+24),
        0x100:b''.join(struct.pack('<Iii',0x2284380,k,v) for k,v in entries)})
    assert kind==0xc0412 and reply==native
    kind,reply=maximum_refresh(4,7,90)
    native,_=probe(0xd9dfb0,0xe4e950,0xd9e050,{8:struct.pack('<iii',4,7,90)})
    assert kind==0xc0414 and reply==native
    # A confirmed repair request layout is not permission to invoke NPC repair.
    request=struct.pack('>iQii',2,123456,4,7)
    native,_=probe(0x8184f0,0xe4cf30,0xd954c0,
        {8:struct.pack('<i',2),0x10:struct.pack('<Qii',123456,4,7)})
    assert request==native
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'耐久同步',12,1010101)
        config=Inventory.prepare(store);inv=Inventory(store,1111,role['id'],config)
        inv.grant_item(40200,binding=1);key=inv.snapshot()['items'][0]['id']
        inv.equip(key,0)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');inv.wear_equipment(db,key,'wear',0,20)
            assert inv.equipment_refresh(db,key)==(endurance_refresh(4,((key,80),)),maximum_refresh(4,key,100))
        replies=inv.receive(REQUEST_ENDURES,struct.pack('>i',4))
        assert replies==[endurance_refresh(4,((key,80),)),maximum_refresh(4,key,100)]
        probe(0xef9850,0xefa210,0xefa2a0,payload=replies[0][1])
        probe(0xd9dfb0,0xe4e950,0xd9e050,payload=replies[1][1])
        assert inv.receive(REQUEST_ENDURES,struct.pack('>i',1))==[endurance_refresh(1,())]
        inv.unequip(key,3)
        assert inv.receive(REQUEST_ENDURES,struct.pack('>i',1))[0]==endurance_refresh(1,((key,80),))
        with closing(store.connect()) as db,db:
            db.execute('INSERT INTO inventory_items(role_id,template_id,quantity,slot) VALUES(?,?,1,?)',
                       (role['id'],40200,8))
        before=inv.snapshot()
        try:inv.receive(REQUEST_ENDURES,struct.pack('>i',1))
        except ValueError:pass
        else:raise AssertionError('Unknown legacy durability hidden by fabricated partial reply')
        assert inv.snapshot()==before
    report={'passed':['native endurance request layout','native nonempty current-endurance list bytes',
        'native maximum-endurance message bytes','native repair request layout',
        'original handlers apply current/max to the exact column and instance key',
        'owned carried/equipped condition query','post-wear current-state refresh','unknown legacy refuses fabrication'],
        'native_ui_tested':False,'NPC_repair_route_connected':False}
    write_json(OUT/'evidence/equipment-endurance-protocol-verification.json',report)
    print('PASS:',', '.join(report['passed']))


if __name__=='__main__':main()

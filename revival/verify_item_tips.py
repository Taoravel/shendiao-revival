"""Quality metadata reply and the original FoodObject quality-reader prefix."""
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
from accounts import AccountStore
from inventory import Inventory, ITEM_TIPS
from inspect_client import OUT, write_json
from native_inspect import BASE,DATA
from native_gameplay_probe import probe
from wire import octets


def native_quality(payload):
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
    emu=Uc(UC_ARCH_X86,UC_MODE_32)
    emu.mem_map(0,0x1000);emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
    emu.mem_map(0x5000000,0x200000)
    obj,stream,buf,stack=0x5001000,0x5002000,0x5003000,0x5100000
    def w(a,*values):emu.mem_write(a,struct.pack('<'+'I'*len(values),*values))
    w(obj+12,32001);w(stream,0x224c100,buf,0);w(buf-12,len(payload),len(payload),1)
    emu.mem_write(buf,payload);w(stack,0x500f000,stream)
    def hook(uc,address,size,user):
        if address==0x10818ec:uc.emu_stop()
        if address==0x1919292:raise ValueError('Original food quality reader rejected payload')
    emu.hook_add(UC_HOOK_CODE,hook)
    emu.reg_write(UC_X86_REG_ECX,obj);emu.reg_write(UC_X86_REG_ESP,stack)
    emu.emu_start(0x1081870,0x500f000,count=10000)
    assert emu.reg_read(UC_X86_REG_EIP)==0x10818ec
    assert struct.unpack('<I',emu.mem_read(stream+8,4))[0]==4
    return struct.unpack('<i',emu.mem_read(obj+0x84,4))[0]


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'品质显示',12,1010101)
        inv=Inventory(store,1111,role['id'],Inventory.prepare(store))
        inv.grant_item(32001,quality=10)
        item=inv.snapshot()['items'][0]
        replies=inv.receive(ITEM_TIPS,struct.pack('>ii',1,item['id']))
        expected=struct.pack('>ii',1,item['id'])+octets(struct.pack('>i',10))
        assert replies==[(0xc03fe,expected)]
        probe(0xd9c110,0xe4e5c0,0xe0a240,payload=expected)
        assert native_quality(struct.pack('>i',10))==10
        assert native_quality(struct.pack('>i',0))==0
        try:native_quality(b'\0\0')
        except ValueError:pass
        else:raise AssertionError('Truncated quality accepted')
        inv.grant_item(32000)
        fixed=next(x for x in inv.snapshot()['items'] if x['template_id']==32000)
        assert inv.receive(ITEM_TIPS,struct.pack('>ii',1,fixed['id']))==[
            (0xc03fe,struct.pack('>ii',1,fixed['id'])+octets(b''))]
        inv.grant_item(32001)
        unknown=next(x for x in inv.snapshot()['items'] if x['template_id']==32001 and x['quality'] is None)
        inv.grant_item(32014,quality=10)
        other_bean=next(x for x in inv.snapshot()['items'] if x['template_id']==32014)
        for column,key in ((1,unknown['id']),(1,other_bean['id']),(4,item['id']),(1,999999)):
            before=inv.snapshot()
            try:inv.receive(ITEM_TIPS,struct.pack('>ii',column,key))
            except ValueError:pass
            else:raise AssertionError('Unknown or unowned item detail fabricated')
            assert inv.snapshot()==before
    result={'passed':['native SItemTips decoder','original FoodObject quality reader',
        'zero quality is a real encoded value','truncated native quality rejected',
        'fixed food sends no invented quality','missing quality and unmapped tip beans stay pending',
        'invalid ownership and column cannot expose a detail'],
        'native_ui_tested':False,'food_parser_executed_until':'0x10818ec'}
    write_json(OUT/'evidence/item-tips-verification.json',result)
    print('PASS:',', '.join(result['passed']))


if __name__=='__main__':main()

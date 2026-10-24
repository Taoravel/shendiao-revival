"""Real wallet authority and original bag-consumer cash overwrite."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
from accounts import AccountStore
from inventory import Inventory,QUERY_BAG,MOVE_ITEM,USE_ITEM,EQUIP_ITEM,UNEQUIP_ITEM
from currency import load_currency_rules,prepare_wallet_storage,initialize_wallet
from native_gameplay_probe import probe
from native_inspect import BASE,DATA,u32
from inspect_client import OUT,write_json


def native_cash(body,initial=987654321):
    _,raw=probe(0xef6220,u32(0x2284234),u32(0x2284238),payload=body)
    from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EIP
    emu=Uc(UC_ARCH_X86,UC_MODE_32)
    emu.mem_map(0,0x1000);emu.mem_map(BASE,(len(DATA)+4095)&~4095);emu.mem_write(BASE,DATA)
    emu.mem_map(0x5000000,0x200000)
    wallet,msg,stack=0x5001000,0x5002000,0x5100000
    emu.mem_write(wallet+0xb0,struct.pack('<Q',initial));emu.mem_write(msg,raw)
    column=struct.unpack_from('>i',body)[0]
    emu.mem_write(stack,struct.pack('<IIII',0x500f000,column,msg+0x10,0))
    def hook(uc,address,size,user):
        if address in (0x10a488a,0x10a48d8):uc.emu_stop()
    emu.hook_add(UC_HOOK_CODE,hook)
    emu.reg_write(UC_X86_REG_ESP,stack);emu.reg_write(UC_X86_REG_ECX,wallet)
    emu.emu_start(0x10a4840,0x10a48d8,count=10000)
    assert emu.reg_read(UC_X86_REG_EIP) in (0x10a488a,0x10a48d8)
    return struct.unpack('<Q',emu.mem_read(wallet+0xb0,8))[0]


def main():
    with TemporaryDirectory() as tmp:
        store=AccountStore(Path(tmp)/'state.sqlite3')
        role=store.create_role(1111,'背包现金',12,1010101)
        store.inventory_config=Inventory.prepare(store)
        rules=load_currency_rules()
        epoch=store.acquire_lease(1111,role['id']);cash=2**40+7
        with closing(store.connect()) as db:prepare_wallet_storage(db)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            initialize_wallet(db,1111,role['id'],epoch,(cash,77,0,0),'explicit_migration',rules)
        inv=Inventory(store.leased(1111,role['id'],epoch),1111,role['id'],currency_rules=rules)
        inv.grant_item(31000,3)
        key=inv.snapshot()['items'][0]['id']
        reply=inv.receive(QUERY_BAG,struct.pack('>iQ',1,role['id']))[0]
        assert native_cash(reply[1])==cash,'Bag reply overwrote current cash with a fabricated value'
        moved=inv.receive(MOVE_ITEM,struct.pack('>6iq',1,key,0,1,5,1,-1))
        assert native_cash(moved[0][1])==cash
        worn=inv.receive(QUERY_BAG,struct.pack('>iQ',4,role['id']))[0]
        assert native_cash(worn[1])==987654321  # column4 does not overwrite cash.
        unknown=store.create_role(1111,'未知现金',12,1010101)
        unknown_epoch=store.acquire_lease(1111,unknown['id'])
        missing=Inventory(store.leased(1111,unknown['id'],unknown_epoch),1111,unknown['id'],currency_rules=rules)
        missing.grant_item(31000)
        before=missing.snapshot();item=before['items'][0]
        for kind,body in ((QUERY_BAG,struct.pack('>iQ',1,unknown['id'])),
                          (MOVE_ITEM,struct.pack('>6iq',1,item['id'],0,1,5,0,-1))):
            try:missing.receive(kind,body)
            except ValueError:pass
            else:raise AssertionError('Unknown cash fabricated or mutation committed without a valid reply')
            assert missing.snapshot()==before
        pet=missing.grant_pet(500001)
        missing.grant_item(32000)
        with closing(store.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            missing.change_pet_growth(db,pet,'damage',0,'resources',(1,1))
            missing.change_pet_care(db,pet,'care-loss',0,'defeat',1)
        for template in (32000,31000):
            before=missing.snapshot()
            owned=next(x for x in before['items'] if x['template_id']==template)
            try:missing.receive(USE_ITEM,struct.pack('>iiQ',owned['id'],1,pet))
            except ValueError:pass
            else:raise AssertionError('Pet item committed before discovering unknown bag cash')
            assert missing.snapshot()==before
        missing.grant_item(40200)
        weapon=next(x['id'] for x in missing.snapshot()['items'] if x['template_id']==40200)
        before=missing.snapshot()
        try:missing.receive(EQUIP_ITEM,struct.pack('>ii',weapon,0))
        except ValueError:pass
        else:raise AssertionError('Equip committed before invalid bag reply')
        assert missing.snapshot()==before
        missing.equip(weapon,0)  # explicit server fixture operation emits no reply.
        before=missing.snapshot()
        try:missing.receive(UNEQUIP_ITEM,struct.pack('>ii',weapon,-1))
        except ValueError:pass
        else:raise AssertionError('Unequip committed before invalid bag reply')
        assert missing.snapshot()==before
        no_context=Inventory(store,1111,role['id'],store.inventory_config)
        try:no_context.receive(QUERY_BAG,struct.pack('>iQ',1,role['id']))
        except ValueError:pass
        else:raise AssertionError('A current epoch was guessed for a context-free caller')
    report={'passed':['native bag consumer uses current cash instead of zero',
        '64-bit cash survives nonempty and move refreshes','equipment column does not alter cash',
        'unknown wallet never emits fabricated zero','invalid cash refresh preflight leaves mutation untouched',
        'pet healing and feeding roll back if bag cash cannot be encoded',
        'native equip/unequip roll back if carried cash is unknown',
        'context-free query cannot guess an active epoch'],
        'consumer_executed':'0x10a4840..0x10a488a',
        'native_ui_tested':False}
    write_json(OUT/'evidence/inventory-cash-verification.json',report)
    print('PASS:',', '.join(report['passed']))


if __name__=='__main__':main()

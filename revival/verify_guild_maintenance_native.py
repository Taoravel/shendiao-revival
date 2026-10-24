"""Offline original maintenance scalar consumers; never opens game or live DB.

Only the already bound details scalars are injected, not a production complete
GuildDetails mapper. Header CRT/string copying and formatter results are explicit
Adapters; numeric loads, scalar copies and 64-bit comparison execute unchanged.
SOURCE_OUT stays fixed when review redirects this module's OUT to a temp folder.
"""
from pathlib import Path
from dataclasses import asdict
import hashlib,json,struct,tempfile
import xml.etree.ElementTree as ET
from inspect_client import OUT,write_json
from native_inspect import DATA,BASE,u32
from verify_family_donation_native import Native
from unicorn.x86_const import (UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_EDI,
    UC_X86_REG_ESI,UC_X86_REG_ESP,UC_X86_REG_EIP)


SOURCE_OUT=Path(__file__).resolve().parent
IMAGE_SHA256='2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'
# These offsets bind individual quantities only; unbound fields stay test-zero.
FIELDS=(('funds',0x48,0x2d0,0xa8,True),('resources',0x58,0x2e0,0xb8,False),
    ('power',0x5c,0x2e4,0xbc,False),('normal_fee',0x60,0x2e8,0xc0,True),
    ('popularity',0x78,0x308,0xe0,False),('popularity_denominator',0x7c,0x30c,0xe4,False))


def number(n,address,wide=False):
    return struct.unpack('<Q' if wide else '<I',bytes(n.uc.mem_read(address,8 if wide else 4)))[0]


def control_bindings():
    layout=ET.parse(SOURCE_OUT/'decoded/ui/layouts/gang.layout').getroot()
    names={w.attrib.get('Name') for w in layout.iter('Window')}
    controls=(('Gangresource',0x22b3580,0x14afabc,0x14afb06,0x60),
        ('Gangmoneynum',0x22b3560,0x14afb17,0x14afb61,0x64),
        ('GangStudynum',0x22b3540,0x14afb72,0x14afbbc,0x68),
        ('GangMaintainMoney',0x22b351c,0x14afbcd,0x14afc17,0x6c),
        ('GangPopular',0x22b3500,0x14afc28,0x14afc72,0x70))
    for name,string,push,store,member in controls:
        expected='Gang/GangDetail/'+name
        assert expected in names
        encoded=expected.encode('ascii')+b'\0'
        assert DATA[string-BASE:string-BASE+len(encoded)]==encoded
        assert DATA[push-BASE]==0x68 and u32(push+1)==string
        assert DATA[store-BASE:store-BASE+3]==bytes((0x89,0x47,member)) # mov [edi+member],eax
    return [dict(control=name,member=hex(member),constructor_push=hex(push),
        constructor_store=hex(store)) for name,_,push,store,member in controls]


def scalar_consumers(expected):
    n=Native();manager,destination=0x5004000,0x5007000
    for name,bean,_,_,wide in FIELDS:
        n.uc.mem_write(n.stack+4+bean,struct.pack('<Q' if wide else '<I',expected[name]))
    skipped=[]
    def receive(at):
        if at==0x14a3598:
            # Before the external thiscall string-copy call: consume its one
            # pushed argument, not a return address that has not been pushed.
            skipped.append(hex(at))
            n.uc.reg_write(UC_X86_REG_ESP,n.uc.reg_read(UC_X86_REG_ESP)+4)
            n.uc.reg_write(UC_X86_REG_EIP,0x14a359e)
        elif at==0x14a3688:n.uc.emu_stop()
    n.run(0x14a34f0,manager,receive)
    assert n.uc.reg_read(UC_X86_REG_EIP)==0x14a3688 and skipped==['0x14a3598']
    received={name:number(n,manager+offset,wide) for name,_,offset,_,wide in FIELDS}
    assert received==expected
    n.uc.reg_write(UC_X86_REG_ESI,destination);n.uc.reg_write(UC_X86_REG_EDI,manager+0x228)
    n.run(0x14ab23e,0,lambda at:n.uc.emu_stop() if at==0x14ab327 else None)
    assert n.uc.reg_read(UC_X86_REG_EIP)==0x14ab327
    snapshot={name:number(n,destination+offset,wide) for name,_,_,offset,wide in FIELDS}
    assert snapshot==expected
    for _,_,_,offset,wide in FIELDS:
        n.uc.mem_write(n.stack+0x1e4+offset,bytes(n.uc.mem_read(destination+offset,8 if wide else 4)))
    formatted={}
    for name,start,formatter,wide in (('resources',0x14b125d,0x847450,False),
            ('power',0x14b1380,0x847450,False),('normal_fee',0x14b141c,0x490220,True),
            ('funds',0x14b12f9,0x490220,True)):
        def observe(at):
            if at==formatter:
                sp=n.uc.reg_read(UC_X86_REG_ESP);formatted[name]=number(n,sp+8,wide);n.uc.emu_stop()
        # In the original full refresh EBX is already its zero constant.
        n.uc.reg_write(UC_X86_REG_EBX,0);n.run(start,0,observe)
        assert n.uc.reg_read(UC_X86_REG_EIP)==formatter
    assert formatted=={key:expected[key] for key in ('resources','power','normal_fee','funds')}
    return dict(expected=expected,manager=received,snapshot=snapshot,formatter_arguments=formatted)


def funds_boundaries():
    observations=[];fee=100000001
    for delta,color in ((-1,0xffff0000),(0,0xffffffff),(1,0xffffffff)):
        n=Native();funds=48*fee+delta
        n.uc.mem_write(n.stack+0x2a4,struct.pack('<Q',fee))
        n.uc.mem_write(n.stack+0x28c,struct.pack('<Q',funds));n.uc.reg_write(UC_X86_REG_EBX,0)
        formatted=[];colors=[]
        def observe(at):
            if at==0x490220:
                sp=n.uc.reg_read(UC_X86_REG_ESP);formatted.append(number(n,sp+8,True))
                n.ret(value=0x5009000) # external formatter result only
            elif at==0x14b1364:
                colors.append(n.read(n.uc.reg_read(UC_X86_REG_ESP)));n.uc.emu_stop()
        n.run(0x14b12f9,0,observe)
        assert n.uc.reg_read(UC_X86_REG_EIP)==0x14b1364
        assert formatted==[funds] and colors==[color]
        observations.append(dict(fee=fee,funds=funds,delta_from_48x=delta,color=hex(color)))
    return observations


def popularity_boundaries():
    observations=[]
    for current,first_call in ((999,0x14b1481),(1000,0x14b15d0)):
        n=Native();n.write(n.stack+0x2c4,current,5000);formatted=[];branches=[]
        def observe(at):
            if at in (0x14b1481,0x14b15d0):branches.append(at)
            if at==0x847450:
                sp=n.uc.reg_read(UC_X86_REG_ESP);formatted.append(n.read(sp+8))
                if len(formatted)==1:n.ret(value=0x5009000)
                else:n.uc.emu_stop()
        n.run(0x14b1460,0,observe)
        assert n.uc.reg_read(UC_X86_REG_EIP)==0x847450
        assert formatted==[5000,current] and branches==[first_call]
        observations.append(dict(current=current,display_denominator=5000,
            formatter_arguments=formatted,first_formatter_call=hex(first_call)))
    return observations


def receipt_consumers(directory):
    from verify_guild_maintenance import make
    from guild_maintenance import GuildMaintenanceCommand
    f,guild,start=make(directory/'native-receipt.db')
    materials=f.org.guild_practice_materials(guild)
    f.org.execute(f.cmd(1,guild,'set_research',(300101,)),f.now())
    due=start+3600000
    command=GuildMaintenanceCommand(guild,due,due+5000,
        online=((1,f.epochs[1]),(2,f.epochs[2]),(3,'stale'),(16,f.epochs[16])))
    receipt=f.org.maintain_guild(command,due)
    # Independent explicit fixture expectation, not derived from the native
    # memory being checked or recomputed by the server's fee function.
    expected=dict(funds=9984000,resources=9,power=10,normal_fee=16000,
        popularity=2005,popularity_denominator=5000)
    values=asdict(receipt.after)
    assert {key:values[key] for key in expected if key!='popularity_denominator'}=={
        key:value for key,value in expected.items() if key!='popularity_denominator'}
    assert (receipt.mode,receipt.fee,receipt.online_count,receipt.status)==('normal',16000,2,'maintained')
    assert receipt.research.after.experience==7
    assert f.org.maintain_guild(command,due)==receipt and f.org.guild_practice_materials(guild)==materials
    # Only confirmed receipt scalars and the explicitly designed display
    # denominator are injected. This is not a full details packet producer.
    actual={key:values[key] for key in expected if key!='popularity_denominator'}
    actual['popularity_denominator']=f.org.guild_maintenance_rules.popularity_max
    assert actual==expected
    observed=scalar_consumers(actual)
    observed['maintenance']=dict(mode=receipt.mode,fee=receipt.fee,online_count=receipt.online_count,
        status=receipt.status,research_experience=receipt.research.after.experience,
        duplicate_receipt_equal=True,practice_materials_unchanged=True)
    return observed


def main():
    assert hashlib.sha256(DATA).hexdigest()==IMAGE_SHA256
    controls=control_bindings()
    with tempfile.TemporaryDirectory() as directory:receipt=receipt_consumers(Path(directory))
    wide=scalar_consumers(dict(funds=2**40+113,resources=12345,power=6789,
        normal_fee=2**35+17,popularity=999,popularity_denominator=5000))
    boundaries=funds_boundaries();popularity=popularity_boundaries()
    paths=('decoded/ui/layouts/gang.layout','verify_guild_maintenance.py','guild_maintenance.py',
        'verify_family_donation_native.py')
    result=dict(passed=['original constructor names/store members bind resource, funds, research power, maintenance fee and popularity controls',
        'real disposable-store hourly receipt scalars pass original detail copy, snapshot copy and four numeric formatter inputs',
        'distinct large64 funds and maintenance fee retain both halves through original scalar consumers',
        'original64 multiply and comparison choose red below48 and white at/above48 with a product exceeding32bits',
        'original popularity999/1000 branches read current and display denominator independently'],
        controls=controls,receipt=receipt,width_fixture=wide,funds_boundaries=boundaries,popularity_boundaries=popularity,
        native_image_sha256=IMAGE_SHA256,source_sha256={path:hashlib.sha256((SOURCE_OUT/path).read_bytes()).hexdigest() for path in paths},
        method='research primary-source execution; codebase-design isolates external string/CRT Adapters and keeps production Interface unchanged',
        adapters=['0x14a3598 header string-copy call skipped with original argument cleanup',
            '0x490220 and first 0x847450 return dummy string pointers only when continuing to a later observation',
            'original dialog construction/control stores checked statically; GUI setters are not invoked'],
        unknown=['normal/basic fee generation, resource growth/caps, hall fund cap and practice-room research-power/XP curves',
            'whether maintenance resource and seven-cash-practice materials are originally the same account',
            'complete details production mapping, full GUI render and actual server maintenance comparison timing'],
        details_scalar_prefix_executed=True,full_details_receiver_executed=False,
        full_details_production_mapper_implemented=False,native_gui_verified=False,
        fixture_policy_origin='explicit_test_fixture',production_policy_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/guild-maintenance-native-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()

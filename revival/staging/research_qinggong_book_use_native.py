"""Bounded original type73 field copy, dispatch/progress and CUseItem feedback.

Synthetic config/role/UI adapters only; no client, service, DB or gameplay.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_inspect import BASE,DATA,u32
from research_battle import NativeBattleDecoder
from verify_social_native import native_payload
from pfs import PfsArchive
from bxml import decode
from inspect_client import ROOT,catalog_rows
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESI,UC_X86_REG_EBP,UC_X86_REG_EBX,UC_X86_REG_EDI,UC_X86_REG_EDX

IMAGE_SHA='2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'


def native_qinggong_book_use(item_id,instance_key=123,role_id=0x1122334455667788):
    """Return actual bounded native progress args and native-marshaled body.

    Executes original attribute-field copy and dispatch segments with explicit
    initial state, NOT every outer inventory/UI prerequisite or elapsed timer.
    """
    if (type(item_id) is not int or item_id not in (50190,50191,50192)
            or type(instance_key) is not int or not 0<instance_key<2**31
            or type(role_id) is not int or not 0<role_id<2**63):raise ValueError('Bounded original book fixture required')
    if hashlib.sha256(DATA).hexdigest()!=IMAGE_SHA:raise ValueError('Original image mismatch')
    archive=PfsArchive(ROOT/'artres/config.pfs')
    def row(name):
        return next(v['attributes'] for v in catalog_rows(decode(archive.read('autoconfig/knight.gsp.item.'+name+'.xml')))
            if int(v['attributes']['id'])==item_id)
    item=row('citemattr');relative=row('ctaskrelative')
    assert (int(item['itemtypeid']),int(relative['readtime']),int(relative['usemap']))==(73,15,0)
    p=NativeBattleDecoder()
    cfg,wrapper,data,rel,manager,table,vt,progress,state,role,role_vt,conn,conn_vt=[p.allocate(n) for n in
        (0x180,0x200,0x100,0x90,0x100,0x20,0x20,0x300,0x100,0x200,0x50,0x50,0x50)]
    p.write(cfg,item_id,int(item['itemtypeid']))
    # Actual first two field assignments of1072890, called by108076f on wrapper+4.
    p.write(p.stack,p.stop,cfg);p.u.reg_write(p.sp,p.stack);p.u.reg_write(p.cx,wrapper+4)
    p.u.emu_start(0x1072890,0x10728a5,count=30)
    assert (p.read(wrapper+4),p.read(wrapper+8))==(item_id,73)
    p.u.reg_write(p.ax,p.read(wrapper+8))
    p.u.emu_start(0x10808be,0x1080f2d,count=20)
    assert p.u.reg_read(p.ip)==0x1080f2d
    p.obj=data;p.call(0x1073fd0)
    p.write(wrapper,data);p.write(wrapper+0x78,int(item['needLevel']))
    p.write(data+0xc,item_id);p.write(data+0x14,instance_key)
    p.write(rel,item_id);p.write(rel+0x24,int(relative['readtime']));p.write(rel+0x44,int(relative['usemap']))
    p.write(table,vt);p.write(vt+8,0x5000500)
    p.write(0x29455a8,state);p.write(0x294454c,role);p.write(0x2944550,role);p.write(role,role_vt)
    p.write(role_vt+0x38,0x5000510);p.write(conn,conn_vt);p.write(conn_vt+0x3c,0x5000520)
    p.write(0x294560c,manager)
    copy_string=u32(0x22444b4)
    if not any(start<=copy_string<end for start,end,_ in p.u.mem_regions()):p.u.mem_map(copy_string&~4095,4096)
    hits={'handler':0,'tips':[]};captured=[]
    def hook(uc,a,_size,_user):
        sp=uc.reg_read(p.sp)
        def ret(value=0,cleanup=0):
            uc.reg_write(p.ax,value);uc.reg_write(p.ip,p.read(sp));uc.reg_write(p.sp,sp+4+cleanup)
        if a==0x89da10:ret(table)
        elif a==0x5000500:
            assert p.read(sp+4)==item_id;ret(rel,4)
        elif a==copy_string:
            dst=uc.reg_read(p.cx);src=p.read(sp+4);uc.mem_write(dst,bytes(uc.mem_read(src,28)));ret(dst,4)
        elif a==0x1135590:ret(70)
        elif a in (0x1089220,0x10ee140):ret()
        elif a==0x1078c50:ret(cleanup=4)  # UI item-enabled presentation only.
        elif a==0x10ef5a0:p.write(state+0x78,p.read(sp+4));ret(cleanup=4)
        elif a==0x8114a0:ret(progress)
        elif a==0x10a5a80:hits['handler']+=1
        elif a==0x1091670:
            assert p.read(sp+4)==instance_key;ret(wrapper,8)
        elif a==0x8370a0:
            dst=p.read(sp+4);hits['tips'].append(p.read(sp+8));uc.mem_write(dst,bytes(28));p.write(dst+24,7);ret(dst)
        elif a==0x174cfc0:ret(cleanup=4)  # Tutorial presentation.
        elif a==u32(0x22443ec):ret()  # Temporary text destructor.
        elif a==0x5000510:
            uc.reg_write(UC_X86_REG_EDX,role_id>>32);ret(role_id&0xffffffff)
        elif a==0x813860:ret(conn)
        elif a==0x5000520:
            packet=p.read(sp+4);captured.append((p.read(packet+4),bytes(uc.mem_read(packet+8,16))))
            uc.emu_stop()
    p.u.hook_add(UC_HOOK_CODE,hook)
    # Execute actual TaskRelative readtime assignment from the factory.
    p.write(p.stack,p.stop);p.u.reg_write(p.sp,p.stack)
    for reg,value in ((UC_X86_REG_EDI,data),(UC_X86_REG_EBX,item_id),(UC_X86_REG_EBP,wrapper)):p.u.reg_write(reg,value)
    p.u.emu_start(0x1080f6d,0x1080fa6,count=100)
    assert p.read(data+0x74)==15
    # Original right-click dispatch tail calls the original task-item handler.
    p.write(p.stack,p.stop);p.u.reg_write(p.sp,p.stack);p.u.reg_write(UC_X86_REG_ESI,wrapper);p.u.reg_write(UC_X86_REG_EBP,manager)
    p.u.emu_start(0x10ae7a1,0x16c4140,count=4000)
    assert p.u.reg_read(p.ip)==0x16c4140
    sp=p.u.reg_read(p.sp);kind=p.read(sp+8);threshold=struct.unpack('<f',p.u.mem_read(sp+12,4))[0]
    keyptr=p.read(sp+16);key=(p.read(keyptr+4)<<32)|p.read(keyptr)
    assert (kind,threshold,key,hits['handler'])==(2,15.0,instance_key,1)
    # Explicit completed-kind2 fixture; no real time or UI is simulated.
    p.write(progress+0x5c,2,instance_key,0);p.write(progress+0x68,0)
    p.obj=progress;p.write(p.stack,p.stop);p.u.reg_write(p.sp,p.stack);p.u.reg_write(p.cx,progress)
    p.u.emu_start(0x16c4490,p.stop,count=4000)
    assert len(captured)==1 and hits['tips']==[10040+item_id-50190]
    packet_type,fields=captured[0];key,kind,lo,hi=struct.unpack('<4I',fields)
    assert (packet_type,key,kind,(hi<<32)|lo)==(0xc03ff,instance_key,0,role_id)
    body=native_payload(0xe4d740,scalars=[(8,key),(12,kind),(16,lo),(20,hi)])
    assert body==struct.pack('>iiQ',instance_key,0,role_id)
    return dict(item_id=item_id,instance_key=instance_key,role_id=role_id,progress_kind=2,threshold_raw=threshold,
        tutorial_text_id=hits['tips'][0],packet_type=packet_type,body=body,
        completed_timer_is_fixture=True,server_completion_authorized=False)


def main():
    rows=[]
    for item in (50190,50191,50192):
        v=native_qinggong_book_use(item);v['body_hex']=v.pop('body').hex();rows.append(v)
    print(json.dumps(dict(image_sha256=IMAGE_SHA,cases=rows,gui_verified=False,server_rule_verified=False),ensure_ascii=False,indent=2))


if __name__=='__main__':main()

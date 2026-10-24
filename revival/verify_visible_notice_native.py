"""Pure designed local notice through the original chat serializer/Process."""
import hashlib,json,struct
from dataclasses import FrozenInstanceError
from native_inspect import DATA
from verify_social_native import native_payload
from verify_family_donation_native import Native
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EIP
from inspect_client import OUT,write_json
from visible_notice import visible_notice
from native_gameplay_probe import probe


def receiver():
    n=Native();obj,manager=0x5001000,0x5004000
    n.write(0x294455c,manager);n.write(0x294480c,0x5006000)
    n.write(obj+8,0,0);n.write(obj+0x2c,0,2);seen=[]
    def observe(at):
        if at==0x1277d60:raise AssertionError('Zero system source entered player blacklist lookup')
        if at==0x15b7f40:
            sp=n.uc.reg_read(UC_X86_REG_ESP)
            seen.append(tuple(n.read(sp+offset) for offset in (4,8,12,16,20,24)))
            n.ret(24)
    n.run(0x15b8a40,obj,observe,args=(0,0))
    assert n.uc.reg_read(UC_X86_REG_EIP)==n.stop
    assert seen==[(2,0,0,0,obj+0x10,obj+0x34)]
    return seen


def decode_and_process(message,reason):
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ECX
    seen=[]
    def observer(machine,target):
        def read(address):return struct.unpack('<I',machine.mem_read(address,4))[0]
        def wstr(address):
            start=address+4 if read(address+24)<8 else read(address+4)
            return bytes(machine.mem_read(start,read(address+20)*2)).decode('utf-16-le')
        assert read(target+4)==message.kind and read(target+8)==read(target+0xc)==read(target+0x2c)==0
        assert read(target+0x30)==2 and wstr(target+0x10)=='系统通知' and wstr(target+0x34)==reason
        machine.mem_write(0x294455c,struct.pack('<I',0x5006000));machine.mem_write(0x294480c,struct.pack('<I',0x5007000))
        stack,stop=0x5100000,0x500f000
        machine.mem_write(stack,struct.pack('<III',stop,0,0))
        machine.reg_write(UC_X86_REG_ESP,stack);machine.reg_write(UC_X86_REG_ECX,target)
        def receive(uc,at,size,data):
            if at==0x1277d60:raise AssertionError('Decoded zero source entered player blacklist')
            if at==0x15b7f40:
                sp=uc.reg_read(UC_X86_REG_ESP)
                channel,low,high,level,name,text=(read(sp+v) for v in (4,8,12,16,20,24))
                seen.append((channel,low|(high<<32),level,wstr(name),wstr(text)))
                uc.reg_write(UC_X86_REG_EIP,read(sp));uc.reg_write(UC_X86_REG_ESP,sp+28)
        handle=machine.hook_add(UC_HOOK_CODE,receive)
        try:machine.emu_start(0x15b8a40,stop,count=500000)
        finally:machine.hook_del(handle)
        assert machine.reg_read(UC_X86_REG_EIP)==stop
    probe(0xf142c0,0xf143c0,0xf74b60,payload=message.body,observer=observer)
    assert seen==[(2,0,0,'系统通知',reason)]
    return seen


def main():
    text='当前角色资料尚未准备好，请稍后重试。'
    message=visible_notice(text)
    assert message.kind==0xc1772
    assert message.body==native_payload(0xf143c0,strings=[(0x10,'系统通知'),(0x34,text)],scalars=[(8,0),(0xc,0),(0x2c,0),(0x30,2)])
    try:message.kind=0
    except FrozenInstanceError:pass
    else:raise AssertionError('Notice DTO is mutable')
    for invalid in ('','\0','bad\nline','x'*257,True,'\ud800'):
        try:visible_notice(invalid)
        except ValueError:pass
        else:raise AssertionError('Invalid local notice accepted')
    seen=receiver()
    decoded=decode_and_process(message,text)
    result=dict(passed=['pure immutable local notice matches original SSendChatMsg marshal with sender0, fixed system label, level0 and current channel2',
        'complete original SSendChatMsg Process bypasses player blacklist for source0 and passes all six arguments to original ChatManager ingress',
        'original constructor/unmarshal consumes the actual encoded bytes and its decoded object reaches original Process/ChatManager ingress intact',
        'invalid or oversized plain notice text rejects before encoding'],
        image_sha256=hashlib.sha256(DATA).hexdigest(),consumer_ingress=seen,
        decoded_consumer_ingress=decoded,original_unmarshal_verified=True,
        designed_chat_fallback=True,native_system_notice_protocol_implemented=False,
        chat_manager_render_executed=False,native_gui_verified=False,live_server_changed=False,shared_entry_files_edited=False)
    write_json(OUT/'evidence/visible-notice-native-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()

"""Offline original normal-move gate; only toast output is host-adapted."""
from pathlib import Path
import hashlib,json,struct
from native_inspect import BASE,DATA,capstone


def main():
 from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
 from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
 uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(BASE,(len(DATA)+4095)&~4095);uc.mem_write(BASE,DATA)
 uc.mem_map(0x5000000,0x20000)
 role,scene,cutscene,modal,session_state,other,stack,stop=0x5001000,0x5002000,0x5003000,0x5004000,0x5005000,0x5006000,0x5010000,0x501f000
 def put(a,*v):uc.mem_write(a,struct.pack('<'+'I'*len(v),*(n&0xffffffff for n in v)))
 removed=[]
 def hook(emu,address,size,user):
  if address==0x11d37d0:
   sp=emu.reg_read(UC_X86_REG_ESP);target,effect=struct.unpack('<II',emu.mem_read(sp,8));removed.append(effect)
   emu.reg_write(UC_X86_REG_ESP,sp+8);emu.reg_write(UC_X86_REG_EIP,target)
  elif address==0x15bb820:
   sp=emu.reg_read(UC_X86_REG_ESP);target=struct.unpack('<I',emu.mem_read(sp,4))[0]
   emu.reg_write(UC_X86_REG_EAX,0);emu.reg_write(UC_X86_REG_ESP,sp+16);emu.reg_write(UC_X86_REG_EIP,target)
 uc.hook_add(UC_HOOK_CODE,hook)
 def reset():
  for a in (role,scene,cutscene,modal,session_state,other):uc.mem_write(a,bytes(0x800))
  uc.mem_write(0x2945060+0x3d8,b'\0')
  put(0x2944564,scene);put(0x2945620,cutscene);put(0x2945594,modal);put(0x294556c,session_state);put(0x29455c0,other);put(0x294d190,0)
 def run():
  put(stack,stop);uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,role)
  uc.emu_start(0x1211db0,stop,count=10000)
  assert uc.reg_read(UC_X86_REG_EIP)==stop
  return bool(uc.reg_read(UC_X86_REG_EAX)&255)
 cases=[]
 for name,address,data,expected in (
   ('clear_baseline',role+0x2e4,b'\0',True),
   ('application_3d8',0x2945060+0x3d8,b'\1',False),
   ('role_2e4',role+0x2e4,b'\1',False),
   ('cutscene_3c',cutscene+0x3c,b'\1',False),
   ('role_13c',role+0x13c,struct.pack('<I',1),False),
   ('global_294d190',0x294d190,struct.pack('<I',1),False),
   ('scene_58',scene+0x58,b'\1',False),
   ('modal_34',modal+0x34,struct.pack('<I',1),False),
   ('other_singleton_4',other+4,b'\1',False),
   ('session_state_3',session_state+4,struct.pack('<I',3),False),
   ('session_state_4',session_state+4,struct.pack('<I',4),False),
   ('opening_global_2945438_alias_of_application_3d8',0x2945438,struct.pack('<I',1),False),
   ('scene_black_effect_39c',scene+0x39c,struct.pack('<I',0x12345678),True),
   ('scene_transition_32c',scene+0x32c,b'\1',True)):
  reset();uc.mem_write(address,data);actual=run();assert actual==expected,(name,actual,expected)
  cases.append({'changed_field':name,'allowed':actual})
 reset();put(0x2945438,1);put(scene+0x39c,0x12345678)
 before=run();put(stack,stop);uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,0x5007000)
 uc.emu_start(0x12b9a10,stop,count=10000)
 assert uc.reg_read(UC_X86_REG_EIP)==stop
 cleared=struct.unpack('<I',uc.mem_read(scene+0x39c,4))[0]
 after=run()
 assert before is False and after is True and cleared==0 and removed==[0x12345678]
 lifecycle={'entry':'CStartSetion vtable+4 = 0x12b9a10','allowed_before':before,'allowed_after':after,'scene_39c_after':cleared,'effect_remove_requested':removed}
 report={'image_sha256' :hashlib.sha256(DATA).hexdigest(),'entry':'0x1211db0','cases':cases,'original_start_section_cleanup':lifecycle,
         'adapter':'0x15bb820 notification output plus external effect disposal only; all gates, flag cleanup and Scene39c reset executed original instructions',
         'limitation':'passing this gate does not prove an overlay passes mouse input or renderer creation succeeded'}
 out=Path(__file__).resolve().parent/'evidence';(out/'movement-input-gates-native.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 cs=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
 ranges=((0x1211db0,0x187),(0x1214bd0,0x101),(0x1214e56,0x38),(0x11e257b,0x32),(0x11e25ee,0x22),(0x11e269b,0x10),(0x11e276a,0x12),(0x11e27fa,0xa),(0x12034e0,0xc),(0x1203f90,7),(0x12689c0,0x13),(0x14ea330,9),(0x120a3bd,0x12),(0x120a4d2,0x12),(0x11dff52,0xc),(0x12bc870,0x2a),(0x12b9a10,0x18),(0x11d3a10,0x1f),(0x813830,6))
 text='native-image.bin SHA256 '+report['image_sha256']+'\n'
 for start,size in ranges:text+='\n'+'\n'.join(f'{i.address:08x} {i.mnemonic:8} {i.op_str}' for i in cs.disasm(DATA[start-BASE:start-BASE+size],start))+'\n'
 (out/'movement-input-gates-disassembly.txt').write_text(text,encoding='utf-8')
 print(json.dumps({'cases':len(cases),'allowed':sum(c['allowed'] for c in cases)}))

if __name__=='__main__':main()

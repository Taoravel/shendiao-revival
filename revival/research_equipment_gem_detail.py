"""Original complete equipment parser with explicit original gem config adapter.

Original scalar/vector/list/map parsing, clearing and summation execute. Config
row copy/destruction use static vectors; this is not a complete GUI lifecycle.
"""
import json
from inspect_client import OUT
from research_equipment_detail_full import NativeEquipmentDetail


class NativeGemEquipmentDetail(NativeEquipmentDetail):
    def __init__(self,template=40104,prefix=1):
        self.gem_rows={}
        super().__init__(template,prefix)
        self.w(0x2945aec,0x57e0000)
        self.w(0x57e0558,0x57e1000)
        self.w(0x57e1008,0x500f300)
        rows=json.loads((OUT/'catalogs/knight.gsp.item.cgemeffect.json').read_text(encoding='utf-8'))
        for index,row in enumerate(rows):
            key=int(row['attributes']['id']);pointer=0x5740000+index*0x200
            self.gem_rows[key]=pointer
            self.emu.mem_write(pointer,bytes(0xd8));self.w(pointer,key)
            kinds=tuple(map(int,row['lists']['effecttype']));values=tuple(map(int,row['lists']['effect']))
            assert len(kinds)==len(values) and len(kinds)<=8
            self.w(pointer+0x18,pointer+0x100,pointer+0x100+4*len(kinds),pointer+0x100+4*len(kinds))
            self.w(pointer+0x28,pointer+0x140,pointer+0x140+4*len(values),pointer+0x140+4*len(values))
            self.w(pointer+0x100,*kinds);self.w(pointer+0x140,*values)

    def hook(self,uc,address,size,user):
        esp,ecx,_,_=self.regs;sp=uc.reg_read(esp)
        if address==0x500f300:
            key=self.r(sp+4)
            if key not in self.gem_rows:raise ValueError('Missing original gem config row')
            self.ret(4,self.gem_rows[key])
        elif address==0xcd0b30:
            target,source=uc.reg_read(ecx),self.r(sp+4)
            uc.mem_write(target,bytes(uc.mem_read(source,0xd8)))
            self.ret(4,target)
        elif address==0xa00730:self.ret()
        else:super().hook(uc,address,size,user)

    def parse(self,payload):
        result=super().parse(payload)
        head=self.r(self.obj+0x9c);node=self.r(head);gems=[]
        while node!=head:
            gems.append(self.r(node+8));node=self.r(node)
            assert len(gems)<=100
        result['gems']=gems;result['gem_effects']=self.properties(0xa4)
        return result

"""Read-only inspection of player initialization from the mapped native image."""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path
from native_inspect import BASE,DATA,disasm
from research_auth import hits
from capstone import Cs,CS_ARCH_X86,CS_MODE_32

OUT=Path(__file__).parent/'evidence'

def provider_refs():
    for offset in (0xe18,0xe20,0xd74):
        print('displacement',hex(offset))
        raw=offset.to_bytes(4,'little')
        for addr in hits(raw):
            if 0x850000<addr<0x8a0000:
                print(hex(addr))
                disasm(addr-7,24)

def catalogs():
    root=Path(__file__).parent/'catalogs'
    for file in ['knight.gsp.role.schoolinfo.json','knight.gsp.role.crolecolor.json','knight.gsp.role.createroleconfig.json']:
        rows=json.loads((root/file).read_text(encoding='utf-8'))
        matches=[x for x in rows if any(str(v) in ('11','1010109','1') for v in x.get('attributes',{}).values())]
        print(file,json.dumps(matches[:8],ensure_ascii=False))

def verify_candidate():
    root=Path(__file__).parent/'catalogs'
    def rows(name):return json.loads((root/('knight.gsp.role.'+name+'.json')).read_text(encoding='utf-8'))
    def find(name,key):
        matches=[x for x in rows(name) if x.get('attributes',{}).get('id')==str(key)]
        assert len(matches)==1,(name,key,len(matches))
        return matches[0]
    school=find('schoolinfo',11)
    masters=find('schoolmasterskillinfo',11)
    level=find('cresmoneyconfig',1)
    character=find('createroleconfig',9)
    assert character['attributes']['color1']=='1010109'
    assert '11' in character['lists']['schools']
    result={'method':'native early lookup keys cross-checked against recovered original catalogs',
            'candidate':{'level':1,'school':11,'shape':1010109},
            'school_info':school['attributes'],
            'school_master_skill_info':masters['attributes'],
            'level_resource_money_config':level['attributes'],
            'create_role':{'id':9,'name':character['attributes']['name'],'color1':character['attributes']['color1'],'schools':character['lists']['schools']},
            'checks_passed':5,
            'scope':'catalog keys and create selection compatibility only; not full SEnterWorld/renderer execution'}
    attr=json.loads((root/'knight.gsp.item.cattributedesconfig.json').read_text(encoding='utf-8'))
    result['property_names']=[x['attributes'] for x in attr if x.get('attributes',{}).get('id') in ('60','70','140','150','640')]
    path=OUT/'world-player-candidate.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(path)
    return result

def evidence():
    path=OUT/'world-player-disassembly.txt'
    with path.open('w',encoding='utf-8') as f,contextlib.redirect_stdout(f):
        print('image sha256',hashlib.sha256(DATA).hexdigest())
        for va,size in [(0x8337c0,0x250),(0x833a55,0x240),(0x833ef3,0xc0),(0x89e660,0x20),(0x89e790,0x20),(0x11da380,0x100),(0xd43da4,0x48),(0xd43bab,0x31),(0xd0a940,0x50),(0xd40020,0x50)]:
            print('\nRANGE',hex(va))
            disasm(va,size)
        print('\nUTF16 TABLE IDENTITIES')
        for addr in (0x225e848,0x225e890,0x225e150):
            end=addr-BASE
            while DATA[end:end+2]!=b'\0\0':end+=2
            print(hex(addr),DATA[addr-BASE:end].decode('utf-16-le'))
    print(path)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--provider-refs',action='store_true')
    p.add_argument('--catalogs',action='store_true')
    p.add_argument('--evidence',action='store_true')
    p.add_argument('--verify-candidate',action='store_true')
    a=p.parse_args()
    if a.provider_refs:provider_refs()
    if a.catalogs:catalogs()
    if a.evidence:evidence()
    if a.verify_candidate:verify_candidate()

if __name__=='__main__':main()

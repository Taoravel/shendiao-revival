"""Family CourseInfo checked against the original serializers, without GUI."""
import struct,json,hashlib,re
from dataclasses import replace
import faction_protocol as p
from native_inspect import DATA
from verify_social_native import native_payload
from inspect_client import OUT,write_json


def octets_vector(values,pointer=0x5007000):
    rows=[];buffers=[]
    for value in values:
        payload=value.encode('utf-16-le')
        rows.append(struct.pack('<II',0x224c100,pointer+12))
        buffers.append((pointer-0x5001000,struct.pack('<III',len(payload),len(payload),1)+payload))
        pointer+=(len(payload)+12+31)&~31
    return b''.join(rows),buffers


def main():
    course=p.FamilyCourse(4,('2026-10-24 04:00:00','新族长甲'))
    values,buffers=octets_vector(course.parameters)
    actual=native_payload(0xed7910,scalars=[(4,4)],
        raw=[(0xc,struct.pack('<III',0x5005000,0x5005000+len(values),0x5005000+len(values))),(0x4000,values),*buffers])
    assert p.family_course(course)==actual
    assert actual==struct.pack('>i',4)+b'\x02\x26'+course.parameters[0].encode('utf-16-le')+b'\x08'+course.parameters[1].encode('utf-16-le')
    original=p.FamilyView(1,'家族甲','同心协力','创始人甲',1,3000000)
    assert p.family_data(original)[-1:]==b'\0'
    history=(p.FamilyCourse(1,('2026-10-24 04:00:00',)),course)
    enriched=replace(original,history=history)
    assert p.family_data(enriched)==p.family_data(original)[:-1]+b'\x02'+b''.join(p.family_course(row) for row in history)
    for courses in (history,(course,)*100):
        rows=[];nested=[]
        for index,item in enumerate(courses):
            start=0x5080000+index*0x100
            vector,buffers=octets_vector(item.parameters,0x5009000+index*0x1000)
            rows.append(struct.pack('<6I',0x22838c8,item.template_id,0,start,start+len(vector),start+len(vector)))
            nested.extend([(start-0x5001000,vector),*buffers])
        end=0x5005000+len(rows)*24
        actual_full=native_payload(0xed7340,[(8,original.founder_name),(0x24,original.name),(0x40,original.aim)],
            [(4,1),(0x5c,1),(0x60,3000000)],raw=[(0x84,struct.pack('<III',0x5005000,end,end)),
            (0x4000,b''.join(rows)),*nested])
        assert actual_full==p.family_data(replace(original,history=courses))
    for row in (p.FamilyCourse(True,('日期',)),p.FamilyCourse(8,('日期',)),p.FamilyCourse(4,('日期',)),
                p.FamilyCourse(1,['日期']),p.FamilyCourse(1,('日期\0',))):
        try:p.family_course(row)
        except ValueError:pass
        else:raise AssertionError('Malformed family course accepted')
    for courses in ([course],(course,)*101):
        try:p.family_data(replace(original,history=courses))
        except ValueError:pass
        else:raise AssertionError('Mutable or unbounded family course vector accepted')
    catalog=json.loads((OUT/'catalogs/knight.gsp.faction.cfamilyprogress.json').read_text(encoding='utf-8'))
    templates={int(row['attributes']['id']):row['attributes']['content'] for row in catalog}
    assert set(templates)==set(range(1,8))
    for key,value in templates.items():assert set(re.findall(r'\$parameter(\d+)\$',value))==({'1'} if key==1 else {'1','2'})
    result=dict(passed=['CourseInfo original marshal preserves template ID and nonempty UTF16 octet vector',
        'original full FamilyData marshal matches two and 100 nonempty CourseInfo rows; legacy empty layout retained',
        'original seven template parameter counts match; malformed/mutable/oversized histories are refused'],
        image_sha256=hashlib.sha256(DATA).hexdigest(),native_gui_verified=False,live_server_changed=False,
        historical_server_date_format_verified=False)
    write_json(OUT/'evidence/family-history-native-verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()

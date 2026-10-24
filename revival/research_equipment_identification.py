"""Read-only original parser comparison for an explicit clean detail bit.

This does not infer the original server's hidden/random generation timing.
"""
from dataclasses import replace
from equipment_detail import DetailRules,encode
from equipment_condition import EquipmentRules
from research_equipment_detail_full import NativeEquipmentDetail
from inspect_client import OUT,write_json
import json


def main():
    rules=DetailRules.load();condition=EquipmentRules.load().generate()
    items={int(r['attributes']['id']):r['attributes'] for r in json.loads((OUT/'catalogs/knight.gsp.item.citemattr.json').read_text(encoding='utf-8'))}
    cases=[]
    for slot in range(6):
        template=next(key for key in sorted(rules.templates) if (int(items[key]['itemtypeid'])>>4)&15==slot)
        detail=rules.generate(template);native=NativeEquipmentDetail(template)
        unknown=encode(template,replace(detail,identified=0),condition,rules)
        known=encode(template,replace(detail,identified=1),condition,rules)
        assert unknown[4:]==known[4:]
        before=native.parse(unknown);after=native.parse(known)
        assert (before['identified'],after['identified'])==(0,1)
        assert before['properties']==after['properties']==sorted(detail.base_properties)
        assert {k:v for k,v in before.items() if k!='identified'}=={k:v for k,v in after.items() if k!='identified'}
        cases.append({'slot':slot,'template':template,'before':before,'after':after,'only_wire_first_BE32_changed':True})
    write_json(OUT/'evidence/equipment-identification-readonly.json',{'source_status':'client_verified',
        'scope':'original full parser and supplied explicit clean payload, not original server identification business rules',
        'cases':cases,'parser_store':'107d9db..107d9ef first BE32 -> EquipObject+58; complete107d960 consumes both states and supplied property map',
        'production_writes':False,'live_server_changed':False,'native_gui_verified':False,
        'unknown':['original server random property generation before/at identification','original NPC charging/authorization','original unidentified tooltip visibility/eligibility semantics']})
    print('PASS six original full clean parsers accept bit0/1 with exactly unchanged supplied properties; no server-generation inference')


if __name__=='__main__':main()

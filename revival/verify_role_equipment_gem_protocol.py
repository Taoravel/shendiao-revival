"""Complete 27-field world refresh through original codec and attr assignment."""
from dataclasses import replace
import struct
from role_attributes import RoleAttributes
from role_growth import GrowthState
from role_equipment import EquipmentRoleSnapshot
from role_equipment_gem_storage import GemEquipmentProfile
from item_effects import VitalState
from role_equipment_gem_protocol import growth_refresh
from role_attribute_protocol import growth_refresh as core_refresh
from wire import read_compact
from verify_role_equipment import original_map
from verify_role_resource_protocol import native_assignment
from native_gameplay_probe import probe


def main():
    rid=9001
    attrs=RoleAttributes(rid,10,0,0,'2026-10-23.attributes.1',(10,10,10,10,10),203,100,124,118,140,50,21,100,59)
    core=EquipmentRoleSnapshot(attrs,VitalState(rid,4,70,203,40,100),9,0,
        '2026-10-24.role-equipment-gems.1',30,30)
    growth=GrowthState(rid,10,0,10,0,None,(0,)*5,(0,)*5,0,0,'2026-10-23.role.1')
    extras=((350,-2),(360,4),(370,5),(380,7),(1130,8),(1530,11))
    profile=GemEquipmentProfile(core,extras,(),((1,1),))
    kind,body=growth_refresh(growth,profile)
    assert kind==0xc32c8 and read_compact(body)==(27,1)
    values=original_map(body)  # actual original marshal and unmarshal
    assert all(values[key]==value for key,value in extras)
    base=original_map(core_refresh(growth,core)[1])
    assert {key:value for key,value in values.items() if key not in dict(extras)}==base
    assert (values[60],values[70],values[140],values[150],values[1230],values[1240])==(70,40,203,100,30,30)
    for key,value in extras:assert native_assignment(key,value)==value&0xffffffff
    def refused(action):
        try:action()
        except ValueError:return
        raise AssertionError('Incomplete or inexact gem refresh accepted')
    refused(lambda:growth_refresh(growth,replace(profile,extras=extras[:-1])))
    refused(lambda:growth_refresh(growth,replace(profile,extras=tuple(reversed(extras)))))
    refused(lambda:growth_refresh(growth,replace(profile,extras=((350,True),)+extras[1:])))
    refused(lambda:growth_refresh(growth,replace(profile,extras=((350,16777217),)+extras[1:])))
    refused(lambda:growth_refresh(growth,replace(profile,core=replace(core,equipment_policy='old'))))
    try:probe(0xec3590,0xec36b0,0xec3730,payload=body[:-1])
    except ValueError:pass
    else:raise AssertionError('Original decoder accepted truncated 27-field map')
    print('PASS 27-field original marshal/unmarshal; all21 existing fields preserved; '
        'signed6 extras assigned by original generic branch; invalid/truncated refuses; no GUI claim')


if __name__=='__main__':main()

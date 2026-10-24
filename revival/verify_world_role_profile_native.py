"""Full explicit entry profile: native integer slots, five stats and potential."""
from dataclasses import replace
import struct
from inspect_client import OUT,write_json
from item_effects import VitalState
from native_gameplay_probe import probe
from role_attributes import AttributeBaseline,derive_attributes,load_attribute_rules
from role_attribute_storage import RoleAttributeSnapshot
from role_growth import GrowthState
from world_protocol import world_snapshot


def refused(action):
    try: action()
    except ValueError: return
    raise AssertionError('Missing or mismatched committed entry profile accepted')


def main():
    rules=load_attribute_rules()
    role_id=2**40
    growth=GrowthState(role_id,2,61,1,0,None,(1,1,1,1,1),(0,1,2,3,4),7,1,rules.growth_policy)
    baseline=AttributeBaseline(role_id,1,0,(10,20,30,40,50),(100,100,20,5,40,20,10,20,5))
    attrs=derive_attributes(baseline,growth,rules)
    snapshot=RoleAttributeSnapshot(attrs,VitalState(role_id,3,80,attrs.hp_max,46,attrs.mp_max))
    role=dict(id=role_id,name='完整入场',level=2,school=111,shape=1010109,experience=61)
    body=world_snapshot(role,snapshot,growth_snapshot=growth,intro_discriminator=1)
    _,decoded=probe(0xfe4160,0xfe45f0,0xfe4630,payload=body)
    assert struct.unpack_from('<5h',decoded,0xd4)==(11,22,33,44,55)
    assert struct.unpack_from('<i',decoded,0xe0)[0]==7
    assert struct.unpack_from('<5i',decoded,0xe4)==(0,0,0,0,0)
    assert struct.unpack_from('<Q',decoded,0xf8)[0]==61
    assert struct.unpack_from('<Q',decoded,0x48)[0]==1
    assert struct.unpack_from('<5i',decoded,0x50)==(80,attrs.hp_max,attrs.hp_max,46,attrs.mp_max)
    assert struct.unpack_from('<7i',decoded,0x6c)==(
        attrs.hit,attrs.physical_attack,attrs.physical_defense,attrs.speed,attrs.dodge,attrs.magic_attack,attrs.magic_defense)
    refused(lambda:world_snapshot(role,growth_snapshot=growth))
    refused(lambda:world_snapshot(dict(role,id=role_id+1),snapshot,growth_snapshot=growth))
    refused(lambda:world_snapshot(dict(role,level=3),snapshot,growth_snapshot=growth))
    refused(lambda:world_snapshot(dict(role,experience=62),snapshot,growth_snapshot=growth))
    refused(lambda:world_snapshot(role,snapshot,growth_snapshot=replace(growth,revision=2)))
    # Compatibility callers do not fabricate growth/potential from a plain profile.
    _,legacy=probe(0xfe4160,0xfe45f0,0xfe4630,payload=world_snapshot(role,snapshot))
    assert struct.unpack_from('<5h',legacy,0xd4)==(0,0,0,0,0)
    assert struct.unpack_from('<i',legacy,0xe0)[0]==0
    report=dict(native_five_stats=(11,22,33,44,55),native_potential=7,
        native_vitals=(80,attrs.hp_max,attrs.hp_max,46,attrs.mp_max),
        native_combat_slots_verified=True,unknown_following_i32_remain_zero=True,
        experience_and_intro_preserved=True,role_level_experience_revision_mismatch_rejected=True,
        compatibility_profile_preserved=True,shared_runtime_tested=False,live_server_changed=False,gui_verified=False)
    write_json(OUT/'evidence/world-role-profile-native.json',report)
    print(report)


if __name__=='__main__':main()

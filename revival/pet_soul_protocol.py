"""Original pet soul complete-map refresh and exact removal intent.

Pure immutable bytes only. The role owner must obtain a known complete profile
and encode before committing; the connection owner delivers after commit.
Incremental c0807 cannot create/delete slots, so it is not an exposed writer.
"""
import struct
from pet_souls import SoulBean,SoulProfile
from wire import compact


def encode_bean(bean):
    if type(bean) is not SoulBean:raise ValueError('Explicit six-field soul bean required')
    return struct.pack('>6i',bean.item_id,bean.cumulative_exp,bean.soul_skill_id,bean.raw4,bean.raw5,bean.raw6)


def full_refresh(profile):
    """Known complete map, including explicitly known empty, never missing=empty."""
    if type(profile) is not SoulProfile:raise ValueError('Explicit complete pet soul profile required')
    return 0xc0803,struct.pack('>i',profile.pet_id)+compact(len(profile.entries))+b''.join(
        struct.pack('>i',slot)+encode_bean(bean) for slot,bean in profile.entries)


def decode_remove(kind,payload):
    """Intent only; no asset ownership, soul existence, fee or server authority."""
    if type(kind) is not int or kind!=0xc0805 or type(payload) is not bytes or len(payload)!=8:
        raise ValueError('Exact original pet soul removal request required')
    pet,slot=struct.unpack('>ii',payload)
    if pet<=0 or not 1<=slot<=5:raise ValueError('Positive owned pet key and original slot1..5 required')
    return pet,slot

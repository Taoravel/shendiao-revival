"""Original CYuanHunZhuObject four-field tips, separate from worn PetSoul.

This pure data Module preserves signed opaque fields. Its worn projection is
for display only: the original nonzero marker loses raw6 information and is
not a complete item flag word or permission to reconstruct/normalize assets.
"""
from dataclasses import dataclass
import struct
from pet_souls import SoulBean
from wire import octets


@dataclass(frozen=True)
class OrbTips:
    cumulative_exp: int
    soul_skill_id: int
    raw5: int  # Original wire field3: corresponds to worn bean field5.
    raw4: int  # Original wire field4: corresponds to worn bean field4.

    def __post_init__(self):
        for index,value in enumerate((self.cumulative_exp,self.soul_skill_id,self.raw5,self.raw4)):
            if type(value) is not int or not (0 if index<2 else -0x80000000)<=value<=0x7fffffff:
                raise ValueError('Four explicit known native soul orb fields required')


def encode_tips(tips):
    """The inner PetSoulPerlItemTipsOctets only; no outer SItemTips/container."""
    if type(tips) is not OrbTips:raise ValueError('Explicit four-field carried orb data required')
    return struct.pack('>4i',tips.cumulative_exp,tips.soul_skill_id,tips.raw5,tips.raw4)


def decode_tips(payload):
    if type(payload) is not bytes or len(payload)!=16:
        raise ValueError('Exact original16-byte soul orb tips required')
    return OrbTips(*struct.unpack('>4i',payload))


def carried_tip_reply(item_key,tips):
    """Original column1 SItemTips, from caller-verified CURRENT owned data.

    Encoding is not item authority. The future role controller verifies source
    and original container, encodes before commit, and delivers after commit.
    """
    if type(item_key) is not int or not 0<item_key<=0x7fffffff:raise ValueError('Positive current carried item key required')
    return 0xc03fe,struct.pack('>ii',1,item_key)+octets(encode_tips(tips))


def display_tips_from_worn(bean):
    """Native1402f90 display mapping; deliberately exposes no inverse factory."""
    if type(bean) is not SoulBean:raise ValueError('Complete six-field worn soul required')
    return OrbTips(bean.cumulative_exp,bean.soul_skill_id,bean.raw5,bean.raw4),int(bean.raw6!=0)


def bag_marker(flags):
    """Native parser107a020 marker from explicit item flags; not raw6 itself."""
    if type(flags) is not int or not 0<=flags<=0xffffffff:raise ValueError('Explicit original item flags required')
    return flags&1

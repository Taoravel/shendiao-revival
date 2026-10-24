"""Current integer pet messages; exact ratios stay in the source snapshot.

The old generic float-map consumer truncates fractions. The return value names
the five unresolved ratio-display IDs, so a caller cannot claim full native
ratio support merely because the safe integer messages have been encoded.
"""
from dataclasses import dataclass
import struct
from inventory import pet_record,REFRESH_PET
from wire import compact
from pet_soul_totals_storage import PetSoulProfile,read_profile


@dataclass(frozen=True)
class PetSoulMessages:
    profile: PetSoulProfile
    messages: tuple
    ratio_display_pending: tuple


def current_messages(db,inventory,rules,pet):
    profile=read_profile(db,inventory,rules,pet)
    snapshot=inventory.immutable_snapshot_transaction(db)
    current=next((p for p in snapshot.pets if p.id==pet),None)
    if current is None or current.progress!=profile.progress:raise ValueError('Same current settled native pet source required')
    pairs=[]
    for key,n,d in profile.progress.attributes.extra_values[:2]:
        if d!=1 or not 0<=n<=0x7fffffff or struct.unpack('>f',struct.pack('>f',n))[0]!=n:
            raise ValueError('Final hit/dodge requires exactly representable native integer values')
        pairs.append((key,n))
    values=struct.pack('>ii',1,pet)+compact(2)+b''.join(struct.pack('>if',key,n) for key,n in pairs)
    messages=((REFRESH_PET,pet_record(vars(current))),(0xc32c9,values))
    return PetSoulMessages(profile,messages,(740,1550,1560,1580,1590))

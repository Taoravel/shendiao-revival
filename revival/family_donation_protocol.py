"""Original generic selector shapes with an explicit server-owned window.

This module chooses no historical donation context/type/opaque values. A root
caller supplies an admitted window and separately owns family/NPC access. It
must not create the expected window from the incoming packet itself.
"""
from dataclasses import dataclass
from task_item_protocol import (C_SUBMIT_2_NPC,S_SUBMIT_2_NPC,
    encode_npc_submission_prompt,decode_npc_item_submission)

SILVER_BOX_TEMPLATES=(36076,36201)
MAX_NATIVE_UNITS=5  # original 0x1684710 walks five selected 0x138-byte rows


@dataclass(frozen=True)
class DonationWindow:
    context_id: int
    npc_key: int
    submit_type: int
    opaque: int

    def __post_init__(self):
        if type(self.npc_key) is not int or not 0<self.npc_key<2**63:
            raise ValueError('family_donation_window_npc_required')
        encode_npc_submission_prompt(self.context_id,self.npc_key,self.submit_type,SILVER_BOX_TEMPLATES,self.opaque)


def prompt(window):
    if not isinstance(window,DonationWindow):raise ValueError('server_family_donation_window_required')
    return S_SUBMIT_2_NPC,encode_npc_submission_prompt(window.context_id,window.npc_key,window.submit_type,
        SILVER_BOX_TEMPLATES,window.opaque)


def validate_units(units,maximum_count):
    if (type(maximum_count) is not int or not 0<maximum_count<2**31
            or type(units) is not tuple or not 1<=len(units)<=MAX_NATIVE_UNITS
            or any(type(row) is not tuple or len(row)!=2
                or any(type(v) is not int or not 0<v<2**31 for v in row) for row in units)
            or len({row[0] for row in units})!=len(units)
            or sum(row[1] for row in units)>maximum_count):
        raise ValueError('invalid_family_donation_selected_units')
    return sum(row[1] for row in units)


def decode_submission(body,window,*,maximum_count):
    if not isinstance(window,DonationWindow) or type(body) is not bytes:
        raise ValueError('server_family_donation_window_required')
    command=decode_npc_item_submission(body)
    if (command.task_id,command.npc_key,command.submit_type)!=(window.context_id,window.npc_key,window.submit_type):
        raise ValueError('family_donation_window_mismatch')
    validate_units(command.units,maximum_count)
    return command

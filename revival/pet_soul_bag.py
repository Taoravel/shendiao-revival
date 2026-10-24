"""Current carried bag plus separately addressed known orb detail messages.

The original Item is48 scalar bytes; CYuanHunZhuObject's four fields belong to
SItemTips, not an inserted Item payload. No connections/commits/source repair
or sends. Caller freezes these messages before commit and delivers afterward.
"""
import struct
from inventory import item_record
from currency import read_wallet
from pet_soul_item_storage import OrbRules
import pet_soul_item_storage as orbs
from wire import compact


def current_messages(db,inventory,rules,currency_rules):
    """Known orb sources are mandatory; no zero tips or omitted unknown orbs.

    Other item records use the existing public Inventory encoder unchanged.
    This optional Adapter must replace current orb-containing bag producers
    together with current detail routing before any shared activation.
    """
    if type(rules) is not OrbRules:raise ValueError('Frozen original orb rules required')
    snapshot=inventory.immutable_snapshot_transaction(db)
    wallet=read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,currency_rules)
    cash=next((row.balance for row in wallet if row.currency=='cash'),None)
    if type(cash) is not int or not 0<=cash<2**63:raise ValueError('Explicit current carried cash required')
    records=[];tips=[]
    for item in snapshot.items:
        if item.equipment_slot is not None:continue
        record=item_record(vars(item))
        if len(record)!=48:raise ValueError('Original scalar Item layout changed; explicit review required')
        if item.template_id in rules.souls.souls:
            basis=orbs.read(db,inventory,rules,item.id)
            if basis is None or basis.inventory_revision!=snapshot.inventory_revision or basis.item!=item:
                raise ValueError('Current complete same-transaction carried orb source required')
            flags=basis.source.nonbinding_flags|item.binding
            record=record[:4]+struct.pack('>I',flags)+record[8:]
            tips.append(orbs.tip_message(db,inventory,rules,item.id))
        records.append(record)
    body=struct.pack('>iQi',1,cash,snapshot.bag_capacity)+compact(len(records))+b''.join(records)+b'\0'
    return ((0xc03f3,body),)+tuple(tips)

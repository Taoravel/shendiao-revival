"""Native ordinary NPC repair -> existing equipment/currency owner transaction."""
from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
import secrets
import struct
import time
from currency import read_wallet
from currency_protocol import encode_currency_balance
from role_resource_storage import ResourceNotInitialized,read_role_resources,apply_resource_transition
from role_resource_plan import plan_resource_caps
from role_equipment_storage import current_equipment_totals,current_resource_profile
from role_equipment import resource_caps_from_projection

REPAIR_EQUIPMENT=0xc0413


@dataclass(frozen=True)
class RepairIntent:
    service: object
    column: int
    item_key: int


def decode_repair(body):
    if type(body) is not bytes or len(body)!=20:
        raise ValueError('CRepairEquipItem requires 20 bytes')
    method,npc_key,column,item_key=struct.unpack('>iqii',body)
    if method!=2 or npc_key<0 or column not in (1,4) or item_key<=0:
        raise ValueError('Unsupported repair method, column or item')
    return npc_key,column,item_key


def plan(resources,body,proof,current,*,request_id,now_ms,deadline_ms):
    key,column,item_key=decode_repair(body)
    service=resources.services.plan(struct.pack('>qi',key,513),proof,current,
        request_id=request_id,now_ms=now_ms,deadline_ms=deadline_ms)
    if service.handler!='equipment.repair':raise ValueError('NPC cannot repair equipment')
    return RepairIntent(service,column,item_key)


def repair(accounts,inventory,intent,precommit=None,*,draw_source=secrets.randbelow,
           resource_rules=None,equipment_rules=None):
    """draw_source is trusted server dependency; no client draw crosses this seam.

    Receipt lookup precedes the random draw and equipment mutation. Current
    condition/wallet is returned on replay, never a historical repair display.

    Optional trusted precommit(db, inventory, current_inventory_snapshot) returns
    immutable logical messages. It runs after mutation/replay reads, inside the
    SAME transaction, before commit. Project final role attributes and encode
    them there; failure rolls back repair, cash and every receipt. It must not
    commit, open a nested connection, publish owner state or send to a Session.
    The fourth argument is positional for the bounded role I/O call surface.

    Optional startup resource/equipment rules transfer caps INSIDE this same
    transaction for an already migrated role. A paid replay only reads current
    profile; it never rebuilds a historical repair transition or source update.
    """
    if precommit is not None and not callable(precommit):raise ValueError('Trusted repair precommit callable required')
    if (resource_rules is None)!=(equipment_rules is None):
        raise ValueError('Repair resource and equipment rules must be injected together')
    service=intent.service
    if ((service.role_id,service.login_epoch)!=(inventory.role_id,inventory.epoch)
            or service.handler!='equipment.repair'):
        raise ValueError('NPC repair owner mismatch')
    fingerprint=hashlib.sha256(json.dumps(('repair',accounts.npc_gameplay.revision,service.npc_id,
        intent.column,intent.item_key),separators=(',',':')).encode()).hexdigest()
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if int(time.monotonic()*1000)>=service.deadline_ms:raise ValueError('NPC repair expired')
        read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,accounts.currency_rules)
        old=db.execute('SELECT fingerprint FROM npc_command_receipts WHERE role_id=? AND request_id=?',
            (inventory.role_id,service.request_id)).fetchone()
        if old and old[0]!=fingerprint:raise ValueError('NPC repair retry intent conflict')
        state=inventory.immutable_snapshot_transaction(db)
        item=next((i for i in state.items if i.id==intent.item_key),None)
        resources=None
        if resource_rules is not None:
            try:resources=read_role_resources(db,inventory.account_id,inventory.role_id,inventory.epoch,resource_rules)
            except ResourceNotInitialized:pass
            else:
                if precommit is None:raise ValueError('Migrated repair requires final profile precommit encoding')
                # Strict source before mutation prevents a repair from quietly
                # adopting unrelated pending asset/growth changes.
                current_resource_profile(db,inventory.account_id,inventory.role_id,inventory.epoch,state,
                    equipment_rules=equipment_rules,resource_rules=resource_rules)
        if not old:
            if item is None or (4 if item.equipment_slot is not None else 1)!=intent.column:
                raise ValueError('Repair item is not in the requested owned column')
            if item.condition is None:raise ValueError('Unknown legacy equipment condition')
            draw=draw_source(1000)
            identity='nr:'+hashlib.sha256(service.request_id.encode()).hexdigest()
            inventory.repair_equipment(db,item.id,inventory.epoch,identity,item.condition.version,draw,accounts.currency_rules)
            if resources is not None:
                snapshot=inventory.immutable_snapshot_transaction(db)
                totals=current_equipment_totals(db,inventory.account_id,inventory.role_id,inventory.epoch,snapshot,equipment_rules)
                transition=plan_resource_caps(resources,resource_caps_from_projection(totals),'equipment_repair',resource_rules)
                result=apply_resource_transition(db,inventory.account_id,inventory.role_id,inventory.epoch,
                    transition,identity,rules=resource_rules,equipment_rules=equipment_rules)
                if result.replayed:raise ValueError('Repair resource receipt exists without its domain receipt')
            db.execute('INSERT INTO npc_command_receipts VALUES(?,?,?)',(inventory.role_id,service.request_id,fingerprint))
        if resources is not None:
            current_resource_profile(db,inventory.account_id,inventory.role_id,inventory.epoch,
                inventory.immutable_snapshot_transaction(db),equipment_rules=equipment_rules,resource_rules=resource_rules)
        messages=list(inventory.equipment_refresh(db,item.id)) if item is not None else []
        wallet=read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,accounts.currency_rules)
        messages.extend(encode_currency_balance(r.currency,r.balance) for r in wallet if r.currency=='cash')
        if precommit is not None:
            projected=precommit(db,inventory,inventory.immutable_snapshot_transaction(db))
            if (type(projected) is not tuple or any(type(row) is not tuple or len(row)!=2
                    or type(row[0]) is not int or not 0<=row[0]<=0xffffffff or type(row[1]) is not bytes
                    for row in projected)):
                raise ValueError('Repair precommit must return immutable encoded logical messages')
            messages.extend(projected)
        return messages

"""NPC gameplay Adapter: startup snapshots and fenced atomic owner transactions."""
from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
import struct
import time
from types import MappingProxyType
from inspect_client import OUT
from inventory import AssetChange, QUERY_BAG, MOVE_ITEM
import npc_depot
import npc_repairs
import npc_shop_sales
import npc_recovery
import npc_role_healing
from currency import CurrencyChange, apply_currency, read_wallet
from currency_protocol import encode_currency_balance,encode_balance
from npc_services import ServiceBinding, load_services
from npc_shop_payments import load_shop_payments
from world_entity_protocol import VISIT_NPC_REPLY
from task_dialog_protocol import decode_visit_npc
from world_catalog import maps,maze_grids,valid_position
from world_collision import maze_clear
from npc_transactions import precommit_messages

BUY_FROM_NPC = 0xc232c
NPC_DEPOT_TYPES = frozenset((npc_depot.OPEN_DEPOT,)) | npc_depot.MONEY_TYPES
NPC_GAMEPLAY_TYPES = frozenset((BUY_FROM_NPC,npc_depot.OPEN_DEPOT,npc_repairs.REPAIR_EQUIPMENT,
                              npc_shop_sales.SELL_ITEMS,npc_shop_sales.REPURCHASE))
NPC_GAMEPLAY_TYPES = NPC_GAMEPLAY_TYPES | {npc_recovery.RECOVERY} | NPC_DEPOT_TYPES


@dataclass(frozen=True)
class NpcResources:
    revision: str
    services: object
    stock: object
    prices: object
    currency: str
    binding: int
    quantity_limit: int
    depot_capacity: int
    routes: object
    payments: object


@dataclass(frozen=True)
class Purchase:
    service: object
    item_id: int
    quantity: int
    unit_price: int
    mode: int = 0


@dataclass(frozen=True)
class TransportRoute:
    source_map: int
    allowed_schools: tuple
    target: tuple


def prepare(accounts):
    policy=json.loads((OUT/'design/npc-services-v1.json').read_text(encoding='utf-8'))
    rows=json.loads((OUT/'catalogs/knight.gsp.item.npcsellitem.json').read_text(encoding='utf-8'))
    definitions=accounts.npc_resources[1]
    stock={int(r['attributes']['id']):tuple(map(int,r['lists'].get('items',()))) for r in rows
           if int(r['attributes']['id']) in definitions}
    prices={key:int(value['price']) for key,value in accounts.inventory_config.items.items()
            if value.get('price','').isdigit() and int(value['price'])>0}
    bindings=tuple(ServiceBinding(npc,2,'shop.open','designed',
        'designed NPC/service association; client_verified npcsellitem stock and native service2 branch1636d38')
        for npc,items in stock.items() if items)
    bindings+=tuple(ServiceBinding(npc,6,'warehouse.open','designed',
        'design/npc-services-v1.json#warehouse; original NPC config and service6 label')
        for npc in policy['warehouse']['npc_ids'])
    if (policy['repair']['method'],policy['repair']['service_id'])!=(2,513):
        raise ValueError('Unsupported NPC repair method policy')
    bindings+=tuple(ServiceBinding(npc,513,'equipment.repair','designed',
        'design/npc-services-v1.json#repair; official weapon/armor/accessory shops')
        for npc in policy['repair']['npc_ids'])
    bindings+=npc_shop_sales.prepare(accounts,policy)
    bindings+=npc_recovery.prepare(accounts,policy)
    bindings+=npc_role_healing.prepare(accounts)
    schools=json.loads((OUT/'catalogs/knight.gsp.role.schoolinfo.json').read_text(encoding='utf-8'))
    routes={}
    for r in policy['transport']['routes']:
        key=(r['npc_id'],r['service_id'])
        if key in routes or r['npc_id'] not in definitions: raise ValueError('Invalid transport binding')
        source_map=r['source_map'];target=tuple(r['target'])
        allowed=tuple(int(s['attributes']['id']) for s in schools
                      if int(s['attributes'].get('schoolmapid',0))==source_map)
        if (not allowed or source_map==target[0] or not valid_position(target,maps())
                or not maze_clear(maze_grids()[target[0]],*target[1:],mask=1)):
            raise ValueError('Invalid transport target or faction policy')
        routes[key]=TransportRoute(source_map,allowed,target)
        bindings+=(ServiceBinding(*key,'transport.depart','designed',
            'design/npc-services-v1.json#transport; official faction system route'),)
    shop=policy['shop']
    if (shop['currency']!='cash' or shop['binding']!=0 or shop['supported_native_mode']!=0
            or not 1<=shop['quantity_limit']<=99):
        raise ValueError('Unsupported NPC shop policy')
    # Original295 only expands a local childservice menu. Its action leaves
    # retain the existing explicit trainer bindings and real recovery handlers.
    groups=tuple((npc,295) for npc in policy['recovery']['trainer_npc_ids'])
    resources=NpcResources(policy['revision'],load_services(bindings,menu_groups=groups),MappingProxyType(stock),
        MappingProxyType(prices),shop['currency'],shop['binding'],shop['quantity_limit'],policy['warehouse']['capacity'],
        MappingProxyType(routes),load_shop_payments())
    if not 1<=resources.depot_capacity<=4096: raise ValueError('Invalid warehouse capacity')
    with closing(accounts.connect()) as db,db:
        db.execute('''CREATE TABLE IF NOT EXISTS npc_command_receipts (
            role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
            fingerprint TEXT NOT NULL,PRIMARY KEY(role_id,request_id))''')
        npc_depot.prepare(db)
    accounts.npc_gameplay=resources


def transport_destination(resources,command,role_school):
    route=resources.routes.get((command.npc_id,command.service_id))
    if (command.handler!='transport.depart' or route is None
            or command.address.map_id!=route.source_map or role_school not in route.allowed_schools):
        raise ValueError('Transport faction or source map is not authorized')
    return route.target


def merge_menu(resources,messages,proof,current):
    result=[]
    for kind,body in messages:
        if kind==VISIT_NPC_REPLY:
            key,services,quests=decode_visit_npc(body)
            if key!=proof.entity_key or services:
                raise ValueError('NPC menu composition mismatch')
            body=resources.services.menu(proof,current,quest_ids=tuple(quests))
        result.append((kind,body))
    return result


def decode_purchase(body):
    if type(body) is not bytes or len(body)!=20:
        raise ValueError('CBuyItemFromNpc requires 20 bytes')
    key,item,quantity,mode=struct.unpack('>qiii',body)
    if key<0 or item<0 or not 1<=quantity<=99 or mode not in (0,1):
        raise ValueError('Unsupported or invalid ordinary NPC purchase')
    return key,item,quantity


def plan_purchase(resources,body,proof,current,*,request_id,now_ms,deadline_ms):
    key,item,quantity=decode_purchase(body)
    mode=struct.unpack_from('>i',body,16)[0]
    resources.payments.recipe(mode)
    service=resources.services.plan(struct.pack('>qi',key,2),proof,current,
        request_id=request_id,now_ms=now_ms,deadline_ms=deadline_ms)
    if (item not in resources.stock.get(proof.npc_id,()) or item not in resources.prices
            or quantity>resources.quantity_limit):
        raise ValueError('Item is unavailable from this NPC')
    return Purchase(service,item,quantity,resources.prices[item],mode)


def purchase(accounts,inventory,intent,precommit=None):
    resources=accounts.npc_gameplay
    service=intent.service
    payment=resources.payments.recipe(intent.mode)
    if (service.role_id,service.login_epoch)!=(inventory.role_id,inventory.epoch):
        raise ValueError('NPC purchase owner mismatch')
    if int(time.monotonic()*1000)>=service.deadline_ms:
        raise ValueError('NPC purchase deadline expired before persistence')
    if (service.service_id!=2 or service.handler!='shop.open'
            or intent.item_id not in resources.stock.get(service.npc_id,())
            or resources.prices.get(intent.item_id)!=intent.unit_price
            or type(intent.quantity) is not int or not 1<=intent.quantity<=resources.quantity_limit):
        raise ValueError('NPC purchase does not match startup stock')
    record=(resources.revision,service.npc_id,intent.item_id,intent.quantity,intent.unit_price)
    if intent.mode==1:
        record+=(payment.mode,payment.currency,payment.binding,resources.payments.revision)
    fingerprint=hashlib.sha256(json.dumps(record,separators=(',',':')).encode()).hexdigest()
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if int(time.monotonic()*1000)>=service.deadline_ms:
            raise ValueError('NPC purchase deadline expired waiting for storage')
        wallet=read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,accounts.currency_rules)
        old=db.execute('SELECT fingerprint FROM npc_command_receipts WHERE role_id=? AND request_id=?',
                       (inventory.role_id,service.request_id)).fetchone()
        if old and old[0]!=fingerprint:
            raise ValueError('NPC request reused with a different purchase')
        if not old:
            identity='npc:'+service.request_id
            cost=intent.unit_price*intent.quantity
            apply_currency(db,inventory.account_id,inventory.role_id,inventory.epoch,
                CurrencyChange(identity,payment.purpose,f'npc:{service.npc_id}:item:{intent.item_id}',
                    ((payment.currency,-cost),)),accounts.currency_rules)
            inventory.apply_settlement(db,AssetChange(identity,
                grants=((intent.item_id,intent.quantity,payment.binding),)))
            db.execute('INSERT INTO npc_command_receipts VALUES(?,?,?)',
                (inventory.role_id,service.request_id,fingerprint))
        projected=precommit_messages(precommit,db,inventory,replayed=old is not None)
        # Encode before commit; a serialization error rolls back payment/item/source together.
        messages=[inventory.equipment_bag_messages(db,inventory.epoch)[0]]
        wallet=read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,accounts.currency_rules)
        messages.extend(encode_currency_balance(row.currency,row.balance) for row in wallet
                        if row.currency==payment.currency)
        messages.extend(projected)
    return messages


def depot_operation(accounts,inventory,service,kind,body,precommit=None):
    resources=accounts.npc_gameplay
    if ((service.role_id,service.login_epoch)!=(inventory.role_id,inventory.epoch)
            or service.handler!='warehouse.open'):
        raise ValueError('Warehouse owner/service mismatch')
    money=kind in npc_depot.MONEY_TYPES
    if money and npc_depot.decode_money(kind,body)[0]!=service.entity_key:
        raise ValueError('Warehouse money NPC differs from authorized key')
    fingerprint=hashlib.sha256(json.dumps((resources.revision,service.npc_id,kind,body.hex()),
        separators=(',',':')).encode()).hexdigest()
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if int(time.monotonic()*1000)>=service.deadline_ms:
            raise ValueError('Warehouse operation expired')
        if not db.execute('SELECT 1 FROM npc_depot_profiles WHERE role_id=?',(inventory.role_id,)).fetchone():
            origin=db.execute('SELECT origin FROM role_restoration_origins WHERE role_id=?',
                              (inventory.role_id,)).fetchone()
            if origin!=('new_restoration_role',):
                raise ValueError('Legacy warehouse cash baseline requires explicit migration')
            npc_depot.initialize(db,inventory,0,'new_restoration_role')
        if kind==MOVE_ITEM or money:
            old=db.execute('SELECT fingerprint FROM npc_command_receipts WHERE role_id=? AND request_id=?',
                           (inventory.role_id,service.request_id)).fetchone()
            if old and old[0]!=fingerprint: raise ValueError('Warehouse request intent conflict')
            if not old:
                if money:
                    npc_depot.transfer_cash(db,inventory,service,kind,body,accounts.currency_rules,fingerprint)
                else:
                    npc_depot.move(db,inventory,body,resources.depot_capacity)
                    db.execute('INSERT INTO inventory_versions VALUES(?,1) ON CONFLICT(role_id) '
                               'DO UPDATE SET revision=revision+1',(inventory.role_id,))
                db.execute('INSERT INTO npc_command_receipts VALUES(?,?,?)',
                           (inventory.role_id,service.request_id,fingerprint))
            elif money:
                journal=db.execute('SELECT fingerprint FROM npc_depot_cash_journal WHERE role_id=? AND request_id=?',
                    (inventory.role_id,service.request_id)).fetchone()
                if journal!=(fingerprint,):raise ValueError('Warehouse transfer receipt audit mismatch')
        elif kind==QUERY_BAG:
            if len(body)!=12 or struct.unpack('>iQ',body) not in ((2,0),(2,inventory.role_id)):
                raise ValueError('Invalid warehouse query')
        elif kind!=npc_depot.OPEN_DEPOT:
            raise ValueError('Unsupported warehouse operation')
        projected=(precommit_messages(precommit,db,inventory,replayed=old is not None)
                   if kind==MOVE_ITEM else ())
        if money:
            wallet=read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,accounts.currency_rules)
            cash=next(r.balance for r in wallet if r.currency=='cash')
            return [encode_currency_balance('cash',cash),encode_balance('money_2',npc_depot.cash_balance(db,inventory))]
        return list(npc_depot.messages(db,inventory,resources.depot_capacity,include_carried=kind==MOVE_ITEM))+list(projected)


def initialize_depot(inventory,cash,origin):
    """Trusted owner migration only; there is deliberately no native packet route."""
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        npc_depot.initialize(db,inventory,cash,origin)

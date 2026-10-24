"""Native NPC sale/buyback with preserved instances and fenced role settlement."""
from contextlib import closing
from dataclasses import asdict,dataclass
from collections import defaultdict
import hashlib
import json
import struct
import time
from types import MappingProxyType
from inspect_client import OUT
from currency import CurrencyChange,apply_currency,read_wallet,WalletNotInitialized
from currency_protocol import encode_currency_balance
from inventory import item_record
from npc_services import ServiceBinding
from npc_depot import StoredItem,carried_items,take_carried,restore_carried
from wire import compact,read_compact,NeedMoreData
from equipment_condition import EquipmentCondition
from npc_transactions import precommit_messages

SELL_ITEMS=0xc232d
REPURCHASE=0xc232e
REPURCHASE_ITEMS=0xc0434


@dataclass(frozen=True)
class SaleRules:
    revision: str
    npc_ids: tuple
    explicit: object
    equipment: object
    capacity: int
    ttl_seconds: int
    cash_level: int


@dataclass(frozen=True)
class SaleIntent:
    service: object
    operation: str
    keys: tuple


def prepare(accounts,policy):
    p=policy['sale']
    if (p['service_id']!=214 or p['cash_equipment_level']!=40 or p['buyback_currency']!='cash'
            or not 1<=p['buyback_capacity']<=256 or not 1<=p['buyback_ttl_seconds']<=86400):
        raise ValueError('Unsupported NPC sale policy')
    rows=json.loads((OUT/'catalogs/knight.gsp.npc.citemsell.json').read_text(encoding='utf-8'))
    explicit={int(r['attributes']['id']):(int(r['attributes']['sellnpc']),int(r['attributes']['sellprice']))
              for r in rows if r['attributes'].get('moneytype')=='2'}
    effects=json.loads((OUT/'catalogs/knight.gsp.item.cequipeffect.json').read_text(encoding='utf-8'))
    equipment={int(r['attributes']['id']):(int(r['attributes']['sellpricecoef']),int(r['attributes']['endurecoef']))
        for r in effects if 'sellpricecoef' in r['attributes'] and 'endurecoef' in r['attributes']}
    ids=tuple(p['npc_ids'])
    if any(i not in accounts.npc_resources[1] for i in ids): raise ValueError('Unknown seller NPC')
    rules=SaleRules(policy['revision'],ids,MappingProxyType(explicit),MappingProxyType(equipment),
        p['buyback_capacity'],p['buyback_ttl_seconds'],p['cash_equipment_level'])
    with closing(accounts.connect()) as db,db:
        db.execute('''CREATE TABLE IF NOT EXISTS npc_buyback_items (
            item_key INTEGER PRIMARY KEY,role_id INTEGER NOT NULL REFERENCES roles(id),
            npc_id INTEGER NOT NULL,record TEXT NOT NULL,cash_price INTEGER NOT NULL CHECK(cash_price>0),
            sold_at INTEGER NOT NULL)''')
        db.execute('''CREATE INDEX IF NOT EXISTS npc_buyback_role ON npc_buyback_items(role_id,npc_id,sold_at)''')
        db.execute('''CREATE TABLE IF NOT EXISTS npc_shop_journal (
            role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
            operation TEXT NOT NULL,detail TEXT NOT NULL,PRIMARY KEY(role_id,request_id))''')
    accounts.npc_sale_rules=rules
    return tuple(ServiceBinding(i,214,'items.sell','designed','design/npc-services-v1.json#sale; original citemsell.sellnpc')
                 for i in ids)


def decode_request(kind,body):
    if type(body) is not bytes or len(body)<8: raise ValueError('Invalid NPC sale request')
    key=struct.unpack_from('>q',body)[0]
    if key<0:raise ValueError('Invalid seller NPC key')
    if kind==REPURCHASE:
        if len(body)!=12:raise ValueError('CRepurchaseFromNpc requires 12 bytes')
        keys=(struct.unpack_from('>i',body,8)[0],)
    elif kind==SELL_ITEMS:
        try:count,offset=read_compact(body,8)
        except NeedMoreData:raise ValueError('Missing sale vector') from None
        if not 1<=count<=10 or len(body)!=offset+count*4:
            raise ValueError('Sale requires 1..10 whole item stacks')
        keys=struct.unpack_from('>'+'i'*count,body,offset)
    else:raise ValueError('Unsupported sale request')
    if min(keys)<=0 or len(set(keys))!=len(keys):raise ValueError('Invalid or duplicate sale item key')
    return key,tuple(keys)


def plan(resources,kind,body,proof,current,*,request_id,now_ms,deadline_ms):
    key,keys=decode_request(kind,body)
    service=resources.services.plan(struct.pack('>qi',key,214),proof,current,
        request_id=request_id,now_ms=now_ms,deadline_ms=deadline_ms)
    return SaleIntent(service,'sell' if kind==SELL_ITEMS else 'buyback',keys)


def quote(rules,inventory,item,npc_id):
    explicit=rules.explicit.get(item.template_id)
    attr=inventory.items[item.template_id]
    if explicit is not None and explicit[0]==npc_id:
        unit=explicit[1]
        currency='bound_silver'
    else:
        coeff=rules.equipment.get(item.template_id)
        if (attr.get('bCanSaleToNpc')!='1' or coeff is None or coeff[1]<=0
                or item.condition_state is None or item.detail_state is None
                or item.condition_revision!=inventory.condition_rules.revision
                or item.detail_revision!=inventory.detail_rules.revision):
            raise ValueError('Item has no known ordinary NPC sale quote')
        state=EquipmentCondition(**json.loads(item.condition_state))
        # Original107a6e0 stores the rational in binary32 before truncation.
        value=struct.unpack('<f',struct.pack('<f',state.current*coeff[0]/coeff[1]))[0]
        unit=max(1,int(value))
        currency=('cash' if item.binding==0 and int(attr['level'])>=rules.cash_level else 'bound_silver')
    price=unit*item.quantity
    if not 1<=price<=0x7fffffff:raise ValueError('NPC sale price outside native signed32 range')
    return currency,price


def _cache(db,inventory,npc_id,rules):
    db.execute('DELETE FROM npc_buyback_items WHERE role_id=? AND sold_at<=?',
               (inventory.role_id,int(time.time())-rules.ttl_seconds))
    return db.execute('SELECT item_key,record,cash_price FROM npc_buyback_items '
        'WHERE role_id=? AND npc_id=? ORDER BY sold_at,item_key',(inventory.role_id,npc_id)).fetchall()


def _listing(db,inventory,npc_id,rules,wallet):
    rows=_cache(db,inventory,npc_id,rules)
    records=[]
    for slot,(key,raw,price) in enumerate(rows):
        item=StoredItem(**json.loads(raw))
        records.append(item_record(dict(id=key,template_id=item.template_id,slot=slot,
                                      quantity=item.quantity,binding=item.binding)))
    cash=next(r.balance for r in wallet if r.currency=='cash')
    # SGetRepurchaseItems embeds ItemBag then its price map. SItemBagInfo's
    # trailing flag belongs to that outer message, not to the shared ItemBag.
    bag=struct.pack('>Qi',cash,rules.capacity)+compact(len(rows))+b''.join(records)
    prices=compact(len(rows))+b''.join(struct.pack('>ii',key,price) for key,raw,price in sorted(rows))
    return REPURCHASE_ITEMS,bag+prices


def cache_messages(accounts,inventory,npc_id):
    if npc_id not in accounts.npc_sale_rules.npc_ids:return []
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        try:wallet=read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,accounts.currency_rules)
        except WalletNotInitialized:return []
        return [_listing(db,inventory,npc_id,accounts.npc_sale_rules,wallet)]


def settle(accounts,inventory,intent,precommit=None):
    service=intent.service;rules=accounts.npc_sale_rules
    if ((service.role_id,service.login_epoch)!=(inventory.role_id,inventory.epoch)
            or service.handler!='items.sell' or service.npc_id not in rules.npc_ids):
        raise ValueError('NPC sale owner or seller mismatch')
    fingerprint=hashlib.sha256(json.dumps((rules.revision,intent.operation,service.npc_id,intent.keys),
        separators=(',',':')).encode()).hexdigest()
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if int(time.monotonic()*1000)>=service.deadline_ms:raise ValueError('NPC sale command expired')
        read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,accounts.currency_rules)
        old=db.execute('SELECT fingerprint FROM npc_command_receipts WHERE role_id=? AND request_id=?',
                       (inventory.role_id,service.request_id)).fetchone()
        if old and old[0]!=fingerprint:raise ValueError('NPC sale retry intent conflict')
        if not old:
            identity='ns:'+hashlib.sha256(service.request_id.encode()).hexdigest()
            detail=[]
            if intent.operation=='sell':
                owned={i.id:i for i in carried_items(db,inventory)}
                selected=[owned.get(key) for key in intent.keys]
                if any(i is None for i in selected):raise ValueError('Sale item is not carried by this role')
                quotes=[quote(rules,inventory,item,service.npc_id) for item in selected]
                deltas=defaultdict(int)
                _cache(db,inventory,service.npc_id,rules)
                for item,(currency,price) in zip(selected,quotes):
                    original=take_carried(db,inventory,item.id)
                    raw=json.dumps(asdict(original),sort_keys=True)
                    db.execute('INSERT INTO npc_buyback_items VALUES(?,?,?,?,?,?)',
                        (item.id,inventory.role_id,service.npc_id,raw,price,int(time.time())))
                    deltas[currency]+=price
                    detail.append({'item':asdict(original),'currency':currency,'price':price})
                apply_currency(db,inventory.account_id,inventory.role_id,inventory.epoch,
                    CurrencyChange(identity,'npc_shop',f'npc:{service.npc_id}:sell',tuple(sorted(deltas.items()))),accounts.currency_rules)
                # Local buyback retention is bounded per role; sold snapshots
                # remain in the immutable journal after cache eviction/expiry.
                rows=db.execute('SELECT item_key FROM npc_buyback_items WHERE role_id=? ORDER BY sold_at DESC,item_key DESC',
                                (inventory.role_id,)).fetchall()
                for key, in rows[rules.capacity:]:db.execute('DELETE FROM npc_buyback_items WHERE item_key=?',(key,))
            elif intent.operation=='buyback':
                row=next((r for r in _cache(db,inventory,service.npc_id,rules) if r[0]==intent.keys[0]),None)
                if row is None:raise ValueError('Buyback item is unavailable from this NPC')
                item=StoredItem(**json.loads(row[1]));price=row[2]
                apply_currency(db,inventory.account_id,inventory.role_id,inventory.epoch,
                    CurrencyChange(identity,'npc_shop',f'npc:{service.npc_id}:buyback:{item.id}',(('cash',-price),)),accounts.currency_rules)
                restore_carried(db,inventory,item)
                db.execute('DELETE FROM npc_buyback_items WHERE item_key=?',(item.id,))
                detail=[{'item':asdict(item),'currency':'cash','price':price}]
            else:raise ValueError('Unknown NPC sale operation')
            db.execute('INSERT INTO npc_shop_journal VALUES(?,?,?,?)',
                (inventory.role_id,service.request_id,intent.operation,json.dumps(detail,sort_keys=True)))
            db.execute('INSERT INTO npc_command_receipts VALUES(?,?,?)',
                (inventory.role_id,service.request_id,fingerprint))
        projected=precommit_messages(precommit,db,inventory,replayed=old is not None)
        wallet=read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,accounts.currency_rules)
        messages=[inventory.equipment_bag_messages(db,inventory.epoch)[0]]
        messages.extend(encode_currency_balance(r.currency,r.balance) for r in wallet if r.currency in ('cash','bound_silver'))
        messages.append(_listing(db,inventory,service.npc_id,rules,wallet))
        messages.extend(projected)
        return messages

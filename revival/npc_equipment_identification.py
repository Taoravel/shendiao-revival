"""NPC fixed-clean identification dialogue and atomic role settlement.

An accepted original query can establish one bounded server dialogue. The
dialogue lifetime is separate from each I/O deadline. Shared callers own live
modal/map/member/connection fences. This Module does not
activate a registry/route or infer a random identification result.
"""
from contextlib import closing
from dataclasses import dataclass,asdict
import hashlib
import json
from pathlib import Path
import struct
import time
from types import MappingProxyType
from inspect_client import OUT
from npc_identification_protocol import IDENTIFY_EQUIPMENT,decode_identification_request
from npc_identification_query import (IdentificationQueryRules,IdentificationQueryIntent,
    plan_query,query_states)
from world_owner import Location
from world_role_delivery import RoleViewBinding
from currency import CurrencyChange,apply_currency,read_wallet
from currency_protocol import encode_currency_balance
from role_equipment_storage import current_resource_profile,synchronize_inventory_resource_source
from role_resource_storage import read_role_resources
from role_growth import read_growth
from role_attribute_protocol import growth_refresh


@dataclass(frozen=True)
class IdentificationRules:
    revision: str
    query_rules: IdentificationQueryRules
    dialogue_deadline_ms: int
    fees: object
    item_levels: object

    def __post_init__(self):
        if (self.revision!='2026-10-24.npc-equipment-identification.1'
                or type(self.query_rules) is not IdentificationQueryRules
                or type(self.dialogue_deadline_ms) is not int or self.dialogue_deadline_ms!=300000
                or type(self.fees) is not MappingProxyType or type(self.item_levels) is not MappingProxyType
                or not self.item_levels):
            raise ValueError('Explicit frozen NPC fixed identification recipe required')


def load_rules(query_rules,inventory_config,*,path=None):
    """Startup-only original exact fees and ordinary CItemAttr.level snapshot."""
    policy=json.loads((Path(path) if path is not None else OUT/'design/npc-equipment-identification-v1.json')
        .read_text(encoding='utf8'))
    if type(policy) is not dict:raise ValueError('Explicit NPC identification policy object required')
    numbers=('npc_id','map_id','placement_id','service_id','confirmation_type',
        'confirmation_mode','confirmation_auxiliary_argument','dialogue_deadline_ms')
    values=tuple(policy.get(key) for key in numbers)
    fee_keys=(1,10,20,30,40,50,60,70,80,90,100,110,120,130,140,150)
    if (type(query_rules) is not IdentificationQueryRules
            or inventory_config.detail_rules is not query_rules.detail_rules
            or any(type(value) is not int for value in values)
            or values!=(10890,1007,75,495,IDENTIFY_EQUIPMENT,1,0,300000)
            or policy.get('handler')!='equipment.identify.clean'
            or policy.get('query_policy')!=query_rules.revision
            or policy.get('fee_catalog')!='knight.gsp.item.cnpcidentifyneedmoneyconfig'
            or policy.get('fee_currency')!='cash' or policy.get('fee_purpose')!='npc_equipment_identify'
            or type(policy.get('fee_keys')) is not list
            or any(type(value) is not int for value in policy['fee_keys'])
            or tuple(policy['fee_keys'])!=fee_keys):
        raise ValueError('Unsupported fixed NPC identification or query contract')
    rows=json.loads((OUT/'catalogs/knight.gsp.item.cnpcidentifyneedmoneyconfig.json').read_text(encoding='utf8'))
    fees=tuple(sorted((int(row['attributes']['id']),int(row['attributes']['needmoney'])) for row in rows))
    original=(100,250,500,1000,2000,15000,20000,30000,50000,100000,200000,300000,400000,500000,600000,800000)
    if fees!=tuple(zip(fee_keys,original)):
        raise ValueError('Original exact identification fee table requires review')
    levels={template:int(inventory_config.items[template]['level']) for template in query_rules.detail_rules.templates
        if int(inventory_config.items[template]['itemtypeid']) not in (0x1c8,0x2c8,0x3c8)}
    if any(level<0 for level in levels.values()):raise ValueError('Negative ordinary equipment level is unsupported')
    return IdentificationRules(policy.get('revision'),query_rules,policy['dialogue_deadline_ms'],
        MappingProxyType(dict(fees)),MappingProxyType(levels))


def prepare(accounts,*,path=None):
    """After query/inventory/currency preparation; no registry or profile change."""
    rules=load_rules(accounts.npc_identification_query_rules,accounts.inventory_config,path=path)
    if 'npc_equipment_identify' not in accounts.currency_rules.spend_purposes['cash']:
        raise ValueError('Dedicated cash identification purpose is not prepared')
    with closing(accounts.connect()) as db,db:
        db.execute('''CREATE TABLE IF NOT EXISTS npc_equipment_identification_receipts (
            role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
            intent TEXT NOT NULL,admission TEXT NOT NULL,fingerprint TEXT NOT NULL,
            fee INTEGER NOT NULL,PRIMARY KEY(role_id,request_id))''')
    accounts.npc_identification_rules=rules


@dataclass(frozen=True)
class IdentificationTicket:
    rules: IdentificationRules
    query: IdentificationQueryIntent
    query_body: bytes
    binding: RoleViewBinding
    request_id: str
    issued_ms: int
    expires_ms: int

    def __post_init__(self):
        if (type(self.rules) is not IdentificationRules or type(self.query) is not IdentificationQueryIntent
                or self.query.rules is not self.rules.query_rules or type(self.query_body) is not bytes
                or type(self.binding) is not RoleViewBinding or type(self.request_id) is not str
                or not 1<=len(self.request_id)<=128
                or type(self.issued_ms) is not int or type(self.expires_ms) is not int
                or not 0<=self.issued_ms<self.expires_ms<2**63
                or self.expires_ms!=self.issued_ms+self.rules.dialogue_deadline_ms):
            raise ValueError('Complete frozen server identification dialogue required')
        _binding_matches(self.binding,self.query.location)


@dataclass(frozen=True)
class IdentificationDialogue:
    ticket: IdentificationTicket
    messages: tuple


@dataclass(frozen=True)
class IdentificationIntent:
    ticket: IdentificationTicket
    item_key: int
    current_query: IdentificationQueryIntent
    deadline_ms: int


def _binding_matches(binding,current):
    if (type(binding) is not RoleViewBinding or type(current) is not Location
            or (binding.address,binding.role_id,binding.login_epoch)!=(
                current.address,current.role_id,current.login_epoch)):
        raise ValueError('Current trusted NPC dialogue membership and connection required')


def query(inventory,body,proof,current,binding,*,rules,request_id,now_ms,deadline_ms):
    """Run the actual read-only query before returning a server dialogue.

    The role owner installs this only after its modal-state gate; movement,
    another menu, transfer, battle or disconnect clears the uncommitted ticket.
    The caller fences these logical replies at actual connection sending.
    """
    if (type(rules) is not IdentificationRules or type(request_id) is not str
            or not 1<=len(request_id)<=128 or type(now_ms) is not int
            or not 0<=now_ms<2**63-rules.dialogue_deadline_ms):
        raise ValueError('Server-owned bounded identification dialogue required')
    _binding_matches(binding,current)
    snapshot=inventory.immutable_snapshot()
    planned=plan_query(body,proof,current,snapshot.inventory_revision,rules=rules.query_rules,
        now_ms=now_ms,deadline_ms=deadline_ms)
    messages=query_states(inventory,planned)
    return IdentificationDialogue(IdentificationTicket(rules,planned,body,binding,request_id,
        now_ms,now_ms+rules.dialogue_deadline_ms),messages)


def confirm(ticket,body,proof,current,binding,*,now_ms,deadline_ms):
    """Freeze original(itemKey,0,1) under the still-current accepted query.

    This plans no fee and writes nothing. Settlement must recheck the current
    lease, queried inventory revision and complete asset CAS in one transaction.
    A paid confirmation ID belongs to this ticket, not a fresh wire packet.
    """
    if (type(ticket) is not IdentificationTicket or type(ticket.rules) is not IdentificationRules
            or type(ticket.query) is not IdentificationQueryIntent
            or type(now_ms) is not int or type(deadline_ms) is not int
            or not ticket.issued_ms<=now_ms<ticket.expires_ms
            or ticket.expires_ms!=ticket.issued_ms+ticket.rules.dialogue_deadline_ms
            or binding!=ticket.binding or current!=ticket.query.location
            or ticket.query.rules is not ticket.rules.query_rules):
        raise ValueError('Expired or invalidated identification dialogue')
    _binding_matches(binding,current)
    request=decode_identification_request(body)
    if (request.mode!=1 or request.auxiliary_argument!=0 or request.item_key<=0
            or request.item_key not in ticket.query.item_keys):
        raise ValueError('Original NPC confirmation must select this query once')
    deadline=min(deadline_ms,ticket.expires_ms)
    fresh=plan_query(ticket.query_body,proof,current,ticket.query.inventory_revision,
        rules=ticket.rules.query_rules,now_ms=now_ms,deadline_ms=deadline)
    if fresh.item_keys!=ticket.query.item_keys:
        raise ValueError('Identification dialogue query payload changed')
    return IdentificationIntent(ticket,request.item_key,fresh,deadline)


def _json(value):return json.dumps(value,sort_keys=True,separators=(',',':'))


def _digest(value):return hashlib.sha256(_json(value).encode('utf8')).hexdigest()


def settle(accounts,inventory,intent):
    """One admitted confirmation: current asset CAS, cash, source and receipts.

    Matching paid tickets only encode current authority. The owning role must
    first reprove current modal/map/member/connection state, then fence final
    logical replies at actual sending; this function never sends or migrates.
    """
    if (type(intent) is not IdentificationIntent or type(intent.item_key) is not int
            or type(intent.current_query) is not IdentificationQueryIntent
            or type(intent.ticket) is not IdentificationTicket
            or intent.ticket.rules is not accounts.npc_identification_rules
            or inventory.detail_rules is not intent.ticket.rules.query_rules.detail_rules):
        raise ValueError('Current frozen server identification intent required')
    ticket=intent.ticket;current=intent.current_query
    checked=confirm(ticket,struct.pack('>iii',intent.item_key,0,1),current.proof,current.location,
        ticket.binding,now_ms=int(time.monotonic()*1000),deadline_ms=intent.deadline_ms)
    if checked!=intent or (current.proof.role_id,current.proof.login_epoch)!=(inventory.role_id,inventory.epoch):
        raise ValueError('Identification owner or current proof differs from admission')
    rr,gear=accounts.resource_rules,accounts.equipment_attribute_rules
    account,role,epoch=inventory.account_id,inventory.role_id,inventory.epoch
    frozen=dict(policy=ticket.rules.revision,request_id=ticket.request_id,item_key=intent.item_key,
        binding=asdict(ticket.binding),query_proof=asdict(ticket.query.proof),
        query_inventory_revision=ticket.query.inventory_revision,query_keys=ticket.query.item_keys,
        issued_ms=ticket.issued_ms,expires_ms=ticket.expires_ms)
    identity='ni:'+hashlib.sha256(ticket.request_id.encode('utf8')).hexdigest()
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if int(time.monotonic()*1000)>=intent.deadline_ms:raise ValueError('Identification expired waiting for storage')
        snapshot=inventory.immutable_snapshot_transaction(db)
        # Reject a missing/pending source before mutation; this operation never
        # repairs a different uncommitted asset change or creates a profile.
        current_resource_profile(db,account,role,epoch,snapshot,equipment_rules=gear,resource_rules=rr)
        resources=read_role_resources(db,account,role,epoch,rr)
        old=db.execute('SELECT intent,admission,fingerprint,fee FROM npc_equipment_identification_receipts '
            'WHERE role_id=? AND request_id=?',(role,ticket.request_id)).fetchone()
        common=db.execute('SELECT fingerprint FROM npc_command_receipts WHERE role_id=? AND request_id=?',
            (role,ticket.request_id)).fetchone()
        if (old is None)!=(common is None):raise ValueError('Identification receipt is incomplete or conflicts')
        if old:
            admission=json.loads(old[1]);fingerprint=_digest(dict(intent=frozen,admission=admission))
            if old[0]!=_json(frozen) or admission['fee']!=old[3] or old[2]!=fingerprint or common[0]!=fingerprint:
                raise ValueError('Identification paid ticket intent conflict')
        else:
            basis=inventory.equipment_identification_basis(db,intent.item_key,epoch,
                expected_inventory_revision=ticket.query.inventory_revision)
            if basis.inventory_revision!=ticket.query.inventory_revision:
                raise ValueError('Identification query asset revision is stale')
            level=ticket.rules.item_levels.get(basis.item.template_id)
            fee=ticket.rules.fees.get(level)
            if fee is None:raise ValueError('No original exact identification quote for this ordinary level')
            admission=dict(fee=fee,level=level,basis=asdict(basis))
            fingerprint=_digest(dict(intent=frozen,admission=admission))
            apply_currency(db,account,role,epoch,CurrencyChange(identity,'npc_equipment_identify',
                f'npc:10890:identify:{intent.item_key}',(('cash',-fee),)),accounts.currency_rules)
            inventory.identify_equipment_clean_transaction(db,basis,epoch)
            db.execute('INSERT INTO npc_equipment_identification_receipts VALUES(?,?,?,?,?,?)',
                (role,ticket.request_id,_json(frozen),_json(admission),fingerprint,fee))
            db.execute('INSERT INTO npc_command_receipts VALUES(?,?,?)',(role,ticket.request_id,fingerprint))
        latest=inventory.immutable_snapshot_transaction(db)
        synchronized=synchronize_inventory_resource_source(db,account,role,epoch,latest,ticket.request_id,
            resource_rules=rr,equipment_rules=gear,replayed=old is not None)
        if synchronized is None or (synchronized.hp,synchronized.mp,synchronized.version,
                synchronized.caps.hp_max,synchronized.caps.mp_max)!=(
                resources.hp,resources.mp,resources.version,resources.caps.hp_max,resources.caps.mp_max):
            raise ValueError('Identification must preserve known current resources and caps')
        profile=current_resource_profile(db,account,role,epoch,latest,equipment_rules=gear,resource_rules=rr)
        messages=[]
        if any(item.id==intent.item_key for item in latest.items):
            messages.append(inventory.equipment_tip_message(db,intent.item_key,epoch))
        elif old is None:
            raise ValueError('Identified equipment disappeared before commit')
        messages.extend((inventory.equipment_bag_messages(db,epoch)[0],
            growth_refresh(read_growth(db,account,role),profile)))
        wallet=read_wallet(db,account,role,epoch,accounts.currency_rules)
        messages.extend(encode_currency_balance(row.currency,row.balance) for row in wallet if row.currency=='cash')
        if int(time.monotonic()*1000)>=intent.deadline_ms:raise ValueError('Identification expired before commit')
        return tuple(messages)

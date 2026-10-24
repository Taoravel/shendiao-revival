"""Own native equipment column3, independent of internal view4/NPC buyback4.

Current role-owner transaction only; no connections, writes, commits or sends.
Read actual owned items then encode original messages, never relabel NPC bytes.
"""
import struct
from dataclasses import dataclass
from inventory import item_record
from wire import compact,octets
from equipment_detail import encode
from equipment_gems import GemRules,encode_detail,decode as decode_socket
from equipment_gem_score import GemScoreRules,validate_current
import equipment_gem_storage as sockets
import equipment_gem_score_storage as scores


@dataclass(frozen=True)
class NativeEquipmentRules:
    gems: GemRules
    score: GemScoreRules

    def __post_init__(self):
        if type(self.gems) is not GemRules or type(self.score) is not GemScoreRules:
            raise ValueError('Frozen original equipment and selected gem score rules required')

    @classmethod
    def load(cls):return cls(GemRules.load(),GemScoreRules.load())


def _worn(snapshot):
    items=tuple(i for i in snapshot.items if i.equipment_slot is not None)
    if (len(items)>16 or len({i.equipment_slot for i in items})!=len(items)
            or any(type(i.equipment_slot) is not int or not 0<=i.equipment_slot<16
                or i.role_id!=snapshot.role_id or i.quantity!=1 or i.slot!=-i.equipment_slot-1 for i in items)):
        raise ValueError('Complete owned equipment slots required')
    return items


def equipment_bag(db,inventory):
    """Current own worn container3; slot positions are equipment slot numbers.

    Column3 has no carried wallet. Carried bag1 is a distinct producer and must
    retain its selected orb/source-aware Interface when combining a refresh.
    """
    snapshot=inventory.immutable_snapshot_transaction(db)
    items=_worn(snapshot)
    records=tuple(item_record(dict(vars(i),slot=i.equipment_slot)) for i in items)
    return 0xc03f3,struct.pack('>iQi',3,0,16)+compact(len(records))+b''.join(records)+b'\0'


def query_bag(db,inventory,payload):
    """Exact own query3 only; NPC column4 never enters this Interface."""
    if type(payload) is not bytes or len(payload)!=12:raise ValueError('Exact own equipment bag request required')
    column,target=struct.unpack('>iQ',payload)
    if column!=3 or target not in (0,inventory.role_id):raise ValueError('Own native equipment column3 and current role required')
    return (equipment_bag(db,inventory),)


def _item(snapshot,key):
    if type(key) is not int or not 0<key<=0x7fffffff:raise ValueError('Owned equipment instance key required')
    item=next((i for i in snapshot.items if i.id==key),None)
    if item is None or item.quantity!=1 or item.detail is None or item.condition is None:
        raise ValueError('Complete current owned equipment detail/condition required')
    return item


def _detail(db,inventory,rules,item):
    if type(rules) is not NativeEquipmentRules:raise ValueError('Frozen native equipment rules required')
    basis=sockets.read(db,inventory,rules.gems,item.id)
    score=scores.read(db,inventory,rules.score,item.id)
    if basis is None:
        if score is not None:raise ValueError('Gem score source without known socket state')
        return encode(item.template_id,item.detail,item.condition,rules.gems.detail_rules)
    if basis.item!=item or score is None:raise ValueError('Exact current gem and explicit score sources required')
    validate_current(rules.score,rules.gems,item,basis.state,score)
    return encode_detail(rules.gems,item,basis.state,basis.equipment_skill)


def item_messages(db,inventory,rules,key):
    """CURRENT tip/endure/max after wear, removal or repair; no old receipt data.

    Known gem state/score is included and validated; it never falls back to an
    empty gem vector. Missing ordinary detail or condition is not initialized.
    """
    snapshot=inventory.immutable_snapshot_transaction(db)
    _worn(snapshot)
    item=_item(snapshot,key);column=1 if item.equipment_slot is None else 3
    detail=_detail(db,inventory,rules,item)
    return ((0xc03fe,struct.pack('>ii',column,key)+octets(detail)),
        (0xc0412,struct.pack('>i',column)+compact(1)+struct.pack('>ii',key,item.condition.current)),
        (0xc0414,struct.pack('>iii',column,key,item.condition.maximum)))


def _column(column):
    if type(column) is not int or column not in (1,3):raise ValueError('Own ordinary equipment column1/3 required')


def query_tips(db,inventory,rules,payload):
    if type(payload) is not bytes or len(payload)!=8:raise ValueError('Exact own equipment detail request required')
    column,key=struct.unpack('>ii',payload);_column(column)
    snapshot=inventory.immutable_snapshot_transaction(db);item=_item(snapshot,key)
    if column!=(1 if item.equipment_slot is None else 3):raise ValueError('Current owned equipment column mismatch')
    return (item_messages(db,inventory,rules,key)[0],)


def query_endures(db,inventory,rules,payload):
    if type(payload) is not bytes or len(payload)!=4:raise ValueError('Exact own endurance column required')
    column=struct.unpack('>i',payload)[0];_column(column)
    if type(rules) is not NativeEquipmentRules:raise ValueError('Frozen native equipment rules required')
    snapshot=inventory.immutable_snapshot_transaction(db);_worn(snapshot)
    items=tuple(i for i in snapshot.items if (i.equipment_slot is not None)==(column==3)
        and i.template_id in rules.gems.detail_rules.templates)
    for item in items:_detail(db,inventory,rules,_item(snapshot,item.id))
    return ((0xc0412,struct.pack('>i',column)+compact(len(items))+
        b''.join(struct.pack('>ii',i.id,i.condition.current) for i in items)),)+tuple(
        (0xc0414,struct.pack('>iii',column,i.id,i.condition.maximum)) for i in items)


def socket_basis(db,inventory,rules,kind,payload):
    """Resolve source byte0/1 against actual carried/worn owned equipment.

    Returned SocketRequest.source_column remains the sealed INTERNAL1/4 marker.
    A worn result belongs to own native3; this never accepts a column4/NPC bag
    query or grants socket-action permission, material/cash debit or mutation.
    """
    if type(rules) is not NativeEquipmentRules:raise ValueError('Frozen native equipment rules required')
    request=decode_socket(kind,payload)
    basis=sockets.request_basis(db,inventory,rules.gems,request)
    _detail(db,inventory,rules,basis.item)
    return request,basis

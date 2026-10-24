"""Add only the readonly NPC query4 interface to the exact published sale module."""
import difflib
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runtime/deployments/npc-repair-20261024T023920Z/source/npc_shop_sales.py'
DEST=ROOT/'staging/npc-buyback-query-candidate-v2'
BASE_SHA='5bfbc44403d9ab2e3aa93dc0cf6304f20e74e7a1b5a111e757fc04bfb6e01058'
ADDITION='''

@dataclass(frozen=True)
class BuybackQuery:
    service: object


def plan_query(resources,body,proof,current,*,request_id,now_ms,deadline_ms):
    """Exact native4/NPC key; a real service2 binding grants only this read.

    It does not grant service214 sale/repurchase or create local shop stock.
    The caller must use current map-member permission before this plan and
    revalidate that permission when accepting its result for delivery.
    """
    if type(body) is not bytes or len(body)!=12:
        raise ValueError('NPC buyback query requires exactly12 bytes')
    column,key=struct.unpack('>iQ',body)
    if column!=4 or not 0<key<=0x7fffffffffffffff:
        raise ValueError('NPC buyback column4 and full NPC key required')
    service=resources.services.plan(struct.pack('>qi',key,2),proof,current,
        request_id=request_id,now_ms=now_ms,deadline_ms=deadline_ms)
    if service.service_id!=2 or service.handler!='shop.open':
        raise ValueError('Current NPC ordinary shop permission required')
    return BuybackQuery(service)


def query_listing(db,inventory,intent,*,rules,currency_rules):
    """Read and encode in the caller's current role transaction; no writes.

    Existing cash_price is the legacy full sale proceeds, retained unchanged
    until a separately adopted display/debit policy replaces the projection.
    No original-server pricing claim or new sale permission is made here.
    """
    if type(intent) is not BuybackQuery or type(rules) is not SaleRules or not db.in_transaction:
        raise ValueError('Current caller transaction and frozen buyback query required')
    service=intent.service
    if ((service.role_id,service.login_epoch)!=(inventory.role_id,inventory.epoch)
            or service.service_id!=2 or service.handler!='shop.open'):
        raise ValueError('NPC buyback query owner or shop mismatch')
    if int(time.monotonic()*1000)>=service.deadline_ms:
        raise ValueError('NPC buyback query expired')
    wallet=read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,currency_rules)
    threshold=int(time.time())-rules.ttl_seconds
    rows=db.execute('SELECT item_key,record,cash_price FROM npc_buyback_items '
        'WHERE role_id=? AND npc_id=? AND sold_at>? ORDER BY sold_at,item_key LIMIT ?',
        (inventory.role_id,service.npc_id,threshold,rules.capacity+1)).fetchall()
    if len(rows)>rules.capacity or rows and service.npc_id not in rules.npc_ids:
        raise ValueError('Unsupported current NPC buyback cache')
    for key,raw,price in rows:
        try:item=StoredItem(**json.loads(raw))
        except (ValueError,TypeError):
            raise ValueError('Complete same-role real buyback instance and price required') from None
        if type(item.template_id) is not int:
            raise ValueError('Complete same-role real buyback instance and price required')
        attr=inventory.items.get(item.template_id)
        if (type(key) is not int or not 0<key<=0x7fffffff or type(item.id) is not int or item.id!=key
                or type(item.role_id) is not int or item.role_id!=inventory.role_id
                or type(item.template_id) is not int or attr is None
                or type(item.quantity) is not int or not 1<=item.quantity<=min(0x7fffffff,int(attr.get('maxNum',1)))
                or type(item.binding) is not int or item.binding not in (0,1)
                or type(price) is not int or not 1<=price<=0x7fffffff):
            raise ValueError('Complete same-role real buyback instance and price required')
    return (_encode_listing(rows,rules,wallet),)


def query(accounts,inventory,intent):
    """Bounded role-I/O reader; connection and snapshot belong to this call.

    SQLite read-only mode is local to this connection. Caller-transaction users
    may invoke query_listing directly in an existing consistent read snapshot.
    """
    with closing(inventory.accounts.connect()) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        return query_listing(db,inventory,intent,rules=accounts.npc_sale_rules,
            currency_rules=accounts.currency_rules)
'''


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert sha(BASE)==BASE_SHA and sha(ROOT/'npc_shop_sales.py')==BASE_SHA
    assert not DEST.exists(),'Keep previous candidates'
    before=BASE.read_text(encoding='utf8');after=before+ADDITION
    # After the complete13-group green, share the real pure packet encoder.
    # Both transaction-driven refresh and readonly query must use one price
    # projection when the independent display/debit policy is later adopted.
    header='def _listing(db,inventory,npc_id,rules,wallet):\n    rows=_cache(db,inventory,npc_id,rules)\n'
    assert after.count(header)==1
    after=after.replace(header,'def _encode_listing(rows,rules,wallet):\n')
    tail='    return REPURCHASE_ITEMS,bag+prices\n\n\n'
    assert after.count(tail)==1
    after=after.replace(tail,tail+'def _listing(db,inventory,npc_id,rules,wallet):\n'
        '    return _encode_listing(_cache(db,inventory,npc_id,rules),rules,wallet)\n\n\n')
    DEST.mkdir(parents=True)
    (DEST/'npc_shop_sales.py').write_text(after,encoding='utf8')
    (DEST/'changes.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
        fromfile='published/npc_shop_sales.py',tofile='query-candidate/npc_shop_sales.py')),encoding='utf8')
    (DEST/'candidate.json').write_text(json.dumps(dict(base_sha256=BASE_SHA,
        candidate_sha256=sha(DEST/'npc_shop_sales.py'),workspace_or_shared_modified=False,
        original_cache_and_settlement_logic_unchanged=True,pure_original_packet_encoder_shared=True,
        display_debit_policy_adopted=False,
        query_permission_adopted=False,deployed=False),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Prepared inactive query4 candidate:',sha(DEST/'npc_shop_sales.py'))


if __name__=='__main__':main()

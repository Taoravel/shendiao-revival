"""Role-owned learning expenses; caller owns the transaction and source proof.

The priority mapping is an explicit caller adoption of bound silver, cash and
same-role depot cash. CurrencyRules must authorize each actual wallet debit.
No policy changes, implicit balances, level changes or guild writes live here.
"""
from dataclasses import dataclass,asdict
import hashlib,json
from currency import CurrencyChange,apply_currency,read_wallet
from npc_depot import cash_balance
from role_practice import owner


@dataclass(frozen=True)
class LearningBalances:
    wallet: tuple
    experience: int
    depot: int | None


@dataclass(frozen=True)
class LearningCostReceipt:
    source: str
    fingerprint: str
    money: int
    experience: int
    spent: tuple
    experience_before: int
    experience_after: int
    depot_before: int | None
    depot_after: int | None
    wallet_proof: str | None


def _json(v):return json.dumps(v,sort_keys=True,separators=(',',':'))


def identity(source):return 'life-learning:'+hashlib.sha256(source.encode()).hexdigest()


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS role_learning_cost_receipts (
        role_id INTEGER NOT NULL REFERENCES roles(id),source TEXT NOT NULL,fingerprint TEXT NOT NULL,
        result TEXT NOT NULL,digest TEXT NOT NULL,PRIMARY KEY(role_id,source))''')


def current(db,inventory,currency_rules):
    wallet=read_wallet(db,inventory.account_id,inventory.role_id,inventory.epoch,currency_rules)
    known=db.execute('SELECT experience FROM role_progress WHERE role_id=?',(inventory.role_id,)).fetchone()
    if known is None:raise ValueError('learning_experience_unknown')
    xp=known[0]
    if type(xp) is not int or not 0<=xp<2**63:raise ValueError('learning_experience_invalid')
    row=db.execute('SELECT cash FROM npc_depot_profiles WHERE role_id=?',(inventory.role_id,)).fetchone()
    depot=cash_balance(db,inventory) if row else None
    return LearningBalances(wallet,xp,depot)


def _wallet_proof(db,role,source):
    row=db.execute('SELECT fingerprint,receipt FROM role_wallet_receipts WHERE role_id=? AND settlement_id=?',
        (role,identity(source))).fetchone()
    return hashlib.sha256(_json(tuple(row)).encode()).hexdigest() if row else None


def receipt(db,role,source):
    row=db.execute('SELECT fingerprint,result,digest FROM role_learning_cost_receipts WHERE role_id=? AND source=?',(role,source)).fetchone()
    if not row:return None
    raw=json.loads(row[1]);raw['spent']=tuple(tuple(v) for v in raw['spent'])
    if hashlib.sha256(_json(raw).encode()).hexdigest()!=row[2]:raise ValueError('learning_cost_proof_invalid')
    result=LearningCostReceipt(**raw)
    if (result.source,result.fingerprint)!=(source,row[0]) or _wallet_proof(db,role,source)!=result.wallet_proof:
        raise ValueError('learning_cost_outcome_unknown')
    return result


def pay(db,inventory,source,fingerprint,money,experience,currency_rules):
    owner(db,inventory.account_id,inventory.role_id,inventory.epoch)
    if (type(source) is not str or not 1<=len(source)<=256 or '\0' in source
            or type(fingerprint) is not str or len(fingerprint)!=64
            or any(type(v) is not int or not 0<=v<2**63 for v in (money,experience))):
        raise ValueError('invalid_learning_cost')
    old=receipt(db,inventory.role_id,source)
    if old:
        if (old.fingerprint,old.money,old.experience)!=(fingerprint,money,experience):raise ValueError('learning_cost_intent_conflict')
        return old
    if _wallet_proof(db,inventory.role_id,source) is not None:raise ValueError('learning_cost_outcome_unknown')
    balances=current(db,inventory,currency_rules)
    if balances.experience<experience:
        raise ValueError('learning_experience_insufficient')
    wallet={b.currency:b.balance for b in balances.wallet};left=money;spent=[]
    for currency in ('bound_silver','cash'):
        amount=min(left,wallet[currency]);left-=amount
        if amount:spent.append((currency,amount))
    if left:
        if balances.depot is None:raise ValueError('learning_depot_unknown')
        if balances.depot<left:raise ValueError('learning_money_insufficient')
        spent.append(('depot_cash',left))
    deltas=tuple((name,-amount) for name,amount in spent if name!='depot_cash')
    if deltas:
        apply_currency(db,inventory.account_id,inventory.role_id,inventory.epoch,
            CurrencyChange(identity(source),'skill_training','life-learning:'+fingerprint,deltas),currency_rules)
    depot_after=None if balances.depot is None else balances.depot-left
    if left:db.execute('UPDATE npc_depot_profiles SET cash=? WHERE role_id=?',(depot_after,inventory.role_id))
    # EXP balance is shared with growth, but spending does not change level,
    # potential or attributes. Growth CAS compares its complete before state,
    # including EXP; retaining its stat revision keeps attribute caches valid.
    after=balances.experience-experience
    if experience:db.execute('UPDATE role_progress SET experience=? WHERE role_id=?',(after,inventory.role_id))
    result=LearningCostReceipt(source,fingerprint,money,experience,tuple(spent),balances.experience,after,
        balances.depot,depot_after,_wallet_proof(db,inventory.role_id,source))
    encoded=_json(asdict(result));digest=hashlib.sha256(encoded.encode()).hexdigest()
    db.execute('INSERT INTO role_learning_cost_receipts VALUES(?,?,?,?,?)',(inventory.role_id,source,fingerprint,encoded,digest))
    return result

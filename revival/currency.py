"""Explicit restoration wallets joining the role owner's fenced transaction.

No connections, commits, network, exchange, cross-role transfer or startup grants.
Task field mappings are designed; a logical wallet is not a native UI slot.
"""
from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from inspect_client import OUT

LIMIT = 2**63-1


class WalletNotInitialized(ValueError):
    pass


@dataclass(frozen=True)
class CurrencyRules:
    revision: str
    currencies: tuple
    task_fields: object
    spend_purposes: object


@dataclass(frozen=True)
class CurrencyChange:
    settlement_id: str
    purpose: str
    source_ref: str
    deltas: tuple  # ((canonical currency, signed integer change), ...)

    def __post_init__(self):
        for value in (self.settlement_id, self.purpose, self.source_ref):
            if type(value) is not str or not 1 <= len(value) <= 160:
                raise ValueError('Invalid currency command identity')
        if type(self.deltas) is not tuple or not 1 <= len(self.deltas) <= 4:
            raise ValueError('Immutable currency deltas required')
        seen, signs = set(), set()
        for row in self.deltas:
            if (type(row) is not tuple or len(row) != 2 or type(row[0]) is not str
                    or row[0] in seen or type(row[1]) is not int or row[1] == 0 or abs(row[1]) > LIMIT):
                raise ValueError('Invalid or repeated currency delta')
            seen.add(row[0]); signs.add(row[1] > 0)
        if len(signs) > 1:
            raise ValueError('Implicit currency exchange is disabled')


@dataclass(frozen=True)
class CurrencyBalance:
    currency: str
    balance: int
    revision: int


@dataclass(frozen=True)
class WalletReceipt:
    settlement_id: str
    policy: str
    balances: tuple


def load_currency_rules(path=None):
    path = Path(path) if path is not None else OUT/'design/currency-v1.json'
    x = json.loads(path.read_text(encoding='utf-8'))
    names = tuple(x['currencies'])
    if (not names or any(type(name) is not str or not name for name in names)
            or len(set(names)) != len(names) or type(x['revision']) is not str or not x['revision']):
        raise ValueError('Invalid currency policy')
    mapping = dict(x['task_fields'])
    if any(value not in names for value in mapping.values()):
        raise ValueError('Unknown mapped currency')
    spending = {name: frozenset(x['spend_purposes'][name]) for name in names}
    if any(type(purpose) is not str or not purpose for purposes in spending.values() for purpose in purposes):
        raise ValueError('Invalid spending purpose')
    return CurrencyRules(x['revision'], names, MappingProxyType(mapping), MappingProxyType(spending))


def prepare_wallet_storage(db):
    """Startup only. Does not create a role wallet or award currency."""
    db.executescript('''CREATE TABLE IF NOT EXISTS role_wallet_profiles (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id), policy TEXT NOT NULL,
        baseline TEXT NOT NULL, origin TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS role_wallet_balances (
        role_id INTEGER NOT NULL REFERENCES roles(id), currency TEXT NOT NULL,
        balance INTEGER NOT NULL CHECK(balance>=0), revision INTEGER NOT NULL,
        PRIMARY KEY(role_id,currency));
        CREATE TABLE IF NOT EXISTS role_wallet_receipts (
        role_id INTEGER NOT NULL REFERENCES roles(id), settlement_id TEXT NOT NULL,
        fingerprint TEXT NOT NULL, receipt TEXT NOT NULL, PRIMARY KEY(role_id,settlement_id));''')


def _owner(db, account_id, role_id, epoch):
    if not db.in_transaction:
        raise ValueError('Wallet requires owner transaction')
    if not db.execute('SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
                      'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
                      (role_id,account_id,epoch)).fetchone():
        raise ValueError('Wallet ownership or login lease mismatch')


def read_wallet(db, account_id, role_id, epoch, rules):
    _owner(db,account_id,role_id,epoch)
    profile = db.execute('SELECT policy FROM role_wallet_profiles WHERE role_id=?',(role_id,)).fetchone()
    if not profile:
        raise WalletNotInitialized('Explicit wallet baseline required')
    if profile[0] != rules.revision:
        raise ValueError('Wallet policy migration required')
    values = {r[0]: CurrencyBalance(*r) for r in db.execute(
        'SELECT currency,balance,revision FROM role_wallet_balances WHERE role_id=?',(role_id,))}
    if set(values) != set(rules.currencies):
        raise ValueError('Wallet profile is incomplete')
    if any(type(row.balance) is not int or not 0 <= row.balance <= LIMIT
           or type(row.revision) is not int or not 0 <= row.revision <= LIMIT for row in values.values()):
        raise ValueError('Invalid persisted wallet balance or revision')
    return tuple(values[name] for name in rules.currencies)


def initialize_wallet(db, account_id, role_id, epoch, baseline, origin, rules):
    """Trusted explicit initialization; never reset an existing balance."""
    _owner(db,account_id,role_id,epoch)
    if (type(baseline) is not tuple or len(baseline) != len(rules.currencies)
            or any(type(v) is not int or not 0 <= v <= LIMIT for v in baseline)
            or origin not in ('new_restoration_role','explicit_migration')):
        raise ValueError('Explicit known wallet baseline and origin required')
    encoded = json.dumps(baseline)
    old = db.execute('SELECT policy,baseline,origin FROM role_wallet_profiles WHERE role_id=?',(role_id,)).fetchone()
    if old:
        if tuple(old) != (rules.revision,encoded,origin):
            raise ValueError('Wallet baseline cannot be reset')
        return read_wallet(db,account_id,role_id,epoch,rules)
    db.execute('INSERT INTO role_wallet_profiles VALUES(?,?,?,?)',(role_id,rules.revision,encoded,origin))
    for name, value in zip(rules.currencies,baseline):
        db.execute('INSERT INTO role_wallet_balances VALUES(?,?,?,0)',(role_id,name,value))
    return read_wallet(db,account_id,role_id,epoch,rules)


def apply_currency(db, account_id, role_id, epoch, change, rules):
    """Credit/debit plus durable retry receipt; caller rolls back on any error.

    A retry returns the original historical receipt. Read the current wallet
    after settlement before refreshing an owner cache or native UI balance.
    """
    balances = {row.currency: row for row in read_wallet(db,account_id,role_id,epoch,rules)}
    if not isinstance(change,CurrencyChange):
        raise ValueError('Immutable currency change required')
    record = {'policy':rules.revision, **asdict(change)}
    fingerprint = hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    old = db.execute('SELECT fingerprint,receipt FROM role_wallet_receipts WHERE role_id=? AND settlement_id=?',
                     (role_id,change.settlement_id)).fetchone()
    if old:
        if old[0] != fingerprint:
            raise ValueError('Currency settlement ID reused with different intent')
        result = json.loads(old[1])
        return WalletReceipt(result['settlement_id'],result['policy'],tuple(CurrencyBalance(**r) for r in result['balances']))
    updated = []
    for name, delta in change.deltas:
        if name not in balances:
            raise ValueError('Unknown currency')
        before = balances[name]
        if delta < 0 and change.purpose not in rules.spend_purposes[name]:
            raise ValueError('Currency cannot fund this purpose')
        amount = before.balance+delta
        if not 0 <= amount <= LIMIT or before.revision >= LIMIT:
            raise ValueError('Insufficient or overflowing currency')
        updated.append(CurrencyBalance(name,amount,before.revision+1))
    for row in updated:
        db.execute('UPDATE role_wallet_balances SET balance=?,revision=? WHERE role_id=? AND currency=?',
                   (row.balance,row.revision,role_id,row.currency))
    receipt = WalletReceipt(change.settlement_id,rules.revision,tuple(updated))
    db.execute('INSERT INTO role_wallet_receipts VALUES(?,?,?,?)',
               (role_id,change.settlement_id,fingerprint,json.dumps(asdict(receipt))))
    return receipt


def task_currency_channels(reward_fields, rules):
    """Return original field/canonical currency/amount; other channels stay external."""
    result=[]
    for field, name in rules.task_fields.items():
        value = reward_fields.get(field,0)
        if type(value) is not int or not 0 <= value <= LIMIT:
            raise ValueError('Invalid task currency reward')
        if value:
            result.append((field,name,value))
    return tuple(result)

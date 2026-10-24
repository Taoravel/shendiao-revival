"""Explicit role-owned vigor; online time accrues in the owner's transaction.

The recovery profile is designed. No unknown legacy vigor is initialized from
current level, and no offline wall time or saved full-cap time creates credit.
"""
from contextlib import closing
from dataclasses import asdict,dataclass,replace
import json
import struct
from wire import compact


@dataclass(frozen=True)
class VigorRules:
    revision: str
    initial: int
    maximum: int
    period_ms: int
    gain: int


@dataclass(frozen=True)
class VigorState:
    role_id: int
    version: int
    value: int
    maximum: int
    online_epoch: str | None
    anchor_ms: int
    remainder_ms: int

    def __post_init__(self):
        if (any(type(v) is not int for v in (self.role_id,self.version,self.value,self.maximum,self.anchor_ms,self.remainder_ms))
                or self.role_id<=0 or not 0<=self.version<2**63-1
                or not 0<=self.value<=self.maximum<=2**24 or self.maximum<1
                or self.anchor_ms<0 or self.remainder_ms<0
                or self.online_epoch is not None and type(self.online_epoch) is not str):
            raise ValueError('Invalid authoritative vigor state')


def prepare(db,policy):
    if (policy['revision']!='2026-10-23.vigor.1' or policy['initial']!=100 or policy['maximum']!=100
            or policy['period_ms']!=300000 or policy['gain']!=5):
        raise ValueError('Vigor profile requires explicit implementation review')
    rules=VigorRules(policy['revision'],policy['initial'],policy['maximum'],policy['period_ms'],policy['gain'])
    db.execute('''CREATE TABLE IF NOT EXISTS role_vigor_profiles (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id),policy TEXT NOT NULL,baseline TEXT NOT NULL,
        origin TEXT NOT NULL,state TEXT NOT NULL)''')
    return rules


def _owner(db,inventory):
    if not db.in_transaction or not db.execute('SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
        'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
        (inventory.role_id,inventory.account_id,inventory.epoch)).fetchone():
        raise ValueError('Vigor requires current role lease transaction')


def read(db,inventory,rules):
    _owner(db,inventory)
    row=db.execute('SELECT policy,state FROM role_vigor_profiles WHERE role_id=?',(inventory.role_id,)).fetchone()
    if row is None:return None
    if row[0]!=rules.revision:raise ValueError('Vigor policy migration required')
    state=VigorState(**json.loads(row[1]))
    if state.role_id!=inventory.role_id or state.remainder_ms>=rules.period_ms:
        raise ValueError('Invalid persisted vigor scope or fraction')
    return state


def _write(db,inventory,state):
    db.execute('UPDATE role_vigor_profiles SET state=? WHERE role_id=?',
               (json.dumps(asdict(state)),inventory.role_id))
    return state


def initialize(db,inventory,rules,value,maximum,origin):
    _owner(db,inventory)
    if origin not in ('new_restoration_role','explicit_migration'):raise ValueError('Explicit vigor origin required')
    if origin=='new_restoration_role' and db.execute(
        'SELECT origin FROM role_restoration_origins WHERE role_id=?',(inventory.role_id,)).fetchone()!=('new_restoration_role',):
        raise ValueError('New vigor baseline requires durable role creation provenance')
    state=VigorState(inventory.role_id,0,value,maximum,None,0,0)
    baseline=json.dumps((value,maximum))
    old=db.execute('SELECT baseline,origin FROM role_vigor_profiles WHERE role_id=?',(inventory.role_id,)).fetchone()
    if old:
        if old!=(baseline,origin):raise ValueError('Existing vigor baseline cannot be reset')
        return read(db,inventory,rules)
    db.execute('INSERT INTO role_vigor_profiles VALUES(?,?,?,?,?)',
        (inventory.role_id,rules.revision,baseline,origin,json.dumps(asdict(state))))
    return state


def bind(db,inventory,rules,now_ms):
    state=read(db,inventory,rules)
    if state is None:return None
    if type(now_ms) is not int or now_ms<0:raise ValueError('Server monotonic vigor clock required')
    if state.online_epoch==str(inventory.epoch):return state
    return _write(db,inventory,replace(state,version=state.version+1,online_epoch=str(inventory.epoch),anchor_ms=now_ms))


def advance(db,inventory,rules,now_ms):
    state=read(db,inventory,rules)
    if state is None:return None
    if (state.online_epoch!=str(inventory.epoch) or type(now_ms) is not int or now_ms<state.anchor_ms):
        raise ValueError('Vigor session or monotonic clock mismatch')
    elapsed=now_ms-state.anchor_ms
    if not elapsed:return state
    periods,remainder=divmod(elapsed+state.remainder_ms,rules.period_ms)
    value=min(state.maximum,state.value+periods*rules.gain)
    if value==state.maximum:remainder=0
    return _write(db,inventory,replace(state,version=state.version+1,value=value,anchor_ms=now_ms,remainder_ms=remainder))


def consume(db,inventory,rules,amount):
    state=read(db,inventory,rules)
    if (state is None or state.online_epoch!=str(inventory.epoch) or type(amount) is not int
            or not 0<=amount<=state.value):
        raise ValueError('Explicit online vigor profile with sufficient balance required')
    return _write(db,inventory,replace(state,version=state.version+1,value=state.value-amount)) if amount else state


def suspend(db,inventory,rules,now_ms):
    state=advance(db,inventory,rules,now_ms)
    return _write(db,inventory,replace(state,version=state.version+1,online_epoch=None,anchor_ms=0)) if state else None


def refresh(state):
    if not isinstance(state,VigorState):raise ValueError('Authoritative vigor projection required')
    return 0xc32c8,compact(2)+struct.pack('>ifif',440,float(state.value),620,float(state.maximum))


def login(accounts,inventory,now_ms):
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if read(db,inventory,accounts.vigor_rules) is None:
            origin=db.execute('SELECT origin FROM role_restoration_origins WHERE role_id=?',(inventory.role_id,)).fetchone()
            if origin!=('new_restoration_role',):return None
            initialize(db,inventory,accounts.vigor_rules,accounts.vigor_rules.initial,accounts.vigor_rules.maximum,'new_restoration_role')
        return bind(db,inventory,accounts.vigor_rules,now_ms)


def checkpoint(accounts,inventory,now_ms,closing_session=False):
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        before=read(db,inventory,accounts.vigor_rules)
        if before is None:return []
        after=(suspend if closing_session else advance)(db,inventory,accounts.vigor_rules,now_ms)
        return [refresh(after)] if after.value!=before.value else []


def initialize_profile(accounts,inventory,value,maximum,origin,now_ms):
    """Trusted role migration entry only; no client packet authorizes a baseline."""
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        initialize(db,inventory,accounts.vigor_rules,value,maximum,origin)
        return bind(db,inventory,accounts.vigor_rules,now_ms)

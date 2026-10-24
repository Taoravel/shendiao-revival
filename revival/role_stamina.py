"""Known role stamina450/630; distinct from NPC vigor440/620.

No guessed baseline, automatic regeneration, connection, commit or sending.
The role owner joins resource, asset and receipt changes in one transaction.
"""
from dataclasses import dataclass,replace
import json
import struct
from inspect_client import OUT
from wire import compact


@dataclass(frozen=True)
class StaminaRules:
    revision: str


@dataclass(frozen=True)
class StaminaState:
    role_id: int
    version: int
    value: int
    maximum: int

    def __post_init__(self):
        if (any(type(x) is not int for x in (self.role_id,self.version,self.value,self.maximum))
                or self.role_id<=0 or not 0<=self.version<2**63-1 or not 0<=self.value<=self.maximum<=2**24
                or self.maximum<1):
            raise ValueError('Invalid known stamina state')


def prepare(db):
    policy=json.loads((OUT/'design/role-stamina-v1.json').read_text(encoding='utf-8'))
    if (policy['revision']!='2026-10-24.stamina.1' or policy['value_attribute']!=450
            or policy['maximum_attribute']!=630 or policy['origins']!=['explicit_known_stamina']):
        raise ValueError('Stamina policy requires explicit implementation review')
    db.execute('''CREATE TABLE IF NOT EXISTS role_stamina_profiles (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id),policy TEXT NOT NULL,
        baseline TEXT NOT NULL,origin TEXT NOT NULL,version INTEGER NOT NULL,
        value INTEGER NOT NULL,maximum INTEGER NOT NULL)''')
    return StaminaRules(policy['revision'])


def _owner(db,inventory):
    epoch=inventory.epoch
    if (not db.in_transaction or not (type(epoch) is int and epoch>0 or type(epoch) is str and bool(epoch))
            or not db.execute('SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
                'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
                (inventory.role_id,inventory.account_id,epoch)).fetchone()):
        raise ValueError('Stamina requires current role lease transaction')


def read(db,inventory,rules):
    _owner(db,inventory)
    row=db.execute('SELECT policy,origin,version,value,maximum FROM role_stamina_profiles WHERE role_id=?',
        (inventory.role_id,)).fetchone()
    if row is None:return None
    if row[:2]!=(rules.revision,'explicit_known_stamina'):
        raise ValueError('Unknown stamina policy or origin')
    return StaminaState(inventory.role_id,*row[2:])


def initialize(db,inventory,rules,value,maximum,origin):
    """Trusted complete migration only. A client packet cannot authorize this."""
    _owner(db,inventory)
    state=StaminaState(inventory.role_id,0,value,maximum)
    if origin!='explicit_known_stamina':raise ValueError('Explicit known stamina provenance required')
    baseline=json.dumps((value,maximum),separators=(',',':'))
    old=db.execute('SELECT policy,baseline,origin FROM role_stamina_profiles WHERE role_id=?',
        (inventory.role_id,)).fetchone()
    if old:
        if old!=(rules.revision,baseline,origin):raise ValueError('Existing stamina baseline cannot be reset')
        return read(db,inventory,rules)
    db.execute('INSERT INTO role_stamina_profiles VALUES(?,?,?,?,?,?,?)',
        (inventory.role_id,rules.revision,baseline,origin,0,value,maximum))
    return state


def consume(db,inventory,rules,amount):
    state=read(db,inventory,rules)
    if state is None or type(amount) is not int or amount<=0 or state.value<amount:
        raise ValueError('Known sufficient stamina and positive integer debit required')
    after=replace(state,version=state.version+1,value=state.value-amount)
    if db.execute('UPDATE role_stamina_profiles SET value=?,version=? WHERE role_id=? AND policy=? AND version=?',
            (after.value,after.version,inventory.role_id,rules.revision,state.version)).rowcount!=1:
        raise ValueError('Stamina version changed')
    return after


def refresh(state):
    if type(state) is not StaminaState:raise ValueError('Current known stamina required')
    return 0xc32c8,compact(2)+struct.pack('>ifif',450,float(state.value),630,float(state.maximum))

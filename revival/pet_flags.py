"""Known complete pet flag byte; binding is bit1, other bits stay opaque."""
from dataclasses import asdict, dataclass
import json

from inspect_client import OUT


@dataclass(frozen=True)
class PetFlags:
    version: int
    raw: int

    def __post_init__(self):
        if (type(self.version) is not int or not 0<=self.version<0x7fffffff
                or type(self.raw) is not int or not 0<=self.raw<=255):
            raise ValueError('Invalid known pet flags')

    @property
    def bound(self):
        return bool(self.raw & 2)


@dataclass(frozen=True)
class FlagRules:
    revision: str
    initial_raw: int

    @classmethod
    def load(cls):
        policy=json.loads((OUT/'design/pet-flags-v1.json').read_text(encoding='utf-8'))
        if (policy['revision']!='2026-10-23.pet-flags.1'
                or policy['wire']!={'bean_offset':220,'binding_mask':2,'maximum_raw':255}
                or type(policy['generation']['initial_raw']) is not int
                or policy['generation']['initial_raw']!=0):
            raise ValueError('Pet flag policy requires implementation review')
        return cls(policy['revision'],policy['generation']['initial_raw'])


def prepare(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_flags (
        pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id),
        policy TEXT NOT NULL,state TEXT NOT NULL);''')


def _owner(db,account,role,pet):
    if (type(pet) is not int or not 0<pet<=0x7fffffff or not db.in_transaction
            or not db.execute(
            'SELECT 1 FROM inventory_pets p JOIN roles r ON r.id=p.role_id '
            'WHERE p.id=? AND p.role_id=? AND r.account_id=? AND p.released=0',
            (pet,role,account)).fetchone()):
        raise ValueError('Pet flags require an owned live pet transaction')


def initialize(db,account,role,pet,rules,raw):
    _owner(db,account,role,pet)
    state=PetFlags(0,raw)
    if db.execute('SELECT 1 FROM inventory_pet_flags WHERE pet_id=?',(pet,)).fetchone():
        raise ValueError('Known pet flags cannot be reset')
    db.execute('INSERT INTO inventory_pet_flags VALUES(?,?,?)',
               (pet,rules.revision,json.dumps(asdict(state))))
    db.execute('INSERT INTO inventory_versions(role_id,revision) VALUES(?,1) '
               'ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(role,))
    return state


def load(db,account,role,pet,rules):
    _owner(db,account,role,pet)
    row=db.execute('SELECT policy,state FROM inventory_pet_flags WHERE pet_id=?',(pet,)).fetchone()
    if not row or row[0]!=rules.revision:
        raise ValueError('Pet flags require explicit known initialization or migration')
    return PetFlags(**json.loads(row[1]))


def bind_for_learning(db,account,role,pet,rules):
    """Internal learning operation; caller records the shared asset revision."""
    before=load(db,account,role,pet,rules)
    after=before if before.bound else PetFlags(before.version+1,before.raw|2)
    if after!=before:
        db.execute('UPDATE inventory_pet_flags SET state=? WHERE pet_id=?',
                   (json.dumps(asdict(after)),pet))
    return before,after

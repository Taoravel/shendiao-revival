"""Known cake history; current aptitude authority remains the growth Profile."""
from dataclasses import dataclass,asdict
import json
from inspect_client import OUT
import pet_traits


@dataclass(frozen=True)
class PetCakeHistory:
    version: int
    count: int
    added_aptitudes: tuple

    def __post_init__(self):
        if (type(self.version) is not int or not 0<=self.version<=0x7fffffff
                or type(self.count) is not int or not 0<=self.count<=20
                or type(self.added_aptitudes) is not tuple or len(self.added_aptitudes)!=5
                or any(type(x) is not int or not 0<=x<=0x7fffffff for x in self.added_aptitudes)
                or self.count==0 and any(self.added_aptitudes)):
            raise ValueError('Complete known cake count and historical additions required')


@dataclass(frozen=True)
class CakeRules:
    revision: str

    @classmethod
    def load(cls):
        p=json.loads((OUT/'design/pet-cake-v1.json').read_text(encoding='utf-8'))
        if (p['revision'],p['maximum_count'],p['new_pet_count'])!=('2026-10-23.pet-cake.1',20,0):
            raise ValueError('Cake history policy requires review')
        return cls(p['revision'])


def prepare(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_cakes(
        pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id),policy TEXT NOT NULL,
        source TEXT NOT NULL,state TEXT NOT NULL);''')


def initialize(db,account,role,pet,rules,count,added,*,source):
    pet_traits._owned(db,account,role,pet)
    if source not in ('new_restoration_pet','explicit_known_import'):
        raise ValueError('Cake history requires explicit complete initialization')
    state=PetCakeHistory(0,count,added)
    if db.execute('SELECT 1 FROM inventory_pet_cakes WHERE pet_id=?',(pet,)).fetchone():
        raise ValueError('Cake history already known')
    db.execute('INSERT INTO inventory_pet_cakes VALUES(?,?,?,?)',(pet,rules.revision,source,json.dumps(asdict(state))))
    _revision(db,role)
    return state


def load(db,account,role,pet,rules):
    pet_traits._owned(db,account,role,pet)
    row=db.execute('SELECT policy,source,state FROM inventory_pet_cakes WHERE pet_id=?',(pet,)).fetchone()
    if not row or row[0]!=rules.revision or row[1] not in ('new_restoration_pet','explicit_known_import'):
        raise ValueError('Unknown cake history requires explicit reconciliation')
    value=json.loads(row[2]);value['added_aptitudes']=tuple(value['added_aptitudes'])
    return PetCakeHistory(**value)


def reset(db,account,role,pet,rules,before):
    if load(db,account,role,pet,rules)!=before:raise ValueError('Cake history changed before save')
    if before.count==0:return before
    after=PetCakeHistory(before.version+1,0,(0,)*5)
    row=db.execute('SELECT state FROM inventory_pet_cakes WHERE pet_id=?',(pet,)).fetchone()
    if db.execute('UPDATE inventory_pet_cakes SET state=? WHERE pet_id=? AND state=?',
            (json.dumps(asdict(after)),pet,row[0])).rowcount!=1:raise ValueError('Cake source changed')
    _revision(db,role)
    return after


def _revision(db,role):
    db.execute('INSERT INTO inventory_versions VALUES(?,1) ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(role,))

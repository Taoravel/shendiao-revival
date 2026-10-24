"""Independent known stone sources, composed once after ordinary blood aptitudes."""
from dataclasses import dataclass,asdict,replace
import json
from inspect_client import OUT
from pet_traits import _owned

POLICY='2026-10-24.pet-stones.1'


@dataclass(frozen=True)
class PetStones:
    version: int
    count: int
    added_aptitudes: tuple
    policy: str=POLICY

    def __post_init__(self):
        if (self.policy!=POLICY or type(self.version) is not int or not 0<=self.version<=0x7fffffff
                or type(self.count) is not int or not 0<=self.count<=5
                or type(self.added_aptitudes) is not tuple or len(self.added_aptitudes)!=5
                or any(type(v) is not int or not 0<=v<=250 for v in self.added_aptitudes)
                or sum(self.added_aptitudes)!=50*self.count):
            raise ValueError('Known complete stone count and exact added aptitudes required')


def decode(value):return PetStones(value['version'],value['count'],tuple(value['added_aptitudes']),value['policy'])


@dataclass(frozen=True)
class StoneRules:
    revision: str
    templates: tuple
    maximum_count: int
    growth_per_stone: int
    aptitude_per_stone: int

    @classmethod
    def load(cls):
        p=json.loads((OUT/'design/pet-stones-v1.json').read_text(encoding='utf-8'))
        if (p['revision']!='2026-10-24.pet-stones.1' or p['templates']!=[70052,70053]
                or (p['maximum_count'],p['growth_per_stone'],p['aptitude_per_stone'])!=(5,5,50)
                or (p['draws']['count'],p['draws']['exclusive_maximum'])!=(50,10000)):
            raise ValueError('Stone policy requires review')
        return cls(p['revision'],tuple(p['templates']),p['maximum_count'],p['growth_per_stone'],p['aptitude_per_stone'])

    def validate_draws(self,draws):
        if (type(draws) is not tuple or len(draws)!=self.aptitude_per_stone
                or any(type(v) is not int or not 0<=v<10000 for v in draws)):
            raise ValueError('Exactly50 immutable trusted admitted stone draws required')

    def additions(self,draws):
        self.validate_draws(draws);values=[0]*5
        for draw in draws:values[draw*5//10000]+=1
        return tuple(values)

    def effective_profile(self,profile,stones):
        if stones is None:return profile
        if type(stones) is not PetStones:raise ValueError('Frozen known stone source required')
        values=tuple(a+b for a,b in zip(profile.aptitudes,stones.added_aptitudes))
        if len(values)!=5 or any(type(v) is not int or not 0<=v<=0x7fffffff for v in values):
            raise ValueError('Effective stone aptitude overflow')
        return replace(profile,aptitudes=values)


def prepare(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_stones(
        pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id),policy TEXT NOT NULL,
        source TEXT NOT NULL,state TEXT NOT NULL);''')


def initialize(db,account,role,pet,rules,count,added_aptitudes,*,source):
    _owned(db,account,role,pet);state=PetStones(0,count,added_aptitudes)
    if source not in ('new_restoration_pet','explicit_known_import'):
        raise ValueError('Explicit complete stone source required')
    if source=='new_restoration_pet' and count!=0:raise ValueError('New restoration stone source must be zero')
    if db.execute('SELECT 1 FROM inventory_pet_stones WHERE pet_id=?',(pet,)).fetchone():
        raise ValueError('Known stone sources cannot be initialized twice')
    db.execute('INSERT INTO inventory_pet_stones VALUES(?,?,?,?)',(pet,rules.revision,source,json.dumps(asdict(state))))
    db.execute('INSERT INTO inventory_versions VALUES(?,1) ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(role,))
    return state


def load(db,account,role,pet,rules):
    _owned(db,account,role,pet)
    row=db.execute('SELECT policy,source,state FROM inventory_pet_stones WHERE pet_id=?',(pet,)).fetchone()
    if row is None:return None
    if type(rules) is not StoneRules or row[0]!=rules.revision or row[1] not in ('new_restoration_pet','explicit_known_import'):
        raise ValueError('Known stone policy/source requires explicit reconciliation')
    return decode(json.loads(row[2]))

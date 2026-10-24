"""Known complete baby/wild identity and raw insight; unknown old pets stay unknown."""
from dataclasses import dataclass,asdict
import json
from inspect_client import OUT


@dataclass(frozen=True)
class PetTraits:
    version: int
    origin: int
    insight: int

    def __post_init__(self):
        if (type(self.version) is not int or not 0<=self.version<=0x7fffffff
                or type(self.origin) is not int or self.origin not in (1,2)
                or type(self.insight) is not int or not 0<=self.insight<=0x7fffffff):
            raise ValueError('Known baby/wild origin and representable raw insight required')

    @property
    def baby(self):return self.origin==2


@dataclass(frozen=True)
class TraitRules:
    revision: str
    initial_origin: int
    initial_insight: int

    @classmethod
    def load(cls):
        p=json.loads((OUT/'design/pet-traits-v1.json').read_text(encoding='utf-8'))
        if (p['revision']!='2026-10-23.pet-traits.1'
                or p['native']!={'insight_bean_offset':56,'insight_attribute':1160,'origin_bean_offset':180,'wild':1,'baby':2}
                or p['insight_limits']['minimum']!=0 or p['insight_limits']['maximum']!=0x7fffffff):
            raise ValueError('Pet traits policy requires review')
        initial=PetTraits(0,p['generation']['origin'],p['generation']['insight'])
        if (initial.origin,initial.insight)!=(2,0):raise ValueError('Pet traits generation baseline requires review')
        return cls(p['revision'],initial.origin,initial.insight)


def prepare(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_traits (
        pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id),policy TEXT NOT NULL,
        source TEXT NOT NULL,state TEXT NOT NULL);''')


def _owned(db,account,role,pet):
    if (type(pet) is not int or not 0<pet<=0x7fffffff or not db.in_transaction
            or not db.execute('SELECT 1 FROM inventory_pets p JOIN roles r ON r.id=p.role_id '
                'WHERE p.id=? AND r.id=? AND r.account_id=? AND p.released=0',(pet,role,account)).fetchone()):
        raise ValueError('Pet traits require an owned live pet transaction')


def initialize(db,account,role,pet,rules,origin,insight,*,source):
    _owned(db,account,role,pet)
    if source not in ('new_restoration_pet','explicit_known_import'):
        raise ValueError('Explicit pet traits initialization authority required')
    value=PetTraits(0,origin,insight)
    if db.execute('SELECT 1 FROM inventory_pet_traits WHERE pet_id=?',(pet,)).fetchone():
        raise ValueError('Pet traits already known; reset forbidden')
    db.execute('INSERT INTO inventory_pet_traits VALUES(?,?,?,?)',
               (pet,rules.revision,source,json.dumps(asdict(value))))
    db.execute('INSERT INTO inventory_versions(role_id,revision) VALUES(?,1) '
               'ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(role,))
    return value


def load(db,account,role,pet,rules):
    _owned(db,account,role,pet)
    row=db.execute('SELECT policy,source,state FROM inventory_pet_traits WHERE pet_id=?',(pet,)).fetchone()
    if (not row or row[0]!=rules.revision or row[1] not in ('new_restoration_pet','explicit_known_import')):
        raise ValueError('Pet traits require explicit known initialization or reconciliation')
    return PetTraits(**json.loads(row[2]))

"""Versioned known expansion points and immutable certification policy."""
from dataclasses import asdict,dataclass
import json
from types import MappingProxyType

from inspect_client import OUT


@dataclass(frozen=True)
class SkillProgress:
    version: int
    points: int

    def __post_init__(self):
        if (type(self.version) is not int or not 0<=self.version<0x7fffffff
                or type(self.points) is not int or not 0<=self.points<=10000):
            raise ValueError('Invalid known pet expansion progress')


@dataclass(frozen=True)
class LearningRules:
    revision: str
    thresholds: object
    initial_progress: int
    draw_upper_exclusive: int
    chances: object
    base_gain: int
    basic_gain: int
    advanced_gain: int
    basic_template: int
    advanced_template: int
    basic_level: int
    advanced_level: int

    @classmethod
    def load(cls):
        p=json.loads((OUT/'design/pet-skill-learning-v3.json').read_text(encoding='utf-8'))
        chances=p['probability'];gains=p['failure_progress'];cert=p['certification']
        values=(p['generation']['initial_progress'],chances['denominator'],gains['base'],
            gains['basic_extra'],gains['advanced_extra'],cert['basic_template'],cert['advanced_template'],
            cert['per_attempt_quantity'],cert['maximum_protected'])
        source_chances={'none':(10000,2000,1000,500,250,200,100,50,20,10,5,2),
            'basic':(0,1000,2000,1000,500,250,200,100,50,20,10,5),
            'both':(0,0,10000,2000,1000,500,250,200,100,50,20,10)}
        if (p['revision']!='2026-10-23.pet-skill-learning.3'
                or any(type(x) is not int for x in values)
                or values!=(0,10000,1,1,3,31254,31255,1,2)
                or any(type(v) is not int for mode in source_chances for v in chances[mode])
                or any(tuple(chances[mode])!=expected for mode,expected in source_chances.items())
                or cert['advanced_requires_basic'] is not True):
            raise ValueError('Pet certification policy requires implementation review')
        rows=json.loads((OUT/'catalogs/knight.gsp.item.cpetskillsuccessconfig.json').read_text(encoding='utf-8'))
        thresholds={int(r['attributes']['id']):int(r['attributes']['progress']) for r in rows}
        if thresholds!={0:0,1:10,2:20,3:40,4:80,5:100,6:200,7:400,8:1000,9:2000,10:4000,11:10000,12:0}:
            raise ValueError('Original pet expansion thresholds require review')
        items={int(r['attributes']['id']):r['attributes'] for r in
            json.loads((OUT/'catalogs/knight.gsp.item.citemattr.json').read_text(encoding='utf-8'))}
        if any(int(items[key]['itemtypeid'])!=81 for key in (values[5],values[6])):
            raise ValueError('Original certification item type requires review')
        return cls(p['revision'],MappingProxyType(thresholds),values[0],values[1],
                   MappingProxyType(source_chances),values[2],values[3],values[4],values[5],values[6],
                   int(items[values[5]]['needLevel']),int(items[values[6]]['needLevel']))


def prepare(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS inventory_pet_skill_progress (
        pet_id INTEGER PRIMARY KEY REFERENCES inventory_pets(id),
        policy TEXT NOT NULL,state TEXT NOT NULL);''')


def _owner(db,account,role,pet):
    if (type(pet) is not int or not 0<pet<=0x7fffffff or not db.in_transaction
            or not db.execute('SELECT 1 FROM inventory_pets p JOIN roles r ON r.id=p.role_id '
            'WHERE p.id=? AND p.role_id=? AND r.account_id=? AND p.released=0',(pet,role,account)).fetchone()):
        raise ValueError('Pet expansion progress requires an owned live pet transaction')


def initialize(db,account,role,pet,rules,points):
    _owner(db,account,role,pet);state=SkillProgress(0,points)
    if db.execute('SELECT 1 FROM inventory_pet_skill_progress WHERE pet_id=?',(pet,)).fetchone():
        raise ValueError('Known pet expansion progress cannot be reset')
    db.execute('INSERT INTO inventory_pet_skill_progress VALUES(?,?,?)',
               (pet,rules.revision,json.dumps(asdict(state))))
    db.execute('INSERT INTO inventory_versions(role_id,revision) VALUES(?,1) '
               'ON CONFLICT(role_id) DO UPDATE SET revision=revision+1',(role,))
    return state


def load(db,account,role,pet,rules):
    _owner(db,account,role,pet)
    row=db.execute('SELECT policy,state FROM inventory_pet_skill_progress WHERE pet_id=?',(pet,)).fetchone()
    if not row or row[0]!=rules.revision:
        raise ValueError('Pet expansion progress requires explicit known initialization or migration')
    return SkillProgress(**json.loads(row[1]))


def save(db,account,role,pet,rules,before,points):
    """Internal learning write; caller saves the shared inventory revision."""
    current=load(db,account,role,pet,rules)
    if current!=before:raise ValueError('Pet expansion progress version mismatch')
    after=before if points==before.points else SkillProgress(before.version+1,points)
    if after!=before:
        db.execute('UPDATE inventory_pet_skill_progress SET state=? WHERE pet_id=?',
                   (json.dumps(asdict(after)),pet))
    return after

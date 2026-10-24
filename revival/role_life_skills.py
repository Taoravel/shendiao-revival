"""Known personal life skills in the caller's current role transaction.

The original assist-skill cache is shared with seven practice types. This
Module owns the fourteen life-skill segment only; incremental messages preserve
other segments. It never initializes unknown historical roles during a read.
"""
from dataclasses import dataclass,replace,asdict
import hashlib,json
from inspect_client import OUT
from guild_research_protocol import RESEARCH_SKILLS
from role_practice import owner


@dataclass(frozen=True)
class LifeRules:
    skills: tuple
    skilled: tuple
    cost_rows: tuple
    fingerprint: str


@dataclass(frozen=True)
class LifeSkill:
    skill: int
    level: int
    proficiency: int


@dataclass(frozen=True)
class LifeSkillsSnapshot:
    role: int
    revision: int
    skills: tuple
    recipe: str
    origin: str


def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def load_rules():
    """Startup catalog validation, no production learning policy or grants."""
    rows=json.loads((OUT/'catalogs/knight.gsp.skill.clifeskill.json').read_text(encoding='utf-8'))
    attributes=tuple(sorted((int(r['attributes']['id']),int(r['attributes']['bNeedSkilled']))
        for r in rows if r['attributes']['bCanStudy']=='1'))
    costs=json.loads((OUT/'catalogs/knight.gsp.skill.clifeskillcost.json').read_text(encoding='utf-8'))
    if tuple(s for s,_ in attributes)!=tuple(sorted(RESEARCH_SKILLS)) or any(v not in (0,1) for _,v in attributes):
        raise ValueError('life_skill_catalog_changed')
    costs=tuple((int(r['attributes']['id']),tuple(sorted((k,int(v)) for k,v in r['attributes'].items() if k!='id'))) for r in costs)
    if tuple(n for n,_ in costs)!=tuple(range(1,161)) or any(not 0<=v<2**31 for _,row in costs for _,v in row):
        raise ValueError('life_skill_cost_catalog_changed')
    fingerprint=hashlib.sha256(encode((attributes,costs)).encode()).hexdigest()
    return LifeRules(tuple(s for s,_ in attributes),tuple(s for s,v in attributes if v),costs,fingerprint)


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS role_life_skill_profiles (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id),revision INTEGER NOT NULL,
        baseline TEXT NOT NULL,origin TEXT NOT NULL,recipe TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS role_life_skills (
        role_id INTEGER NOT NULL REFERENCES role_life_skill_profiles(role_id),skill INTEGER NOT NULL,
        level INTEGER NOT NULL,proficiency INTEGER NOT NULL,PRIMARY KEY(role_id,skill))''')


def validate(entries,rules):
    if (type(entries) is not tuple or any(type(s) is not LifeSkill for s in entries)
            or tuple(s.skill for s in entries)!=rules.skills
            or any(type(v) is not int for s in entries for v in (s.skill,s.level,s.proficiency))
            or any(not 0<=s.level<=160 or not 0<=s.proficiency<2**31 for s in entries)):
        raise ValueError('complete_life_skill_baseline_required')


def read(db,account,role,epoch,rules):
    owner(db,account,role,epoch)
    profile=db.execute('SELECT revision,origin,recipe FROM role_life_skill_profiles WHERE role_id=?',(role,)).fetchone()
    if not profile:raise ValueError('life_skill_profile_unknown')
    if profile[2]!=rules.fingerprint:raise ValueError('life_skill_recipe_changed')
    if type(profile[0]) is not int or not 0<=profile[0]<2**63:raise ValueError('life_skill_revision_invalid')
    entries=tuple(LifeSkill(*tuple(r)) for r in db.execute(
        'SELECT skill,level,proficiency FROM role_life_skills WHERE role_id=? ORDER BY skill',(role,)))
    validate(entries,rules)
    return LifeSkillsSnapshot(role,profile[0],entries,profile[2],profile[1])


def initialize(db,account,role,epoch,baseline,origin,rules):
    owner(db,account,role,epoch);validate(baseline,rules)
    if origin not in ('new_restoration_role','explicit_migration'):raise ValueError('explicit_life_skill_origin_required')
    encoded=encode([asdict(s) for s in baseline])
    old=db.execute('SELECT baseline,origin,recipe FROM role_life_skill_profiles WHERE role_id=?',(role,)).fetchone()
    if old:
        if tuple(old)!=(encoded,origin,rules.fingerprint):raise ValueError('life_skill_baseline_cannot_reset')
    else:
        db.execute('INSERT INTO role_life_skill_profiles VALUES(?,0,?,?,?)',(role,encoded,origin,rules.fingerprint))
        for s in baseline:db.execute('INSERT INTO role_life_skills VALUES(?,?,?,?)',(role,s.skill,s.level,s.proficiency))
    return read(db,account,role,epoch,rules)


def learn_one(db,account,role,epoch,skill,expected_revision,rules):
    """Caller has proved and paid a learning permit in this same transaction."""
    current=read(db,account,role,epoch,rules)
    if type(expected_revision) is not int or current.revision!=expected_revision:raise ValueError('life_skill_revision_conflict')
    if type(skill) is not int or skill not in rules.skills:raise ValueError('invalid_life_skill')
    before=next(s for s in current.skills if s.skill==skill)
    if before.level==160:raise ValueError('life_skill_supported_range_exhausted')
    if current.revision==2**63-1:raise ValueError('life_skill_revision_overflow')
    db.execute('UPDATE role_life_skills SET level=level+1 WHERE role_id=? AND skill=?',(role,skill))
    db.execute('UPDATE role_life_skill_profiles SET revision=revision+1 WHERE role_id=?',(role,))
    return read(db,account,role,epoch,rules)

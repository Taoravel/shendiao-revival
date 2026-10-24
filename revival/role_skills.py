"""Role-owned complete native OtherSkills ledger in the caller transaction.

Startup prepares schema/catalogs. Creation must explicitly authorize empty
skills before positions/leases; historical roles need a verified COMPLETE
baseline. Missing state is unknown. No commits, sends, inferred migration,
battle formulas or task reward receipts live here.
"""
from dataclasses import dataclass,asdict
import hashlib
import json
from inspect_client import OUT
from task_domain import valid_task_epoch
from battle_protocol import OTHER_SKILLS,other_skills


# Original display class6 mixes several learned containers. Native12d55f0
# selects manager+40 for class1/8 and special310202 before class4 dispatch.
OTHER_SKILL_IDS=frozenset((100007,100008,100009,310202,700004))
LOCAL_BASELINE_REVISION='2026-10-24.local-prologue-other-skills-baseline.1'
LOCAL_BASELINE_POLICY_SHA='f0224cd71d73fef5f9d57b841562a72875cbc625b7cec4d37feac703bc7661f5'
LOCAL_BASELINE_EVIDENCE_SHA='660fea5b20f5f14c96df00308d49176e93300ee7bc1ebfc215d6a3820598447d'
LOCAL_BASELINE_ORIGIN='designed_local_prologue_baseline'


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)


def _hash(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _text(value,limit=128):
    return type(value) is str and 1<=len(value)<=limit


def _sha(value):
    return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)


@dataclass(frozen=True)
class OtherSkillRules:
    revision:str
    catalog_ids:frozenset
    fingerprint:str
    maximum:int=128
    snapshot_flag:int=1


def load_other_skill_rules():
    """Startup only; verify display catalog separately from native wire scope.

    The26 display entries are not a common learned map. Only the five original
    manager+40 identities belong here. Lightness350001 uses manager+74, mounts
    use+80, and600018 uses+4c; no unknown baseline is silently filtered.
    """
    names=('cskillitem','cskillshowlist','cskillshowlistclient')
    tables={n:json.loads((OUT/('catalogs/knight.gsp.skill.'+n+'.json')).read_text(encoding='utf8')) for n in names}
    rows=[r for r in tables['cskillshowlist'] if int(r['attributes']['id'])==6]
    if len(rows)!=1:raise ValueError('Original other-skill class6 missing or duplicated')
    ids=tuple(map(int,rows[0]['lists']['skillnumber']))
    if len(ids)!=26 or len(set(ids))!=26 or 600005 in ids or not OTHER_SKILL_IDS<=set(ids):
        raise ValueError('Original class6 catalog changed; review namespace before use')
    for name in ('cskillitem','cskillshowlistclient'):
        found=[r['attributes'] for r in tables[name] if int(r['attributes']['id'])==100008]
        if len(found)!=1 or found[0]['skillname']!='太祖长拳':raise ValueError('Player first-skill identity changed')
        if name=='cskillshowlistclient' and found[0]['skilltype']!='1':raise ValueError('Player first-skill type changed')
    return OtherSkillRules('2026-10-24.newbie-first-skill.1',OTHER_SKILL_IDS,
        _hash(('native_other_skills_manager+0x40',sorted(OTHER_SKILL_IDS),tables)))


@dataclass(frozen=True)
class VerifiedOtherSkillBaseline:
    """Trusted migration input, never decoded from a client packet.

    entries is the verified complete native OtherSkills map, even when empty.
    evidence_sha256 identifies the independent full-baseline investigation.
    A restoration/chapter marker is not such evidence.
    """
    entries:tuple
    verification_id:str
    evidence_sha256:str


@dataclass(frozen=True)
class LocalPrologueBaselineRules:
    revision:str
    policy_sha256:str
    evidence_sha256:str
    task_pairs:tuple
    creation_profile:str
    creation_wallet_policy:str
    currency_fields:tuple


@dataclass(frozen=True)
class LocalPrologueBaselinePermit:
    """Task caller's frozen, fully audited first teaching COMMIT permission.

    Not a historical proof, client input, login permit or permission to skip
    Task cohort validation. The role ledger only owns this distinct enrollment.
    """
    account_id:int
    role_id:int
    policy_revision:str
    policy_sha256:str
    evidence_sha256:str
    migration_id:str
    creation_id:str
    chapter_id:str
    route_fingerprint:str
    teaching_task_id:int
    battle_task_id:int
    battle_id:str
    battle_admission_fingerprint:str
    battle_terminal_fingerprint:str
    eligibility_fingerprint:str
    teaching_operation_id:str
    original_epoch:object


@dataclass(frozen=True)
class LocalPrologueBaselineReceipt:
    migration_id:str
    policy_revision:str
    intent_fingerprint:str
    permit:LocalPrologueBaselinePermit
    initial_map_fingerprint:str


def load_local_prologue_baseline_rules(path=OUT/'design/local-prologue-other-skills-baseline-v1.json',*,
        attribute_rules=None,growth_rules=None,currency_rules=None):
    """Explicit startup adoption of the reviewed DESIGNED compatibility policy."""
    raw=path.read_bytes();policy=json.loads(raw)
    if (hashlib.sha256(raw).hexdigest()!=LOCAL_BASELINE_POLICY_SHA
            or policy['revision']!=LOCAL_BASELINE_REVISION or policy['origin']!=LOCAL_BASELINE_ORIGIN
            or tuple(policy['native_supported_ids'])!=tuple(sorted(OTHER_SKILL_IDS)) or policy['baseline_entries']!=[]):
        raise ValueError('Reviewed designed local-prologue baseline policy required')
    pairs=tuple(zip(policy['first_skill_task_ids'],policy['predecessor_battle_task_ids']))
    # These reads only run at explicit startup adoption. Task compares the real
    # stored creation document to this frozen public creation-profile contract.
    if attribute_rules is None:
        from role_attributes import load_attribute_rules
        attribute_rules=load_attribute_rules()
    if growth_rules is None:
        from role_growth import load_growth_rules
        growth_rules=load_growth_rules()
    if currency_rules is None:
        from currency import load_currency_rules
        currency_rules=load_currency_rules()
    if (attribute_rules.initial_profile is None or attribute_rules.initial_profile.level!=1
            or attribute_rules.growth_policy!=growth_rules.revision):
        raise ValueError('Reviewed local creation profile required')
    creation=_json(dict(format=1,source='design/role-attributes-v1.json#new_role_designed_baseline',
        provenance='designed',growth_policy=growth_rules.revision,attribute_policy=attribute_rules.revision,
        profile=asdict(attribute_rules.initial_profile)))
    return LocalPrologueBaselineRules(LOCAL_BASELINE_REVISION,LOCAL_BASELINE_POLICY_SHA,LOCAL_BASELINE_EVIDENCE_SHA,
        pairs,creation,currency_rules.revision,tuple(sorted(currency_rules.task_fields.items())))


@dataclass(frozen=True)
class OtherSkillsSnapshot:
    role_id:int
    revision:int
    entries:tuple
    catalog_fingerprint:str
    origin:str
    source_id:str
    baseline_fingerprint:str


def prepare_other_skill_storage(db):
    """Startup DDL only; no historical row is initialized."""
    db.execute('''CREATE TABLE IF NOT EXISTS role_other_skills (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id),revision INTEGER NOT NULL,
        skills TEXT NOT NULL,catalog_fingerprint TEXT NOT NULL,origin TEXT NOT NULL,
        source_id TEXT NOT NULL,baseline_fingerprint TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS role_other_skill_baseline_migrations (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id),policy_revision TEXT NOT NULL,
        migration_id TEXT UNIQUE NOT NULL,intent_fingerprint TEXT NOT NULL,
        permit TEXT NOT NULL,initial_map_fingerprint TEXT NOT NULL)''')


def _owner(db,aid,rid,epoch=None,*,creation=False):
    if (not db.in_transaction or type(aid) is not int or type(rid) is not int
            or not db.execute('SELECT 1 FROM roles WHERE id=? AND account_id=?',(rid,aid)).fetchone()):
        raise ValueError('Other skills require owned caller transaction')
    if not creation and (not valid_task_epoch(epoch) or not db.execute(
            'SELECT 1 FROM role_leases WHERE role_id=? AND epoch=? AND active=1',(rid,epoch)).fetchone()):
        raise ValueError('Other-skill login lease mismatch')


def _entries(entries,rules):
    if (type(rules) is not OtherSkillRules or type(entries) is not tuple or len(entries)>rules.maximum
            or any(type(pair) is not tuple or len(pair)!=2 or any(type(x) is not int or not 0<x<2**31 for x in pair)
                or pair[0] not in rules.catalog_ids for pair in entries)
            or len({p[0] for p in entries})!=len(entries)):
        raise ValueError('Complete supported native OtherSkills integer map required')
    return tuple(sorted(entries))


def _read(db,rid,rules):
    row=db.execute('SELECT revision,skills,catalog_fingerprint,origin,source_id,baseline_fingerprint '
        'FROM role_other_skills WHERE role_id=?',(rid,)).fetchone()
    if row is None:return None
    try:
        raw=json.loads(row[1]);entries=tuple(tuple(p) for p in raw)
    except (TypeError,ValueError):raise ValueError('Malformed stored other-skill baseline') from None
    entries=_entries(entries,rules)
    if (type(row[0]) is not int or not 0<=row[0]<2**63 or row[2]!=rules.fingerprint
            or row[3] not in ('new_role_creation','verified_complete_baseline',LOCAL_BASELINE_ORIGIN)
            or not _text(row[4]) or not _sha(row[5]) or _json(entries)!=row[1]):
        raise ValueError('Unsupported other-skill baseline or catalog migration required')
    if row[3]==LOCAL_BASELINE_ORIGIN:
        receipt=_local_receipt(db,rid)
        if (receipt is None or (row[4],row[5])!=(receipt.migration_id,receipt.intent_fingerprint)
                or receipt.permit.account_id!=db.execute('SELECT account_id FROM roles WHERE id=?',(rid,)).fetchone()[0]):
            raise ValueError('Designed baseline has no matching immutable migration receipt')
    return OtherSkillsSnapshot(rid,row[0],entries,*row[2:])


def read_other_skills(db,aid,rid,epoch,rules):
    """Pure current authority: None means unknown; callers must not send empty."""
    _owner(db,aid,rid,epoch)
    return _read(db,rid,rules)


def authorize_new_role_other_skills(db,aid,rid,creation_id,rules):
    """Trusted actual creation workflow only, before position/lease insertion.

    Caller MUST have just inserted this role in this SAME transaction. Existing
    origin labels are deliberately not read as authority. No login redeems an
    absent record. New-role creation rollback also removes this authorization.
    """
    _owner(db,aid,rid,creation=True)
    if (not _text(creation_id) or db.execute('SELECT 1 FROM role_leases WHERE role_id=?',(rid,)).fetchone()
            or db.execute('SELECT 1 FROM role_positions WHERE role_id=?',(rid,)).fetchone()
            or db.execute('SELECT level FROM roles WHERE id=?',(rid,)).fetchone()[0]!=1
            or _read(db,rid,rules) is not None):
        raise ValueError('Explicit fresh creation-only other-skill authorization required')
    db.execute('INSERT INTO role_other_skills VALUES(?,0,?,?,?,?,?)',
        (rid,'[]',rules.fingerprint,'new_role_creation',creation_id,_hash(('new_role_creation',creation_id,rid))))
    return _read(db,rid,rules)


def adopt_verified_other_skills(db,aid,rid,epoch,rules,baseline):
    """Explicit one-time complete baseline adoption; never merge a partial map."""
    _owner(db,aid,rid,epoch)
    if (type(baseline) is not VerifiedOtherSkillBaseline or not _text(baseline.verification_id)
            or not _sha(baseline.evidence_sha256)):
        raise ValueError('Explicit verified complete other-skill baseline required')
    entries=_entries(baseline.entries,rules)
    fingerprint=_hash((entries,baseline.verification_id,baseline.evidence_sha256))
    old=_read(db,rid,rules)
    if old is not None:
        if (old.origin,old.source_id,old.baseline_fingerprint)!=('verified_complete_baseline',baseline.verification_id,fingerprint):
            raise ValueError('Other-skill baseline cannot be replaced or reset')
        return old
    db.execute('INSERT INTO role_other_skills VALUES(?,0,?,?,?,?,?)',
        (rid,_json(entries),rules.fingerprint,'verified_complete_baseline',baseline.verification_id,fingerprint))
    return _read(db,rid,rules)


def _local_permit(permit):
    if (type(permit) is not LocalPrologueBaselinePermit
            or any(type(v) is not int or not 0<v<2**63 for v in (permit.account_id,permit.role_id,
                permit.teaching_task_id,permit.battle_task_id))
            or permit.policy_revision!=LOCAL_BASELINE_REVISION or permit.policy_sha256!=LOCAL_BASELINE_POLICY_SHA
            or permit.evidence_sha256!=LOCAL_BASELINE_EVIDENCE_SHA or not valid_task_epoch(permit.original_epoch)
            or any(not _text(v) for v in (permit.migration_id,permit.creation_id,permit.chapter_id,
                permit.battle_id,permit.teaching_operation_id))
            or any(not _sha(v) for v in (permit.route_fingerprint,permit.battle_admission_fingerprint,
                permit.battle_terminal_fingerprint,permit.eligibility_fingerprint))):
        raise ValueError('Explicit policy-bound local teaching commit permit required')


def _local_identity(permit):
    result=asdict(permit);result.pop('original_epoch')
    return result


def _local_receipt(db,rid):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='role_other_skill_baseline_migrations'").fetchone():
        return None
    row=db.execute('SELECT policy_revision,migration_id,intent_fingerprint,permit,initial_map_fingerprint '
        'FROM role_other_skill_baseline_migrations WHERE role_id=?',(rid,)).fetchone()
    if row is None:return None
    try:permit=LocalPrologueBaselinePermit(**json.loads(row[3]))
    except (TypeError,ValueError):raise ValueError('Malformed designed-baseline receipt') from None
    _local_permit(permit)
    if (permit.role_id!=rid or row[0]!=permit.policy_revision or row[1]!=permit.migration_id
            or row[2]!=_hash(_local_identity(permit)) or row[3]!=_json(asdict(permit)) or row[4]!=_hash(())):
        raise ValueError('Conflicting designed-baseline receipt identity')
    return LocalPrologueBaselineReceipt(row[1],row[0],row[2],permit,row[4])


def read_local_prologue_baseline_receipt(db,aid,rid,epoch,rules,policy):
    """Pure audit of the original compatibility decision, not a new permit."""
    _owner(db,aid,rid,epoch)
    receipt=_local_receipt(db,rid)
    if receipt is not None:
        current=_read(db,rid,rules)
        if (type(policy) is not LocalPrologueBaselineRules or policy.policy_sha256!=receipt.permit.policy_sha256
                or current is None or current.origin!=LOCAL_BASELINE_ORIGIN
                or current.baseline_fingerprint!=receipt.intent_fingerprint):
            raise ValueError('Designed migration receipt and current ledger differ')
    return receipt


def enroll_local_prologue_other_skills(db,aid,rid,epoch,rules,policy,permit):
    """Task COMMIT caller only: complete designed baseline + unique receipt.

    Cohort/NPC/task proof belongs to Task and must be checked in this same
    transaction. Existing identical receipt is read first and returns current
    learned values across leases; accepted original_epoch is never rewritten.
    """
    _owner(db,aid,rid,epoch);_local_permit(permit);_entries((),rules)
    if (type(policy) is not LocalPrologueBaselineRules or policy.revision!=LOCAL_BASELINE_REVISION
            or policy.policy_sha256!=LOCAL_BASELINE_POLICY_SHA or policy.evidence_sha256!=LOCAL_BASELINE_EVIDENCE_SHA
            or (permit.account_id,permit.role_id)!=(aid,rid)
            or (permit.teaching_task_id,permit.battle_task_id) not in policy.task_pairs):
        raise ValueError('Reviewed compatibility policy and original task pair required')
    fingerprint=_hash(_local_identity(permit));receipt=_local_receipt(db,rid);old=_read(db,rid,rules)
    if receipt is not None:
        if receipt.intent_fingerprint!=fingerprint or old is None or old.origin!=LOCAL_BASELINE_ORIGIN:
            raise ValueError('Conflicting designed baseline or lost current ledger')
        return old
    if old is not None:return old
    if permit.original_epoch!=epoch or type(permit.original_epoch) is not type(epoch):
        raise ValueError('New designed enrollment requires this accepted current epoch')
    db.execute('INSERT INTO role_other_skill_baseline_migrations VALUES(?,?,?,?,?,?)',
        (rid,policy.revision,permit.migration_id,fingerprint,_json(asdict(permit)),_hash(())))
    db.execute('INSERT INTO role_other_skills VALUES(?,0,?,?,?,?,?)',
        (rid,'[]',rules.fingerprint,LOCAL_BASELINE_ORIGIN,permit.migration_id,fingerprint))
    return _read(db,rid,rules)


def grant_other_skill(db,aid,rid,epoch,rules,skill_id,value,*,expected_revision):
    """RoleOwner-only CAS, preserve every other key and max(existing,value).

    This is not an independent task settlement authority. The task caller
    validates its immutable accepted command and owns its one durable receipt.
    Retries with that receipt skip this method and read the current full map.
    """
    _owner(db,aid,rid,epoch);_entries(((skill_id,value),),rules)
    current=_read(db,rid,rules)
    if (current is None or type(expected_revision) is not int or current.revision!=expected_revision):
        raise ValueError('Known complete other-skill baseline and current revision required')
    values=dict(current.entries);values[skill_id]=max(values.get(skill_id,0),value)
    entries=_entries(tuple(values.items()),rules)
    if entries==current.entries:return current
    if current.revision>=2**63-1:raise ValueError('Other-skill revision exhausted')
    changed=db.execute('UPDATE role_other_skills SET skills=?,revision=revision+1 '
        'WHERE role_id=? AND revision=?',(_json(entries),rid,expected_revision))
    if changed.rowcount!=1:raise ValueError('Other-skill revision changed')
    return _read(db,rid,rules)


def other_skill_messages(snapshot,rules):
    """Native COMPLETE replacement; flag1 still removes omitted original keys."""
    if (type(snapshot) is not OtherSkillsSnapshot or snapshot.catalog_fingerprint!=rules.fingerprint
            or type(snapshot.revision) is not int or snapshot.revision<0):
        raise ValueError('Known complete current other-skill snapshot required')
    entries=_entries(snapshot.entries,rules)
    return ((OTHER_SKILLS,other_skills(dict(entries),rules.snapshot_flag)),)

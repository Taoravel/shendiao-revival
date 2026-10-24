"""Explicit complete role Mingwen source, including soul-cap inscription22.

Startup schema and caller-transaction CAS only; no implicit unlocks, payments,
connections, commits or sends. Missing is unknown, never an inactive ledger.
"""
from dataclasses import dataclass,asdict
import json
from inspect_client import OUT


REVISION='2026-10-24.role-mingwen-source.1'


@dataclass(frozen=True)
class MingwenEntry:
    entry_id: int
    raw2: int
    raw3: int
    raw_active: int

    def __post_init__(self):
        if (type(self.entry_id) is not int or not 1<=self.entry_id<=22
                or any(type(v) is not int or not -0x80000000<=v<=0x7fffffff
                    for v in (self.raw2,self.raw3,self.raw_active))):
            raise ValueError('Exact known original four-field Mingwen entry required')


@dataclass(frozen=True)
class MingwenState:
    role_id: int
    version: int
    policy: str
    source_ref: str
    entries: tuple

    def __post_init__(self):
        if (type(self.role_id) is not int or not 0<self.role_id<2**63
                or type(self.version) is not int or not 0<=self.version<2**63-1
                or type(self.policy) is not str or self.policy!=REVISION or type(self.source_ref) is not str or not 1<=len(self.source_ref)<=160
                or type(self.entries) is not tuple or len(self.entries)!=22
                or any(type(e) is not MingwenEntry for e in self.entries)
                or tuple(e.entry_id for e in self.entries)!=tuple(range(1,23))):
            raise ValueError('Complete explicitly known versioned22-entry Mingwen state required')

    @property
    def soul_cap_increment(self):
        # Original1545ef0 is ==1, not nonzero, and22 is a one-based index.
        return int(self.entries[21].raw_active==1)


@dataclass(frozen=True)
class MingwenRules:
    revision: str

    def __post_init__(self):
        if type(self.revision) is not str or self.revision!=REVISION:raise ValueError('Frozen explicitly selected Mingwen source policy required')

    @classmethod
    def load(cls):
        policy=json.loads((OUT/'design/role-mingwen-source-v1.json').read_text(encoding='utf-8'))
        expected={'entry_ids':'1..22','pet_soul_cap_entry':22,'active_equals':1,
            'native_fields':['entry_id','raw2','raw3','raw_active']}
        rows=json.loads((OUT/'catalogs/knight.gsp.game.cmingwen.json').read_text(encoding='utf-8'))
        originals={int(r['attributes']['id']):r['attributes'] for r in rows}
        if (policy['revision']!=REVISION or policy['client_verified']!=expected
                or any(type(policy['client_verified'][key]) is not int for key in ('pet_soul_cap_entry','active_equals'))
                or len(rows)!=22 or set(originals)!=set(range(1,23))
                or originals[22]['name']!='铭文·简易' or int(originals[22]['maxlevel'])!=1):
            raise ValueError('Original Mingwen22 source requires explicit reconciliation')
        return cls(REVISION)


@dataclass(frozen=True)
class MingwenBasis:
    account_id: int
    inventory_revision: int
    state: MingwenState
    origin: str
    raw_state: str
    baseline_source: str

    def __post_init__(self):
        if (type(self.account_id) is not int or not 0<self.account_id<2**63
                or type(self.inventory_revision) is not int or not 0<=self.inventory_revision<2**63-1
                or type(self.state) is not MingwenState
                or any(type(v) is not str for v in (self.origin,self.raw_state,self.baseline_source))):
            raise ValueError('Complete frozen owned Mingwen source basis required')


def prepare(db):
    """Startup only; establishes no role state or activation."""
    db.execute('''CREATE TABLE IF NOT EXISTS role_mingwen_profiles (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id),policy TEXT NOT NULL,
        origin TEXT NOT NULL,baseline TEXT NOT NULL,state TEXT NOT NULL)''')


def _owned(db,inventory,rules):
    if type(rules) is not MingwenRules:raise ValueError('Frozen current Mingwen rules required')
    return inventory.immutable_snapshot_transaction(db)


def _json(state):return json.dumps(asdict(state),sort_keys=True,separators=(',',':'),ensure_ascii=False)


def _decode(raw):
    value=json.loads(raw);value['entries']=tuple(MingwenEntry(**e) for e in value['entries'])
    return MingwenState(**value)


@dataclass(frozen=True)
class MingwenStateSource:
    state: MingwenState
    origin: str
    raw_state: str
    baseline_source: str


def read_state_source(db,account_id,role_id,rules):
    """Owned primitive growth source read; no recursive pet projection.

    This internal read is not session admission, an unlock or a write permit.
    Current session reads/writes continue through the epoch-fenced Interface.
    """
    if (not db.in_transaction or type(rules) is not MingwenRules
            or any(type(v) is not int or not 0<v<2**63 for v in (account_id,role_id))
            or not db.execute('SELECT 1 FROM roles WHERE id=? AND account_id=?',(role_id,account_id)).fetchone()):
        raise ValueError('Owned primitive Mingwen source transaction required')
    row=db.execute('SELECT policy,origin,baseline,state FROM role_mingwen_profiles WHERE role_id=?',
        (role_id,)).fetchone()
    if row is None:return None
    if row[0]!=rules.revision or row[1] not in ('explicit_known_mingwen_ledger','mingwen_change'):
        raise ValueError('Unknown Mingwen source policy or provenance')
    baseline,current=_decode(row[2]),_decode(row[3])
    if (baseline.role_id!=role_id or current.role_id!=role_id
            or baseline.version!=0 or baseline.source_ref!=current.source_ref
            or row[1]=='explicit_known_mingwen_ledger' and current!=baseline
            or row[1]=='mingwen_change' and current.version==0):
        raise ValueError('Current complete Mingwen state diverges from its immutable baseline')
    return MingwenStateSource(current,row[1],row[3],row[2])


def read(db,inventory,rules):
    snapshot=_owned(db,inventory,rules)
    source=read_state_source(db,inventory.account_id,inventory.role_id,rules)
    if source is None:return None
    return MingwenBasis(inventory.account_id,snapshot.inventory_revision,source.state,
        source.origin,source.raw_state,source.baseline_source)


def _advance(db,inventory,version):
    if version==0:
        changed=db.execute('INSERT INTO inventory_versions(role_id,revision) VALUES(?,1) '
            'ON CONFLICT(role_id) DO UPDATE SET revision=revision+1 WHERE revision=0',(inventory.role_id,)).rowcount
    else:
        changed=db.execute('UPDATE inventory_versions SET revision=revision+1 WHERE role_id=? AND revision=?',
            (inventory.role_id,version)).rowcount
    if changed!=1:
        raise ValueError('Mingwen inventory source changed')


def initialize(db,inventory,rules,state,origin):
    snapshot=_owned(db,inventory,rules)
    if (type(state) is not MingwenState or state.role_id!=inventory.role_id or state.policy!=rules.revision
            or state.version!=0 or origin!='explicit_known_mingwen_ledger'):
        raise ValueError('Trusted explicit complete original Mingwen import required')
    body=_json(state)
    old=db.execute('SELECT policy,baseline FROM role_mingwen_profiles WHERE role_id=?',(inventory.role_id,)).fetchone()
    if old is not None:
        if old!=(rules.revision,body):raise ValueError('Existing Mingwen baseline cannot be reset')
        return read(db,inventory,rules)
    db.execute('INSERT INTO role_mingwen_profiles VALUES(?,?,?,?,?)',(inventory.role_id,rules.revision,origin,body,body))
    _advance(db,inventory,snapshot.inventory_revision)
    return read(db,inventory,rules)


def replace_state(db,inventory,rules,before,after):
    """Source CAS only. Join grants/resources/receipts/encoding before commit.

    ANY exception requires outer rollback. Original sparse message updates do
    not authorize resetting omitted entries or granting inscription ownership.
    """
    if (type(rules) is not MingwenRules or type(before) is not MingwenBasis or before.account_id!=inventory.account_id
            or type(after) is not MingwenState or after.version!=before.state.version+1
            or after.role_id!=before.state.role_id or after.policy!=rules.revision
            or after.source_ref!=before.state.source_ref):
        raise ValueError('Exactly next same-source complete Mingwen state required')
    if read(db,inventory,rules)!=before:raise ValueError('Current Mingwen source changed')
    if db.execute('UPDATE role_mingwen_profiles SET origin=?,state=? WHERE role_id=? AND policy=? '
            'AND origin=? AND baseline=? AND state=?',('mingwen_change',_json(after),inventory.role_id,rules.revision,
                before.origin,before.baseline_source,before.raw_state)).rowcount!=1:
        raise ValueError('Mingwen complete source CAS failed')
    _advance(db,inventory,before.inventory_revision)
    return read(db,inventory,rules)

"""Role-owned combat practice progression; joins the caller's transaction.

The cash purchase requires a guild-owned durable material reservation. This
Module never writes guild resources, guild permits or target network state.
"""
from dataclasses import dataclass,asdict
import json
from types import MappingProxyType
from inspect_client import OUT


@dataclass(frozen=True)
class PracticeRules:
    revision: str
    skills: tuple
    cash_costs: object
    gain: int
    materials: int
    tenure_ms: int
    level_cap: int
    levels: object
    initial_materials: int
    materials_origin: str
    receipt_limit: int
    pill_item: int
    pill_gains: object
    pill_recipe: str


@dataclass(frozen=True)
class PracticeState:
    skill: int
    level: int
    experience: int
    revision: int


@dataclass(frozen=True)
class PracticeReceipt:
    guild: int
    reservation: str
    state: PracticeState
    balances: tuple


@dataclass(frozen=True)
class PillPracticeReceipt:
    guild: int
    reservation: str
    state: PracticeState
    item_key: int
    inventory: object
    messages: tuple = ()


def load_rules(policy=None):
    if policy is None:policy=json.loads((OUT/'design/recovery-baseline.json').read_text('utf-8'))['organizations']
    raw=policy['individual_practice'];skills=tuple(raw['skill_ids']);costs=tuple(raw['cash_costs'])
    pill_gains=tuple(raw['pill_gains'])
    rows=json.loads((OUT/'catalogs/knight.gsp.skill.cadvancedability.json').read_text('utf-8'))
    levels={int(r['attributes']['id']):tuple(int(r['attributes'][k]) for k in ('levelneed','expneed','reputationneed')) for r in rows}
    if (skills!=tuple(range(360001,360008)) or len(costs)!=7
        or any(type(n) is not int or not 0<n<2**31 for n in costs)
        or raw['gain']!=10 or raw['materials']!=3 or raw['tenure_ms']!=604800000
        or raw['level_cap']!=50 or raw['initial_materials']!=0 or raw['currency']!='cash'
        or type(raw['materials_origin']) is not str or not raw['materials_origin']
        or type(raw['revision']) is not str or not raw['revision']
        or type(raw['receipt_limit']) is not int or not 1<=raw['receipt_limit']<=10000
        or type(raw['pill_item']) is not int or raw['pill_item']!=36747
        or any(type(n) is not int for n in pill_gains) or pill_gains!=(20,20,20,30,30,30,30)
        or raw['pill_selection']!='bound_first_then_slot_key'
        or type(raw['pill_recipe_revision']) is not str or not raw['pill_recipe_revision']
        or set(levels)!=set(range(1,52))
        or any(any(n<0 or n>=2**31 for n in row) or row[1]==0 for row in levels.values())):
        raise ValueError('invalid_individual_practice_policy')
    return PracticeRules(raw['revision'],skills,MappingProxyType(dict(zip(skills,costs))),raw['gain'],raw['materials'],
        raw['tenure_ms'],raw['level_cap'],MappingProxyType(levels),raw['initial_materials'],raw['materials_origin'],raw['receipt_limit'],
        raw['pill_item'],MappingProxyType(dict(zip(skills,pill_gains))),raw['pill_recipe_revision'])


def validate(state,rules):
    if (not isinstance(state,PracticeState) or state.skill not in rules.skills
        or any(type(n) is not int for n in (state.skill,state.level,state.experience,state.revision))
        or not 0<=state.level<=rules.level_cap or not 0<=state.revision<2**63
        or not 0<=state.experience<rules.levels[state.level+1][1]
        or state.level==rules.level_cap and state.experience!=0):
        raise ValueError('invalid_practice_state')


def plan(state,role_level,prestige,rules,*,mode=0):
    validate(state,rules)
    if type(mode) is not int or mode not in (0,1):raise ValueError('unsupported_practice_mode')
    if state.revision==2**63-1:raise ValueError('practice_revision_overflow')
    if (type(role_level) is not int or not 1<=role_level<=155
        or type(prestige) is not int or not 0<=prestige<2**31):raise ValueError('practice_ordinary_role_or_prestige_unknown')
    level=state.level;experience=state.experience+(rules.pill_gains[state.skill] if mode==1 else rules.gain)
    if level==rules.level_cap:raise ValueError('practice_level_cap')
    need_level,need_exp,need_prestige=rules.levels[level+1]
    if role_level<need_level or prestige<need_prestige:raise ValueError('practice_level_or_prestige_cap')
    while experience>=need_exp:
        experience-=need_exp;level+=1
        if level==rules.level_cap:
            if experience:raise ValueError('practice_level_cap')
            break
        need_level,need_exp,need_prestige=rules.levels[level+1]
        if experience>=need_exp and (role_level<need_level or prestige<need_prestige):
            raise ValueError('practice_level_or_prestige_cap')
    return PracticeState(state.skill,level,experience,state.revision+1)


def prepare(db):
    db.execute('''CREATE TABLE IF NOT EXISTS role_practice_profiles (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id),policy TEXT NOT NULL,baseline TEXT NOT NULL,origin TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS role_practice_skills (
        role_id INTEGER NOT NULL REFERENCES role_practice_profiles(role_id),skill INTEGER NOT NULL,
        level INTEGER NOT NULL,experience INTEGER NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(role_id,skill))''')
    db.execute('''CREATE TABLE IF NOT EXISTS role_practice_receipts (
        role_id INTEGER NOT NULL REFERENCES roles(id),guild INTEGER NOT NULL,reservation TEXT NOT NULL,
        fingerprint TEXT NOT NULL,skill INTEGER NOT NULL,PRIMARY KEY(role_id,guild,reservation))''')
    db.execute('''CREATE TABLE IF NOT EXISTS role_practice_pill_consumption (
        role_id INTEGER NOT NULL,guild INTEGER NOT NULL,reservation TEXT NOT NULL,item_key INTEGER NOT NULL,
        recipe TEXT NOT NULL,PRIMARY KEY(role_id,guild,reservation),
        FOREIGN KEY(role_id,guild,reservation) REFERENCES role_practice_receipts(role_id,guild,reservation))''')


def owner(db,account,role,epoch):
    if not db.in_transaction:raise ValueError('practice_requires_role_transaction')
    if any(type(n) is not int or n<=0 for n in (account,role)):raise ValueError('invalid_practice_owner')
    if not db.execute('''SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id
        WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1''',(role,account,str(epoch))).fetchone():
        raise ValueError('practice_stale_role_lease')


def read(db,account,role,epoch,rules):
    owner(db,account,role,epoch)
    profile=db.execute('SELECT policy FROM role_practice_profiles WHERE role_id=?',(role,)).fetchone()
    if not profile:raise ValueError('practice_profile_unknown')
    if profile[0]!=rules.revision:raise ValueError('practice_policy_migration_required')
    states=tuple(PracticeState(*tuple(r)) for r in db.execute(
        'SELECT skill,level,experience,revision FROM role_practice_skills WHERE role_id=? ORDER BY skill',(role,)))
    if tuple(s.skill for s in states)!=rules.skills:raise ValueError('practice_profile_incomplete')
    for state in states:validate(state,rules)
    return states


def initialize(db,account,role,epoch,baseline,origin,rules):
    owner(db,account,role,epoch)
    if (type(baseline) is not tuple or any(not isinstance(s,PracticeState) for s in baseline)
        or tuple(s.skill for s in baseline)!=rules.skills
        or origin not in ('new_restoration_role','explicit_migration')):raise ValueError('explicit_practice_baseline_required')
    for state in baseline:
        validate(state,rules)
        if state.revision!=0:raise ValueError('initial_practice_revision_required')
    encoded=json.dumps([asdict(s) for s in baseline],sort_keys=True,separators=(',',':'))
    old=db.execute('SELECT policy,baseline,origin FROM role_practice_profiles WHERE role_id=?',(role,)).fetchone()
    if old:
        if tuple(old)!=(rules.revision,encoded,origin):raise ValueError('practice_baseline_cannot_reset')
    else:
        db.execute('INSERT INTO role_practice_profiles VALUES(?,?,?,?)',(role,rules.revision,encoded,origin))
        for state in baseline:
            db.execute('INSERT INTO role_practice_skills VALUES(?,?,?,?,?)',
                (role,state.skill,state.level,state.experience,state.revision))
    return read(db,account,role,epoch,rules)


def settle(db,account,role,epoch,guild,reservation,now,rules,currency_rules):
    """Role-owner transaction: verify guild reservation, debit, progress, receipt.

    Resolution/compensation is a separate guild-owner command. The local
    Adapter fences cancellation with the same DB transaction, not a Python lock.
    Replay returns current absolute skill/wallet values after verifying receipt.
    """
    from guild_practice import permit,eligibility,require_open
    from currency import CurrencyChange,apply_currency,read_wallet
    owner(db,account,role,epoch)
    if (type(reservation) is not str or not 1<=len(reservation)<=96
        or type(now) is not int or now<0):raise ValueError('invalid_practice_settlement')
    grant=permit(db,guild,role,reservation)
    if grant.policy!=rules.revision:raise ValueError('practice_policy_migration_required')
    validate(grant.before,rules)
    if grant.mode!=0 or grant.gain!=rules.gain or grant.item_template!=0 or grant.pill_recipe:
        raise ValueError('practice_cash_recipe_required')
    states=read(db,account,role,epoch,rules)
    current=next((s for s in states if s.skill==grant.before.skill),None)
    receipt=db.execute('SELECT fingerprint FROM role_practice_receipts WHERE role_id=? AND guild=? AND reservation=?',
        (role,guild,reservation)).fetchone()
    if receipt:
        if receipt[0]!=grant.fingerprint or grant.status=='cancelled':raise ValueError('practice_receipt_conflict')
        return PracticeReceipt(guild,reservation,current,read_wallet(db,account,role,epoch,currency_rules))
    if grant.status!='reserved':raise ValueError('practice_reservation_not_active')
    if grant.epoch!=str(epoch) or now>=grant.deadline_ms:raise ValueError('practice_reservation_expired_or_stale')
    m,_,level,prestige=eligibility(db,guild,role,now,rules)
    if (m['family_token'],m['member_token'])!=(grant.family_token,grant.member_token):
        raise ValueError('practice_membership_changed')
    require_open(db,guild,grant.before.skill)
    if current!=grant.before:raise ValueError('practice_revision_conflict')
    if (grant.cash!=rules.cash_costs[current.skill] or grant.materials!=rules.materials):
        raise ValueError('practice_reservation_recipe_conflict')
    after=plan(current,level,prestige,rules)
    debit_id='practice:'+str(guild)+':'+reservation
    if db.execute('SELECT 1 FROM role_wallet_receipts WHERE role_id=? AND settlement_id=?',(role,debit_id)).fetchone():
        raise ValueError('practice_orphan_currency_receipt')
    apply_currency(db,account,role,epoch,CurrencyChange(debit_id,'skill_training',
        'guild-practice:'+str(guild)+':'+str(current.skill),(('cash',-grant.cash),)),currency_rules)
    db.execute('UPDATE role_practice_skills SET level=?,experience=?,revision=? WHERE role_id=? AND skill=?',
        (after.level,after.experience,after.revision,role,current.skill))
    db.execute('INSERT INTO role_practice_receipts VALUES(?,?,?,?,?)',
        (role,guild,reservation,grant.fingerprint,current.skill))
    return PracticeReceipt(guild,reservation,after,read_wallet(db,account,role,epoch,currency_rules))


def settle_pill(db,account,role,epoch,guild,reservation,now,rules,inventory,*,precommit=None):
    """One original pill and XP in the current role transaction; no wallet read.

    Native requests have no item key. The trusted role Adapter selects a current
    carried stack deterministically and records its key. Encoding failures in
    the optional current-snapshot callback roll back consumption and XP too.
    """
    from guild_practice import permit,eligibility,require_open
    from inventory import Inventory,AssetChange
    from npc_transactions import precommit_messages
    owner(db,account,role,epoch)
    if (not isinstance(inventory,Inventory) or (inventory.account_id,inventory.role_id)!=(account,role)
        or str(inventory.epoch)!=str(epoch)):raise ValueError('practice_inventory_owner_mismatch')
    if (type(reservation) is not str or not 1<=len(reservation)<=96
        or type(now) is not int or now<0):raise ValueError('invalid_practice_settlement')
    grant=permit(db,guild,role,reservation)
    if grant.policy!=rules.revision:raise ValueError('practice_policy_migration_required')
    validate(grant.before,rules)
    if (grant.mode!=1 or grant.item_template!=rules.pill_item or grant.cash!=0 or grant.materials!=0
        or grant.gain!=rules.pill_gains.get(grant.before.skill) or grant.pill_recipe!=rules.pill_recipe):
        raise ValueError('practice_pill_recipe_required')
    current=next(s for s in read(db,account,role,epoch,rules) if s.skill==grant.before.skill)
    receipt=db.execute('SELECT fingerprint FROM role_practice_receipts WHERE role_id=? AND guild=? AND reservation=?',
        (role,guild,reservation)).fetchone()
    if receipt:
        if receipt[0]!=grant.fingerprint or grant.status=='cancelled':raise ValueError('practice_receipt_conflict')
        used=db.execute('SELECT item_key,recipe FROM role_practice_pill_consumption WHERE role_id=? AND guild=? AND reservation=?',
            (role,guild,reservation)).fetchone()
        if not used or used[1]!=grant.pill_recipe:raise ValueError('practice_pill_receipt_unknown')
        messages=precommit_messages(precommit,db,inventory,replayed=True)
        return PillPracticeReceipt(guild,reservation,current,used[0],inventory.immutable_snapshot_transaction(db,epoch=epoch),messages)
    if grant.status!='reserved':raise ValueError('practice_reservation_not_active')
    if grant.epoch!=str(epoch) or now>=grant.deadline_ms:raise ValueError('practice_reservation_expired_or_stale')
    m,_,level,prestige=eligibility(db,guild,role,now,rules)
    if (m['family_token'],m['member_token'])!=(grant.family_token,grant.member_token):raise ValueError('practice_membership_changed')
    require_open(db,guild,current.skill)
    if current!=grant.before:raise ValueError('practice_revision_conflict')
    after=plan(current,level,prestige,rules,mode=1)
    child='practice:'+str(guild)+':'+reservation
    if db.execute('SELECT 1 FROM inventory_settlements WHERE role_id=? AND settlement_id=?',(role,child)).fetchone():
        raise ValueError('practice_orphan_asset_receipt')
    item=db.execute('''SELECT id FROM inventory_items WHERE role_id=? AND template_id=? AND equipment_slot IS NULL
        AND quantity>0 ORDER BY binding DESC,slot,id LIMIT 1''',(role,rules.pill_item)).fetchone()
    if not item:raise ValueError('practice_pill_unavailable')
    inventory.apply_settlement(db,AssetChange(child,debits=((item[0],1),)))
    db.execute('UPDATE role_practice_skills SET level=?,experience=?,revision=? WHERE role_id=? AND skill=?',
        (after.level,after.experience,after.revision,role,current.skill))
    db.execute('INSERT INTO role_practice_receipts VALUES(?,?,?,?,?)',(role,guild,reservation,grant.fingerprint,current.skill))
    db.execute('INSERT INTO role_practice_pill_consumption VALUES(?,?,?,?,?)',(role,guild,reservation,item[0],rules.pill_recipe))
    messages=precommit_messages(precommit,db,inventory,replayed=False)
    return PillPracticeReceipt(guild,reservation,after,item[0],inventory.immutable_snapshot_transaction(db,epoch=epoch),messages)

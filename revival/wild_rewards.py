"""Durable wild reward admission and atomic role-transaction settlement.

Only trusted role-owner commands call these interfaces. No client reward entry,
connection creation, commit, packet send or runtime DDL occurs here.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import struct
from types import MappingProxyType
from inventory import AssetChange,pet_record,REFRESH_PET,REFRESH_PET_EXP
from progression import credit_experience, read_experience
from currency import CurrencyChange, apply_currency
from battle_loadout import OwnedBattlePet

ROOT = Path(__file__).parent


@dataclass(frozen=True)
class WildRewardRules:
    revision: str
    costs: object
    numerator: int
    denominator: int
    minimum: int
    level_gap: int
    silver_per_level: int
    currency: str
    drops: tuple
    content: object = None


def load_wild_reward_rules(root=ROOT, *, version='v2'):
    """Startup-only configuration read. Amounts are local design, not originals."""
    root = Path(root)
    if version not in ('v1','v2'): raise ValueError('Unknown reward version')
    policy = json.loads((root/('design/wild-rewards-'+version+'.json')).read_text(encoding='utf-8'))
    exp = policy['experience']
    if (policy['revision'] != 'wild-rewards-'+version or exp['reference'] != 'scene_min_level_nextexp'
            or policy['currency'] != 'bound_silver' or policy['drop_draw_range'] != 10000
            or exp['denominator'] < 1 or min(exp['numerator'],exp['minimum'],
                policy['overlevel_no_reward_above_scene'],policy['silver_per_scene_level']) < 0):
        raise ValueError('Unsupported wild reward policy')
    items = {int(r['attributes']['id']) for r in json.loads(
        (root/'catalogs/knight.gsp.item.citemattr.json').read_text(encoding='utf-8'))}
    drops = tuple((r['item_id'],r['quantity'],r['binding'],r['weight']) for r in policy.get('drops',()))
    if (any(i not in items or q < 1 or b not in (0,1) or w < 1 for i,q,b,w in drops)
            or (version == 'v1' and sum(r[3] for r in drops) + policy['empty_weight'] != 10000)):
        raise ValueError('Invalid wild drop table')
    content = None
    if version == 'v2':
        pools = json.loads((root/'catalogs/wild-reward-pools.json').read_text(encoding='utf-8'))
        if (pools['revision'] != 'wild-reward-pools-v2' or policy['binding'] != 1
                or policy['equipment']['selection'] != 'highest_template_level_at_or_below_scene_then_uniform'
                or policy['equipment']['quality'] != 'existing_clean_ordinary_baseline'
                or policy['equipment']['maximum_level'] != 80
                or type(policy['cash_per_scene_level']) is not int or policy['cash_per_scene_level'] < 0
                or policy['porcelain']['maximum_absolute_level_gap'] != 5
                or sum(r['weight'] for r in policy['porcelain']['items']) != 10000
                or any(not 0 <= policy[g]['chance'] <= 10000 for g in ('medicine','porcelain','equipment'))
                or policy['pet'] != dict(experience_multiplier=2,maximum_level_above_entry_role=5,
                    ordinary_cap=150,recipient='original_owned_battle_pet_alive_at_terminal',
                    resource_order='write_terminal_pet_resources_before_experience_in_same_transaction')):
            raise ValueError('Unsupported expanded reward policy')
        allowed = {r['item_id'] for r in pools['medicine']}
        if any(not b['items'] or not set(b['items']) <= allowed for b in policy['medicine']['bands']):
            raise ValueError('Invalid medicine bands')
        porcelain = {r['item_id'] for r in pools['porcelain']}
        if any(r['item_id'] not in porcelain or r['weight'] < 1 for r in policy['porcelain']['items']):
            raise ValueError('Invalid porcelain selection')
        from equipment_detail import DetailRules
        supported = DetailRules.load().templates
        if any(not 1 <= int(level) <= 80 or not rows or any(r['item_id'] not in supported for r in rows)
               for level,rows in pools['equipment'].items()):
            raise ValueError('Unsupported equipment candidate')
        # Freeze nested JSON; runtime decisions never mutate startup policy.
        def freeze(value):
            if isinstance(value,dict): return MappingProxyType({k:freeze(v) for k,v in value.items()})
            if isinstance(value,list): return tuple(map(freeze,value))
            return value
        digest = hashlib.sha256(json.dumps([policy,pools],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        content = freeze(dict(policy=policy,pools=pools,digest=digest))
    costs = {int(r['attributes']['id']):int(r['attributes']['nextexp']) for r in json.loads(
        (root/'catalogs/knight.gsp.role.cresmoneyconfig.json').read_text(encoding='utf-8'))}
    return WildRewardRules(policy['revision'],MappingProxyType(costs),exp['numerator'],
        exp['denominator'],exp['minimum'],policy['overlevel_no_reward_above_scene'],
        policy['silver_per_scene_level'],policy['currency'],drops,content)


def _roll(ticket, battle_id, group, bound=10000):
    digest = hashlib.sha256(('wild-drop-v2:'+ticket.encounter_id+':'+battle_id+':'+group).encode()).digest()
    return int.from_bytes(digest[:8],'big') % bound


def _expanded_drops(ticket, participant, battle_id, rules):
    policy, pools = rules.content['policy'], rules.content['pools']
    grants, rolls = [], {}
    for group in ('medicine','porcelain','equipment'):
        roll = rolls[group] = _roll(ticket,battle_id,group)
        if roll >= policy[group]['chance']: continue
        if group == 'medicine':
            band = max((b for b in policy[group]['bands'] if b['minimum_scene_level'] <= ticket.level),
                       key=lambda b:b['minimum_scene_level'])
            item = band['items'][_roll(ticket,battle_id,group+':choice',len(band['items']))]
        elif group == 'porcelain':
            if abs(participant.level-ticket.level) > policy[group]['maximum_absolute_level_gap']: continue
            choice = _roll(ticket,battle_id,group+':choice')
            for row in policy[group]['items']:
                if choice < row['weight']:
                    item = row['item_id']; break
                choice -= row['weight']
        else:
            level = max(int(v) for v in pools['equipment'] if int(v) <= ticket.level)
            choices = pools['equipment'][str(level)]
            item = choices[_roll(ticket,battle_id,group+':choice',len(choices))]['item_id']
        grants.append((item,1,policy['binding']))
    return tuple(grants),rolls


def _capture_pet(db, participant, inventory):
    pet = participant.pet
    if pet is None: return None
    if not isinstance(pet,OwnedBattlePet) or pet.role_id != participant.role_id or not pet.selected:
        raise ValueError('Wild rewards require original owned battle pet')
    actual = inventory.selected_fighting_pet(db)
    if (actual is None or actual.id != pet.key or actual.progress is None
            or actual.template_id != pet.template_id or actual.progress.state.version != pet.growth_version
            or actual.progress.state.level != pet.level or actual.progress.state.hp != pet.stats.hp
            or actual.progress.state.mp != pet.stats.mp or actual.progress.state.hp <= 0
            or inventory.growth_rules.revision != pet.growth_revision
            or participant.level < int(inventory.pet_types[pet.template_id]['uselevel'])):
        raise ValueError('Battle pet differs from owned admission state')
    return dict(battle=asdict(pet),state=asdict(actual.progress.state),profile=asdict(actual.progress.profile),
                award_cap=min(150,participant.level+5))


def prepare_wild_reward_storage(db):
    """Startup migration before listening; no role or reward initialization."""
    db.execute('''CREATE TABLE IF NOT EXISTS wild_reward_admissions (
        role_id INTEGER NOT NULL REFERENCES roles(id), battle_id TEXT NOT NULL,
        plan TEXT NOT NULL, result_fingerprint TEXT, receipt TEXT,
        PRIMARY KEY(role_id,battle_id))''')


def _scope(db, account_id, role_id, epoch, inventory):
    if (not db.in_transaction or inventory.account_id != account_id or inventory.role_id != role_id
            or not db.execute('SELECT 1 FROM roles WHERE id=? AND account_id=?',(role_id,account_id)).fetchone()
            or not db.execute('SELECT 1 FROM role_leases WHERE role_id=? AND epoch=? AND active=1',
                              (role_id,epoch)).fetchone()):
        raise ValueError('Wild reward requires active owned role transaction and lease')


def register_wild_reward(db, account_id, participant, ticket, battle_id, inventory, rules):
    """Persist a fixed reward plan before battle opening. Caller commits once.

    This is a battle admission contract, not a reward grant. Duplicate admission
    must have the identical participant/encounter/role-level/config snapshot.
    """
    role_id, epoch = participant.role_id, participant.login_epoch
    _scope(db,account_id,role_id,epoch,inventory)
    if (ticket.location.role_id != role_id or ticket.location.login_epoch != epoch
            or not isinstance(battle_id,str) or not 1 <= len(battle_id) <= 128
            or ticket.level not in rules.costs or min(participant.attribute_version,participant.level) < 1):
        raise ValueError('Wild admission identity mismatch')
    admission_fingerprint = None
    if rules.content is not None:
        admission_fingerprint = hashlib.sha256(json.dumps([asdict(participant),asdict(ticket),
            rules.content['digest']],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        previous = db.execute('SELECT plan FROM wild_reward_admissions WHERE role_id=? AND battle_id=?',
                              (role_id,battle_id)).fetchone()
        if previous:
            if json.loads(previous[0]).get('admission_fingerprint') != admission_fingerprint:
                raise ValueError('Conflicting wild battle admission')
            return
    eligible = participant.level <= ticket.level + rules.level_gap
    exp = max(rules.minimum,rules.costs[ticket.level]*rules.numerator//rules.denominator) if eligible else 0
    silver = ticket.level*rules.silver_per_level if eligible else 0
    roll = int.from_bytes(hashlib.sha256(('wild-drop-v1:'+ticket.encounter_id+':'+battle_id).encode()).digest()[:8],'big') % 10000
    grants = ()
    remaining = roll
    if eligible:
        for item,quantity,binding,weight in rules.drops:
            if remaining < weight:
                grants = ((item,quantity,binding),); break
            remaining -= weight
    plan = dict(role_id=role_id, epoch=epoch, battle_id=battle_id, encounter_id=ticket.encounter_id,
        snapshot_version=participant.attribute_version, scene_level=ticket.level, role_level=participant.level,
        monster=ticket.monster.template_id, encounter_revision=ticket.revision, reward_revision=rules.revision,
        experience=exp,silver=silver,currency=rules.currency,grants=grants,roll=roll)
    if rules.content is not None:
        plan['grants'],plan['rolls'] = _expanded_drops(ticket,participant,battle_id,rules) if eligible else ((),{})
        plan['pet'] = _capture_pet(db,participant,inventory)
        plan['pet_experience'] = exp*rules.content['policy']['pet']['experience_multiplier']
        plan['cash'] = ticket.level*rules.content['policy']['cash_per_scene_level'] if eligible else 0
        # Preserve policy identity, not merely a label, for conflict detection.
        plan['content_digest'] = rules.content['digest']
        plan['admission_fingerprint'] = admission_fingerprint
    encoded = json.dumps(plan,sort_keys=True,separators=(',',':'))
    old = db.execute('SELECT plan FROM wild_reward_admissions WHERE role_id=? AND battle_id=?',
                     (role_id,battle_id)).fetchone()
    if old:
        if old[0] != encoded: raise ValueError('Conflicting wild battle admission')
        return
    db.execute('INSERT INTO wild_reward_admissions(role_id,battle_id,plan) VALUES(?,?,?)',
               (role_id,battle_id,encoded))


def _settle_pet(db, finished, plan, inventory, victory):
    decision = plan.get('pet')
    resources = tuple(r for r in finished.combat_resources if r.kind in ('pet','pet_fixture'))
    if decision is None:
        if resources: raise ValueError('Terminal pet not present in admission')
        return dict(status='no_pet',recipient=None,awarded=0)
    pet = decision['battle']; key = pet['key']
    if len(resources) != 1: raise ValueError('Original pet terminal snapshot required')
    resource = resources[0]
    if (resource.kind != 'pet' or resource.entity_id != key or resource.position != pet['position']
            or resource.source_version != pet['growth_version']
            or resource.inventory_revision != pet['inventory_revision']
            or resource.growth_revision != pet['growth_revision']
            or resource.max_hp != pet['stats']['max_hp'] or resource.max_mp != pet['max_mp']):
        raise ValueError('Terminal pet differs from original battle snapshot')
    actual = inventory.read_pet_state(db,key)
    if (actual is None or actual.progress is None
            or json.loads(json.dumps(asdict(actual.progress.state))) != decision['state']
            or json.loads(json.dumps(asdict(actual.progress.profile))) != decision['profile']):
        raise ValueError('Original battle pet changed before resource settlement')
    after = inventory.change_pet_growth(db,key,finished.settlement_id+':pet_resources',
        pet['growth_version'],'resources',(resource.hp,resource.mp))
    eligible = (victory and not resource.escaped and resource.hp > 0
                and after.state.level <= decision['award_cap'] and plan['pet_experience'] > 0)
    if eligible:
        inventory.change_pet_growth(db,key,finished.settlement_id+':pet_exp',after.state.version,
            'experience_capped',(plan['pet_experience'],decision['award_cap']))
    # Refuse an unencodable pet state while every reward can still roll back.
    current = inventory.read_pet_state(db,key)
    pet_record(current.__dict__)
    struct.pack('>iQ',key,current.progress.state.experience)
    return dict(status='awarded' if eligible else 'ineligible',recipient=key,
                awarded=plan['pet_experience'] if eligible else 0)


def settle_wild_reward(db, account_id, role_id, epoch, finished, inventory,
                       currency_rules, growth_rules=None, attribute_rules=None,*,resource_context=None,recovery_from_epoch=None):
    """Atomic XP, bound silver, items and receipt; caller rolls back any error.

    Supply the authoritative battle-owner terminal event. Resource/death/pet
    settlement must join the host's same outer transaction before committing.
    Returning this dictionary is not proof of commit and must not trigger sends.
    """
    _scope(db,account_id,role_id,epoch,inventory)
    if finished.login_epoch!=epoch:
        # Only a durable original terminal outbox authorizes a new fenced owner
        # to receive the old outcome. Original admission/result stay unchanged.
        digest=hashlib.sha256(json.dumps(asdict(finished),sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if (recovery_from_epoch!=finished.login_epoch or not db.execute(
            'SELECT 1 FROM wild_runtime_battles WHERE role_id=? AND battle_id=? AND accepted_epoch=? '
            'AND terminal_hash=?',(role_id,finished.battle_id,str(finished.login_epoch),digest)).fetchone()):
            raise ValueError('Old wild terminal requires durable recovery authorization')
    if (finished.role_id != role_id
            or finished.scope != 'wild_encounter_v1' or finished.settlement_id != 'wild:'+finished.battle_id):
        raise ValueError('Invalid wild battle result scope')
    row = db.execute('SELECT plan,result_fingerprint,receipt FROM wild_reward_admissions '
        'WHERE role_id=? AND battle_id=?',(role_id,finished.battle_id)).fetchone()
    if row is None: raise ValueError('Wild battle has no durable admission')
    plan = json.loads(row[0])
    if (plan['epoch'] != finished.login_epoch or plan['snapshot_version'] != finished.snapshot_version
            or plan['encounter_revision'] != finished.revision):
        raise ValueError('Wild battle result changed admission snapshot')
    fingerprint = hashlib.sha256(json.dumps(asdict(finished),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if row[2] is not None:
        if row[1] != fingerprint: raise ValueError('Wild terminal result conflict')
        return {**json.loads(row[2]),'replayed':True}
    victory = finished.outcome == 'victory' and finished.won and finished.winner_side == 0
    if finished.won != victory or finished.outcome not in ('victory','defeat','draw','escape'):
        raise ValueError('Inconsistent wild terminal outcome')
    exp, silver, grants = (plan['experience'],plan['silver'],tuple(tuple(g) for g in plan['grants'])) if victory else (0,0,())
    pet_receipt = (_settle_pet(db,finished,plan,inventory,victory)
                   if plan['reward_revision'] == 'wild-rewards-v2' else None)
    # Pet resources/XP can advance the shared inventory revision. Compose role
    # growth from the NEW same-transaction assets, not the admission snapshot.
    if resource_context is not None:
        from dataclasses import replace
        from role_equipment_storage import synchronize_inventory_resource_source
        current_inventory=inventory.immutable_snapshot_transaction(db,epoch=epoch)
        synchronize_inventory_resource_source(db,account_id,role_id,epoch,current_inventory,
            finished.settlement_id+':pet_source',resource_rules=resource_context.resource_rules,
            equipment_rules=resource_context.equipment_rules,replayed=False)
        resource_context=replace(resource_context,inventory_snapshot=current_inventory)
    cash = plan.get('cash',0) if victory else 0
    if silver or cash:
        deltas = tuple((name,amount) for name,amount in ((plan['currency'],silver),('cash',cash)) if amount)
        apply_currency(db,account_id,role_id,epoch,CurrencyChange(finished.settlement_id+':money',
            'wild_reward',finished.battle_id,deltas),currency_rules)
    balance = (credit_experience(db,account_id,role_id,exp,growth_rules,attribute_rules,epoch,resource_context=resource_context)
               if exp else read_experience(db,account_id,role_id))
    if grants: inventory.apply_settlement(db,AssetChange(finished.settlement_id+':items',grants))
    receipt = dict(settlement_id=finished.settlement_id,role_id=role_id,outcome=finished.outcome,
        experience_awarded=exp,silver_awarded=silver,items_awarded=grants,
        reward_revision=plan['reward_revision'],replayed=False,
        pet_experience_status='pending' if victory and any(r.kind=='pet' for r in finished.combat_resources) else 'not_applicable')
    if pet_receipt is not None:
        receipt['cash_awarded'] = cash
        receipt['pet_experience_status'] = pet_receipt['status']
        receipt['pet_experience'] = pet_receipt
    db.execute('UPDATE wild_reward_admissions SET result_fingerprint=?,receipt=? WHERE role_id=? AND battle_id=?',
        (fingerprint,json.dumps(receipt),role_id,finished.battle_id))
    # Historical receipt intentionally excludes balance snapshots. The host reads
    # current XP/wallet/bag after settlement for refresh and cache replacement.
    return json.loads(json.dumps(receipt))


def wild_pet_refresh(db,account_id,role_id,epoch,receipt,inventory):
    """Post-commit read of the original recipient's current absolute state.

    Caller uses a fresh owned read transaction and sends only after the reward
    commit succeeded. A historical receipt never replaces current pet balances.
    """
    _scope(db,account_id,role_id,epoch,inventory)
    if receipt['role_id'] != role_id: raise ValueError('Wild reward refresh owner mismatch')
    decision = receipt.get('pet_experience')
    if not decision or decision['recipient'] is None: return ()
    pet = inventory.read_pet_state(db,decision['recipient'])
    if pet is None or pet.progress is None:
        raise ValueError('Original battle pet unavailable for refresh')
    return ((REFRESH_PET,pet_record(pet.__dict__)),
            (REFRESH_PET_EXP,struct.pack('>iQ',pet.id,pet.progress.state.experience)))

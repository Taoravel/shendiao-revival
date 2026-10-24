"""Frozen task recipient decisions and transaction-joining pet XP settlement.

Only capture_fresh_recipient may select a pet, before any character reward.
Settlement and retries use that immutable decision, including ineligible pets.
"""
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import struct
from inspect_client import OUT
from inventory import REFRESH_PET, REFRESH_PET_EXP, pet_record


@dataclass(frozen=True)
class TaskPetExperienceRules:
    revision: str
    above_role: int
    ordinary_cap: int
    maximum_exp: int


def load_task_pet_experience_rules():
    """Startup only. A changed policy needs implementation/migration review."""
    policy = json.loads((OUT/'design/task-pet-experience-v1.json').read_text(encoding='utf-8'))
    if (policy['revision'] != '2026-10-23.task-pet-exp.1'
            or policy['source_field'] != 'PetExpReward'
            or policy['eligibility']['maximum_level_above_role'] != 5
            or policy['leveling']['ordinary_cap'] != 150
            or policy['leveling']['maximum_stored_experience'] != 2147483647):
        raise ValueError('Task pet XP policy requires implementation review')
    return TaskPetExperienceRules(policy['revision'], 5, 150, 2147483647)


def prepare_task_pet_experience_storage(db):
    db.execute('''CREATE TABLE IF NOT EXISTS task_pet_reward_decisions (
        role_id INTEGER NOT NULL REFERENCES roles(id), task_id INTEGER NOT NULL,
        payload TEXT NOT NULL, PRIMARY KEY(role_id,task_id))''')


@dataclass(frozen=True)
class TaskPetExperienceResult:
    status: str
    reason: str
    amount: int
    recipient_id: int | None = None
    current_pet: object = None


def _scope(db, account_id, role_id, epoch, inventory):
    if (not db.in_transaction or inventory.account_id != account_id or inventory.role_id != role_id
            or not db.execute('SELECT 1 FROM roles WHERE id=? AND account_id=?', (role_id,account_id)).fetchone()
            or not db.execute('SELECT 1 FROM role_leases WHERE role_id=? AND epoch=? AND active=1',
                              (role_id,epoch)).fetchone()):
        raise ValueError('Task pet XP requires current owned role transaction')


def _read_decision(db, role_id, task_id):
    row = db.execute('SELECT payload FROM task_pet_reward_decisions WHERE role_id=? AND task_id=?',
                     (role_id,task_id)).fetchone()
    return json.loads(row[0]) if row else None


def capture_fresh_recipient(db, actor, task_id, resources, inventory, rules):
    """Call only at active->completed; the caller rolls back on any later error.

    Missing rules still freeze the selected key for explicit reconciliation.
    Enabling a policy later cannot retrospectively qualify a different pet.
    """
    _scope(db,actor.account_id,actor.role_id,actor.login_epoch,inventory)
    row = db.execute('SELECT state FROM task_journal WHERE role_id=? AND task_id=?',
                     (actor.role_id,task_id)).fetchone()
    if row is None or row[0] != 'active':
        raise ValueError('Only fresh active task may capture a pet recipient')
    amount = resources.definitions[task_id]['display_rewards']['PetExpReward']
    if type(amount) is not int or amount < 0:
        raise ValueError('Invalid original task pet XP')
    role_level = db.execute('SELECT level FROM roles WHERE id=?',(actor.role_id,)).fetchone()[0]
    decision = dict(amount=amount, policy=asdict(rules) if rules else None,
        role_level=role_level, recipient_id=None, status='zero', reason='original_zero')
    if amount:
        pet = inventory.selected_fighting_pet(db)
        decision.update(status='not_awarded',reason='no_selected_pet')
        if pet is not None:
            decision.update(recipient_id=pet.id,template_id=pet.template_id)
            uselevel = inventory.pet_types.get(pet.template_id,{}).get('uselevel')
            decision['uselevel'] = int(uselevel) if uselevel is not None else None
            if pet.progress is not None:
                decision.update(growth_version=pet.progress.state.version,
                    growth_policy=inventory.growth_rules.revision,
                    growth_state=asdict(pet.progress.state), profile=asdict(pet.progress.profile))
            if rules is None:
                decision.update(status='pending',reason='task_pet_policy_not_initialized')
            elif pet.progress is None:
                decision.update(status='pending',reason='explicit_pet_baseline_reconciliation')
            elif uselevel is None:
                decision.update(status='pending',reason='original_uselevel_unavailable')
            else:
                state = pet.progress.state
                cap = min(rules.ordinary_cap, role_level+rules.above_role)
                decision['award_cap'] = cap
                if not inventory.growth_rules.initial_level <= state.level <= rules.ordinary_cap:
                    decision['reason'] = 'not_ordinary_pet_growth'
                elif state.hp <= 0:
                    decision['reason'] = 'pet_dead'
                elif role_level < int(uselevel):
                    decision['reason'] = 'role_below_original_uselevel'
                elif state.level > cap:
                    decision['reason'] = 'pet_above_captured_level_cap'
                else:
                    decision.update(status='eligible',reason='captured_ordinary_fighting_pet')
        elif rules is None:
            decision.update(status='pending',reason='task_pet_policy_not_initialized')
    old = _read_decision(db,actor.role_id,task_id)
    if old is not None:
        raise ValueError('Fresh task already has a pet decision; reconciliation required')
    db.execute('INSERT INTO task_pet_reward_decisions VALUES(?,?,?)',
               (actor.role_id,task_id,json.dumps(decision,sort_keys=True)))


def settle_pet_experience(db, account_id, role_id, epoch, task_id, amount, fingerprint, inventory, rules):
    """Join the caller transaction; unresolved decisions never select a new pet."""
    _scope(db,account_id,role_id,epoch,inventory)
    decision = _read_decision(db,role_id,task_id)
    if decision is None:
        if amount:
            return TaskPetExperienceResult('pending','explicit_recipient_reconciliation',amount)
        # Original zero needs no historical recipient or growth mutation.
        decision = dict(amount=0,policy=None,recipient_id=None,status='zero',reason='original_zero')
        db.execute('INSERT INTO task_pet_reward_decisions VALUES(?,?,?)',
                   (role_id,task_id,json.dumps(decision,sort_keys=True)))
    if decision['amount'] != amount:
        raise ValueError('Task pet XP amount migration required')
    if amount and rules is not None and decision['policy'] != asdict(rules):
        raise ValueError('Task pet XP policy migration required')
    pet_id = decision['recipient_id']
    if decision['status'] == 'pending':
        return TaskPetExperienceResult('pending',decision['reason'],amount,pet_id)
    digest = hashlib.sha256(json.dumps(decision,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    old = db.execute("SELECT fingerprint,receipt FROM task_reward_channels WHERE role_id=? AND task_id=? AND channel='pet_experience'",
                     (role_id,task_id)).fetchone()
    if old:
        receipt = json.loads(old[1])
        if old[0] != fingerprint or receipt['decision'] != digest:
            raise ValueError('Task pet XP receipt migration required')
    else:
        status = decision['status']
        if status == 'eligible':
            if rules is None:
                return TaskPetExperienceResult('pending','task_pet_policy_not_initialized',amount,pet_id)
            pet = inventory.read_pet_state(db,pet_id)
            if pet is None:
                return TaskPetExperienceResult('pending','original_recipient_unavailable_audit',amount,pet_id)
            if (pet.progress is None or inventory.growth_rules.revision != decision['growth_policy']
                    or json.loads(json.dumps(asdict(pet.progress.state))) != decision['growth_state']
                    or json.loads(json.dumps(asdict(pet.progress.profile))) != decision['profile']):
                return TaskPetExperienceResult('pending','original_pet_growth_changed_audit',amount,pet_id)
            if pet.progress.state.experience+amount > rules.maximum_exp:
                raise ValueError('Pet experience overflow')
            inventory.change_pet_growth(db,pet_id,f'task:{role_id}:{task_id}:PetExpReward:{pet_id}',
                decision['growth_version'],'experience_capped',(amount,decision['award_cap']))
            status = 'awarded'
        receipt = dict(decision=digest,status=status,amount=amount,recipient_id=pet_id,reason=decision['reason'])
        db.execute('INSERT INTO task_reward_channels VALUES(?,?,?,?,?)',
                   (role_id,task_id,'pet_experience',fingerprint,json.dumps(receipt)))
    if receipt['status'] == 'awarded':
        pet = inventory.read_pet_state(db,pet_id)
        if pet is None or pet.progress is None:
            return TaskPetExperienceResult('pending','original_recipient_unavailable_audit',amount,pet_id)
        # Refuse unencodable task output while the whole award can still roll back.
        pet_record(pet.__dict__)
        struct.pack('>iQ',pet.id,pet.progress.state.experience)
        # A pre-commit snapshot must not escape as a ready-to-send refresh.
        # refresh_pet_experience re-reads it after the caller has committed.
        return TaskPetExperienceResult('awarded',receipt['reason'],amount,pet_id)
    return TaskPetExperienceResult(receipt['status'],receipt['reason'],amount,pet_id)


def refresh_pet_experience(db, account_id, role_id, epoch, result, inventory):
    """Post-commit role-owner read. Keep the original recipient even after switching."""
    _scope(db,account_id,role_id,epoch,inventory)
    if result is None or result.status != 'awarded':
        return result
    pet = inventory.read_pet_state(db,result.recipient_id)
    if pet is None or pet.progress is None:
        return replace(result,status='pending',reason='original_recipient_unavailable_audit',current_pet=None)
    return replace(result,current_pet=pet)


def pet_experience_messages(result):
    """Encode a current original-recipient snapshot; caller sends after commit."""
    if result is None or result.status != 'awarded' or result.current_pet is None:
        return ()
    pet = result.current_pet
    return ((REFRESH_PET,pet_record(pet.__dict__)),
            (REFRESH_PET_EXP,struct.pack('>iQ',pet.id,pet.progress.state.experience)))

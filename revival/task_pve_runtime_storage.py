"""Role-worker Task PVE loadout/admission/checkpoint and terminal outbox.

Task admission/settlement and actual resource consumption share the caller role
transaction. No wild reward, training snapshot, transport or global lock lives
here. Producer terminal events retain their original epoch across recovery.
"""
from contextlib import closing
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from battle import Fighter, Skill
from battle_owner import Participant
from battle_loadout import CombatResources, OwnedBattlePet, selected_pet
from role_attribute_storage import read_attribute_snapshot
from role_resource_storage import read_role_resources, ResourceNotInitialized
from currency import read_wallet
from training_battle import BattleFinished


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def _hash(value):
    return hashlib.sha256(_json(value).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class TaskCombatSnapshot:
    participant: Participant
    basis: str
    vitals: object
    resources: object
    skill_ledger: str | None


@dataclass(frozen=True)
class TaskPveCommit:
    role: object
    packets: tuple
    replayed: bool
    settlement: object


def _scope(db, account, role, epoch):
    if not db.in_transaction or not db.execute(
            'SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
            'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1',
            (role, account, epoch)).fetchone():
        raise ValueError('Task combat requires the current role-owned transaction')


def prepare(db):
    """Startup schema only. Existing roles receive no admission or baseline."""
    from task_battle import prepare_task_battle_storage
    prepare_task_battle_storage(db)
    db.execute('''CREATE TABLE IF NOT EXISTS task_pve_runtime_battles (
        role_id INTEGER NOT NULL REFERENCES roles(id),battle_id TEXT NOT NULL,
        accepted_epoch TEXT NOT NULL,participant TEXT NOT NULL,basis TEXT NOT NULL,
        engine_revision TEXT NOT NULL,fighters TEXT NOT NULL,
        round_number INTEGER NOT NULL,state_version INTEGER NOT NULL,
        snapshot_phase TEXT NOT NULL,terminal TEXT,terminal_hash TEXT,receipt TEXT,
        status TEXT NOT NULL CHECK(status IN ('active','terminal','settled')),
        producer_kind TEXT,producer_epoch TEXT,
        PRIMARY KEY(role_id,battle_id))''')
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS task_pve_one_pending ON "
               "task_pve_runtime_battles(role_id) WHERE status!='settled'")


def read_combat_snapshot_transaction(db, accounts, account, role, epoch, generation, rules):
    """Public actual loadout read. Unknown legacy data never becomes defaults.

    No skill capability is implemented by this recipe. The complete learned
    ledger is preserved as an explicit known snapshot or UNKNOWN, and no empty
    OtherSkills message is produced. Inventory/profile provenance is included
    even when it does not change the current attack/HP numbers.
    """
    import runtime_storage as storage
    _scope(db, account, role, epoch)
    if type(generation) is not int or generation < 1:
        raise ValueError('Actual connection generation required')
    inventory = storage._inventory(accounts, account, role, epoch)
    assets = inventory.immutable_snapshot_transaction(db, epoch=epoch)
    profile = storage._role_profile_transaction(db, accounts, account, role, epoch,
                                               inventory, assets)
    if profile.attributes is None or profile.attributes.vitals.hp <= 0:
        raise ValueError('Task combat requires known living current role attributes')
    attributes, vitals = profile.attributes.attributes, profile.attributes.vitals
    try:
        resources = read_role_resources(db, account, role, epoch, accounts.resource_rules)
    except ResourceNotInitialized:
        resources = None
        if read_attribute_snapshot(db, account, role, epoch).vitals != vitals:
            raise ValueError('Legacy equipped resource caps need explicit reconciliation')
    row = db.execute('SELECT name,shape FROM roles WHERE id=? AND account_id=?',
                     (role, account)).fetchone()
    pet = selected_pet(assets, role_id=role, role_level=profile.role.level,
        templates=rules.pet_templates, growth_revision=inventory.growth_rules.revision)
    participant = Participant(role, epoch, generation, max(1, vitals.version),
        row[0], row[1], profile.role.level,
        Fighter(1, 0, vitals.hp, vitals.max_hp, vitals.mp, attributes.physical_attack,
                attributes.physical_defense, attributes.speed, max_mp=vitals.max_mp), pet=pet)
    # Reward encoding must not discover an unknown wallet only after victory.
    read_wallet(db, account, role, epoch, accounts.currency_rules)
    ledger = None
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='role_other_skills'").fetchone():
        skill_rules = getattr(accounts, 'other_skill_rules', None)
        if skill_rules is None:
            raise ValueError('Existing skill ledger requires prepared original namespace rules')
        from role_skills import read_other_skills
        current = read_other_skills(db, account, role, epoch, skill_rules)
        ledger = _json(asdict(current)) if current is not None else None
    from task_persistence import load_task_state
    from task_newbie_chapter import read_newbie_chapter
    _, tasks = load_task_state(db,account,role,epoch)
    task_basis=dict(revision=tasks.revision,**{name:sorted(getattr(tasks,name))
                    for name in ('offered','active','completed','tracked')})
    chapter=read_newbie_chapter(db,account,role,epoch,accounts.newbie_rules)
    chapter_basis=(dict(origin=asdict(chapter.origin),phase=chapter.phase,revision=chapter.revision)
                   if chapter is not None else None)
    directory_basis=None
    if chapter is not None and chapter.phase=='completed':
        from world_transfer_storage import load_map_instance_transaction
        from world_story_instances import StoryInstanceIntent,load_story_instance_transaction
        checkpoint=load_map_instance_transaction(db,account,role,epoch)
        if checkpoint is not None and checkpoint.address.map_id==1501:
            origin=chapter.origin
            source=accounts.story_instance_rules.source_tasks[(origin.route.character_id,origin.route.school_id)]
            intent=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,
                                        origin.route_fingerprint,source)
            directory=load_story_instance_transaction(db,account,role,epoch,intent,
                accounts.story_instance_rules,expected_address=checkpoint.address)
            directory_basis=asdict(directory)
    # Epoch is deliberately absent from this stable asset basis: a trusted new
    # role lease can recover the original durable terminal without rebinding its
    # original participant/event. The caller separately fences each DB lease.
    basis = _json(dict(identity=dict(role_id=role,name=row[0],shape=row[1]),
        level=profile.role.level, experience=profile.role.experience,
        growth=asdict(profile.growth) if profile.growth is not None else None,
        attributes=asdict(profile.attributes), inventory=asdict(assets),
        resources=asdict(resources) if resources is not None else None,
        skill_ledger=ledger,tasks=task_basis,chapter=chapter_basis,directory=directory_basis))
    return TaskCombatSnapshot(participant, basis, vitals, resources, ledger)


def participant(accounts, account, role, epoch, generation):
    with closing(accounts.leased(account, role, epoch).connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM task_pve_runtime_battles WHERE role_id=? AND status!='settled'",
                      (role,)).fetchone():
            raise ValueError('Prior task battle awaits durable settlement')
        return read_combat_snapshot_transaction(db, accounts, account, role, epoch, generation,
                                               accounts.task_pve_rules).participant


def dialogue(accounts,account,role,epoch,proof,current,generation,map_generation,now_ms,deadline_ms,movement_state):
    from task_persistence import load_task_state
    from task_first_battle import open_first_battle_transaction
    with closing(accounts.leased(account,role,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        _,state=load_task_state(db,account,role,epoch)
        candidates=tuple(q for q in state.active if q in accounts.task_battle_resources.enabled_task_ids)
        if not candidates:return None
        if len(candidates)!=1:raise ValueError('Conflicting active first-dream battle tasks')
        return open_first_battle_transaction(db,account,role,epoch,accounts.task_resources,
            accounts.first_battle_rules,candidates[0],proof,current,generation=generation,
            map_generation=map_generation,now_ms=now_ms,deadline_ms=deadline_ms,movement_state=movement_state)


def skill_dialogue(accounts,account,role,epoch,proof,current,generation,map_generation,now_ms,movement_state):
    from task_persistence import load_task_state
    from task_first_skill import open_first_skill_transaction
    with closing(accounts.leased(account,role,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        _,state=load_task_state(db,account,role,epoch)
        candidates=tuple(q for q in state.active if q in accounts.first_skill_rules.definitions)
        if not candidates:return None
        if len(candidates)!=1:raise ValueError('Conflicting active first-skill teaching tasks')
        return open_first_skill_transaction(db,account,role,epoch,accounts.task_resources,
            accounts.first_skill_rules,candidates[0],proof,current,generation=generation,
            map_generation=map_generation,now_ms=now_ms,movement_state=movement_state,
            baseline_policy=accounts.local_prologue_skill_baseline_rules)


def skill_complete(accounts,account,role,epoch,ticket,command,proof,current,generation,map_generation,now_ms,movement_state):
    import runtime_storage as storage
    from task_first_skill import complete_first_skill_transaction
    with closing(accounts.leased(account,role,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        inventory=storage._inventory(accounts,account,role,epoch)
        result=complete_first_skill_transaction(db,account,role,epoch,accounts.task_resources,
            accounts.first_skill_rules,ticket,command,inventory,proof=proof,location=current,
            generation=generation,map_generation=map_generation,now_ms=now_ms,movement_state=movement_state,
            baseline_policy=accounts.local_prologue_skill_baseline_rules,**_task_rules(accounts))
        profile=storage._role_profile_transaction(db,accounts,account,role,epoch,inventory)
        messages=list(result.messages)
        if profile.refresh is not None:
            messages=[packet for packet in messages if packet[0]!=profile.refresh[0]]
            messages.append(profile.refresh)
        return TaskPveCommit(profile.role,tuple(messages),result.replayed,result)


def admit(accounts, account, actor, ticket, request, proof, location, battle_id,
          map_generation, now_ms, movement_state):
    from task_first_battle import admit_first_battle_transaction
    role, epoch = actor.role_id, actor.login_epoch
    with closing(accounts.leased(account, role, epoch).connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        actual = read_combat_snapshot_transaction(db, accounts, account, role, epoch,
            actor.connection_generation, accounts.task_pve_rules)
        if actual.participant != actor:
            raise ValueError('Task combat loadout changed before admission')
        admission = admit_first_battle_transaction(db, account, role, epoch,
            accounts.task_resources, accounts.first_battle_rules, ticket, request, proof,
            location, actor, battle_id, generation=actor.connection_generation,
            map_generation=map_generation, now_ms=now_ms, movement_state=movement_state)
        row = db.execute('SELECT basis FROM task_pve_runtime_battles WHERE role_id=? AND battle_id=?',
                         (role, battle_id)).fetchone()
        if row is not None:
            if row[0] != actual.basis:
                raise ValueError('Task combat admission retry changed the complete asset source')
            return admission
        fighters = tuple(sorted((actor.stats, accounts.task_pve_rules.enemy)
            + ((actor.pet.stats,) if actor.pet else ()), key=lambda fighter: fighter.id))
        db.execute('INSERT INTO task_pve_runtime_battles VALUES(?,?,?,?,?,?,?,?,?,?,NULL,NULL,NULL,?,NULL,NULL)',
            (role, battle_id, str(epoch), _json(asdict(actor)), actual.basis,
             accounts.task_pve_rules.revision, _json([asdict(f) for f in fighters]), 1, 1, 'commands', 'active'))
        return admission


def _fighter(record):
    data = dict(record)
    data['skills'] = tuple(Skill(**skill) for skill in data.get('skills', ()))
    return Fighter(**data)


def _participant(record):
    data = dict(record)
    data['stats'] = _fighter(data['stats'])
    data['authorized_skills'] = tuple(data['authorized_skills'])
    if data['pet'] is not None:
        pet = dict(data['pet'])
        pet['stats'] = _fighter(pet['stats'])
        data['pet'] = OwnedBattlePet(**pet)
    return Participant(**data)


def _finished(record):
    data = dict(record)
    data['item_rewards'] = tuple(data['item_rewards'])
    data['combat_resources'] = tuple(CombatResources(**entry) for entry in data['combat_resources'])
    return BattleFinished(**data)


def checkpoint(accounts, account, role, epoch, snapshot, finished=None):
    """Persist the actual combat copy before logical packets are delivered.

    A terminal is an immutable producer outbox event. Its later consumer receipt
    is committed atomically with resources and Task rewards, never with this
    initial producer write. No event is relabelled to match a replacement lease.
    """
    with closing(accounts.leased(account, role, epoch).connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        _scope(db, account, role, epoch)
        row = db.execute('SELECT accepted_epoch,participant,fighters,round_number,state_version,'
            'snapshot_phase,terminal_hash,status FROM task_pve_runtime_battles '
            'WHERE role_id=? AND battle_id=?', (role, snapshot.battle_id)).fetchone()
        if row is None or row[0] != str(epoch):
            raise ValueError('Task checkpoint does not belong to this admitted lease')
        actor = _participant(json.loads(row[1]))
        previous = tuple(_fighter(record) for record in json.loads(row[2]))
        if (snapshot.state_version < row[4] or snapshot.round_number < row[3]
                or snapshot.round_number > accounts.task_pve_rules.max_rounds
                or snapshot.phase not in ('commands', 'playback', 'ended')
                or tuple(f.id for f in previous) != tuple(f.id for f in snapshot.fighters)):
            raise ValueError('Task checkpoint version, phase or roster changed')
        for before, after in zip(previous, snapshot.fighters):
            if (not isinstance(after, Fighter) or replace(after, hp=before.hp, mp=before.mp) != before
                    or type(after.hp) is not int or type(after.mp) is not int
                    or not 0 <= after.hp <= before.hp or not 0 <= after.mp <= before.mp):
                raise ValueError('Task checkpoint rewrote stats, healed or increased MP')
        if snapshot.state_version == row[4] and (
                snapshot.fighters != previous or (snapshot.round_number, snapshot.phase) != (row[3], row[5])):
            raise ValueError('Task checkpoint reused a version for different state')
        digest = _hash(asdict(finished)) if finished is not None else None
        if row[6] is not None:
            if digest != row[6]:
                raise ValueError('Original task producer terminal is immutable')
            return
        if finished is not None:
            if (not isinstance(finished, BattleFinished) or snapshot.phase != 'ended'
                    or finished.battle_id != snapshot.battle_id or finished.role_id != role
                    or finished.login_epoch != actor.login_epoch
                    or finished.snapshot_version != actor.attribute_version
                    or finished.revision != accounts.task_pve_rules.revision
                    or finished.scope != 'task_quest_v1' or finished.task_event_eligible is not True
                    or finished.settlement_id != 'task-battle:' + snapshot.battle_id
                    or finished.currency_reward != 0 or finished.item_rewards != ()):
                raise ValueError('Only the admitted dedicated engine can produce this terminal')
            by_id = {fighter.id: fighter for fighter in snapshot.fighters}
            expected = {1: ('role', role, actor.attribute_version)}
            if actor.pet:
                expected[actor.pet.position] = ('pet', actor.pet.key, actor.pet.growth_version)
            if len(finished.combat_resources) != len(expected):
                raise ValueError('Complete admitted role/pet terminal resources required')
            seen = set()
            for resource in finished.combat_resources:
                f = by_id.get(resource.position)
                if (resource.position in seen or f is None
                        or (resource.kind, resource.entity_id, resource.source_version) != expected.get(resource.position)
                        or (resource.hp, resource.mp, resource.max_hp, resource.max_mp)
                            != (f.hp, f.mp, f.max_hp, f.max_mp)):
                    raise ValueError('Task terminal resources disagree with actual combat checkpoint')
                seen.add(resource.position)
        db.execute('UPDATE task_pve_runtime_battles SET fighters=?,round_number=?,state_version=?,'
            'snapshot_phase=?,terminal=?,terminal_hash=?,status=?,producer_kind=?,producer_epoch=? '
            'WHERE role_id=? AND battle_id=?',
            (_json([asdict(f) for f in snapshot.fighters]), snapshot.round_number, snapshot.state_version,
             snapshot.phase, _json(asdict(finished)) if finished is not None else None, digest,
             'terminal' if finished is not None else 'active',
             'owner_terminal' if finished is not None else None,
             str(epoch) if finished is not None else None,role, snapshot.battle_id))


def _producer(row):
    """Fingerprint only immutable admission/checkpoint/terminal producer data."""
    return _hash(dict(battle_id=row['battle_id'], accepted_epoch=row['accepted_epoch'],
        participant=json.loads(row['participant']), basis=json.loads(row['basis']),
        engine_revision=row['engine_revision'], fighters=json.loads(row['fighters']),
        round_number=row['round_number'], state_version=row['state_version'],
        snapshot_phase=row['snapshot_phase'], terminal=json.loads(row['terminal']),
        terminal_hash=row['terminal_hash'],producer_kind=row['producer_kind'],
        producer_epoch=row['producer_epoch']))


def _row(db, role, battle_id):
    names=('battle_id','accepted_epoch','participant','basis','engine_revision','fighters',
           'round_number','state_version','snapshot_phase','terminal','terminal_hash','receipt','status',
           'producer_kind','producer_epoch')
    result=db.execute('SELECT '+','.join(names)+' FROM task_pve_runtime_battles '
                      'WHERE role_id=? AND battle_id=?',(role,battle_id)).fetchone()
    if result is None:raise ValueError('No durable Task PVE producer admission')
    return dict(zip(names,result))


def _admission(db, role, battle_id):
    row=db.execute('SELECT fingerprint,plan FROM task_battle_admissions WHERE role_id=? AND battle_id=?',
                    (role,battle_id)).fetchone()
    if row is None:raise ValueError('Task PVE producer lacks its Task admission')
    return row[0],json.loads(row[1])


def _witness(role,epoch,row,admission_fingerprint):
    from task_battle import TaskBattleRecoveryWitness
    return TaskBattleRecoveryWitness(role,epoch,admission_fingerprint,row['terminal_hash'],
        'task-pve-producer:'+row['battle_id'],_producer(row),_hash(json.loads(row['basis'])))


def _task_rules(accounts):
    import runtime_storage as storage
    return {**storage._reward_rules(accounts),**storage._task_resource_rules(accounts)}


def _consume(db,accounts,account,role,epoch,actor,actual,finished,task_id,terminal_hash):
    """Actual losses first, dedicated dream recovery second; same outer TX."""
    import runtime_storage as storage
    from role_resource_plan import plan_combat_resources
    from role_resource_storage import apply_resource_transition,revive_task_dream_resources
    from role_attribute_storage import update_role_vitals
    from task_dream_resources import (TaskDreamRevivePermit,POLICY_SHA256,
                                      plan_legacy_task_dream_revival)
    inventory=storage._inventory(accounts,account,role,epoch)
    role_results=tuple(entry for entry in finished.combat_resources if entry.kind=='role')
    pet_results=tuple(entry for entry in finished.combat_resources if entry.kind=='pet')
    if len(role_results)!=1 or len(finished.combat_resources)!=1+int(actor.pet is not None):
        raise ValueError('Exact admitted role/pet terminal required for consumption')
    raw=role_results[0]
    before=actual.vitals
    if ((raw.entity_id,raw.position,raw.source_version,raw.max_hp,raw.max_mp)
            !=(role,1,actor.attribute_version,before.max_hp,before.max_mp)
            or type(raw.hp) is not int or type(raw.mp) is not int
            or not 0<=raw.hp<=before.hp or not 0<=raw.mp<=before.mp):
        raise ValueError('Task terminal role resources changed their complete admission')
    resources=actual.resources
    if resources is not None:
        transition=plan_combat_resources(resources,raw.hp,raw.mp,accounts.resource_rules)
        result=apply_resource_transition(db,account,role,epoch,transition,
            finished.settlement_id+':role-resources',rules=accounts.resource_rules,
            equipment_rules=accounts.equipment_attribute_rules)
        carrier=result.resources
    else:
        carrier=before
        if (raw.hp,raw.mp)!=(before.hp,before.mp):
            carrier=replace(before,version=before.version+1,hp=raw.hp,mp=raw.mp)
            update_role_vitals(db,account,role,epoch,before,carrier)
    revived=False
    if raw.hp==0:
        # This new authorization belongs to the CURRENT lease; the immutable
        # original terminal/epoch remain bound by terminal_hash and Task witness.
        permit=TaskDreamRevivePermit(role,epoch,task_id,finished.battle_id,
            finished.settlement_id,finished.revision,POLICY_SHA256,terminal_hash,raw,carrier.version)
        if resources is not None:
            revive_task_dream_resources(db,account,role,epoch,carrier,permit,
                rules=accounts.resource_rules,equipment_rules=accounts.equipment_attribute_rules)
        else:
            update_role_vitals(db,account,role,epoch,carrier,
                              plan_legacy_task_dream_revival(carrier,permit))
        revived=True
    if actor.pet is None:
        if pet_results:raise ValueError('Unadmitted pet terminal')
    else:
        pet=actor.pet
        if len(pet_results)!=1:raise ValueError('Original owned pet terminal required')
        result=pet_results[0]
        if ((result.entity_id,result.position,result.source_version,result.inventory_revision,
             result.growth_revision,result.max_hp,result.max_mp)
                !=(pet.key,pet.position,pet.growth_version,pet.inventory_revision,
                   pet.growth_revision,pet.stats.max_hp,pet.max_mp)
                or type(result.hp) is not int or type(result.mp) is not int
                or not 0<=result.hp<=pet.stats.hp or not 0<=result.mp<=pet.stats.mp):
            raise ValueError('Task pet resources differ from the owned admission')
        inventory.change_pet_growth(db,pet.key,finished.settlement_id+':pet-resources',
            pet.growth_version,'resources',(result.hp,result.mp))
        storage._synchronize_source(db,accounts,inventory,
            finished.settlement_id+':pet-resource-source',replayed=False)
    return inventory,revived


def _committed(db,accounts,account,role,epoch,actor,inventory,settlement):
    import runtime_storage as storage
    from task_workflow import completion_messages
    from inventory import REFRESH_PET,pet_record
    profile=storage._role_profile_transaction(db,accounts,account,role,epoch,inventory)
    if settlement.completion is not None:
        completion=storage._project_completion(db,accounts,account,role,epoch,
                                               settlement.completion,inventory)
        settlement=replace(settlement,completion=completion,messages=completion_messages(completion))
    messages=list(settlement.messages)
    if profile.refresh is not None:
        messages=[packet for packet in messages if packet[0]!=profile.refresh[0]]
        messages.append(profile.refresh)
    if actor.pet is not None:
        current=inventory.read_pet_state(db,actor.pet.key)
        if current is None and settlement.replayed:
            pass  # A legitimately released old pet is no longer current UI state.
        elif current is None or current.progress is None:
            raise ValueError('Original task pet unavailable for final native encoding')
        else:messages.append((REFRESH_PET,pet_record(current.__dict__)))
    # Every native body above is constructed before this caller transaction can
    # commit. The immutable packets are sent only after the context exits.
    return TaskPveCommit(profile.role,tuple(messages),settlement.replayed,settlement)


def _settle(db,accounts,account,role,epoch,battle_id,*,recovery=False):
    import runtime_storage as storage
    from task_battle import (settle_task_battle_transaction,recover_task_battle_transaction,
                            read_task_battle_current_transaction)
    _scope(db,account,role,epoch)
    row=_row(db,role,battle_id)
    if row['terminal'] is None or row['status'] not in ('terminal','settled'):
        raise ValueError('Actual durable Task PVE terminal required')
    event=_finished(json.loads(row['terminal']))
    if _hash(asdict(event))!=row['terminal_hash']:
        raise ValueError('Task PVE terminal outbox fingerprint mismatch')
    if (row['producer_kind'] not in ('owner_terminal','lease_abort')
            or not row['producer_epoch']
            or row['producer_kind']=='owner_terminal' and row['producer_epoch']!=row['accepted_epoch']
            or row['producer_kind']=='lease_abort' and event.outcome!='draw'):
        raise ValueError('Task PVE producer authorization is missing or inconsistent')
    actor=_participant(json.loads(row['participant']))
    admission_fingerprint,plan=_admission(db,role,battle_id)
    if (plan['participant']!=json.loads(row['participant']) or plan['epoch']!=actor.login_epoch
            or row['accepted_epoch']!=str(actor.login_epoch) or row['engine_revision']!=event.revision
            or plan['engine_revision']!=event.revision or event.role_id!=role
            or event.login_epoch!=actor.login_epoch or event.snapshot_version!=actor.attribute_version):
        raise ValueError('Task producer and admission identity/source disagree')
    inventory=storage._inventory(accounts,account,role,epoch)
    witness=_witness(role,epoch,row,admission_fingerprint)
    if row['status']=='settled':
        # Paid is a strictly current read, with no Task chain/grant/heal replay.
        receipt=json.loads(row['receipt']) if row['receipt'] else None
        if receipt is None or (receipt['terminal_fingerprint'],receipt['producer_fingerprint'])!=(
                row['terminal_hash'],_producer(row)):
            raise ValueError('Task PVE consumer receipt differs from its producer')
        result=read_task_battle_current_transaction(db,account,role,epoch,accounts.task_resources,
            accounts.task_battle_resources,event,inventory,currency_rules=accounts.currency_rules,
            **storage._task_resource_rules(accounts))
        return _committed(db,accounts,account,role,epoch,actor,inventory,result)
    if (type(epoch) is not type(actor.login_epoch) or epoch!=actor.login_epoch) and not recovery:
        raise ValueError('Old task terminal needs the explicit current-lease recovery Interface')
    actual=read_combat_snapshot_transaction(db,accounts,account,role,epoch,
        actor.connection_generation,accounts.task_pve_rules)
    if actual.basis!=row['basis']:
        raise ValueError('Complete Task battle asset/profile source changed; terminal remains pending')
    # Identity of the adopted checkpoint must still match the original source.
    from world_transfer_storage import load_map_instance_transaction
    saved=plan['ticket']['location']
    checkpoint=load_map_instance_transaction(db,account,role,epoch)
    if checkpoint is None or (asdict(checkpoint.address),checkpoint.position,checkpoint.version)!=(
            saved['address'],(saved['address']['map_id'],saved['x'],saved['y']),saved['version']):
        raise ValueError('Task battle adopted checkpoint changed before terminal consumption')
    inventory,revived=_consume(db,accounts,account,role,epoch,actor,actual,event,
                               plan['task_id'],row['terminal_hash'])
    if recovery:
        result=recover_task_battle_transaction(db,account,role,epoch,accounts.task_resources,
            accounts.task_battle_resources,event,inventory,witness,**_task_rules(accounts))
    else:
        result=settle_task_battle_transaction(db,account,role,epoch,accounts.task_resources,
            accounts.task_battle_resources,event,inventory,**_task_rules(accounts))
    # Original first-skill continuation is activated only after genuine victory,
    # in this same transaction. No skill is granted by the battle itself.
    if event.won and not result.replayed:
        from task_first_skill import reconcile_first_skill_successor_transaction
        activated=reconcile_first_skill_successor_transaction(db,account,role,epoch,
            accounts.task_resources,accounts.first_skill_rules,plan['task_id'])
        if activated and result.completion is not None:
            from task_protocol import ScenarioQuestInfo,SCENARIO_ACTIVE
            completion=result.completion
            missing=tuple(q for q in activated if q not in completion.started_tasks)
            if missing:
                completion=replace(completion,started_tasks=completion.started_tasks+missing,
                    started_infos=completion.started_infos+tuple(
                        ScenarioQuestInfo(q,SCENARIO_ACTIVE,0,0,0) for q in missing))
                result=replace(result,completion=completion)
    committed=_committed(db,accounts,account,role,epoch,actor,inventory,result)
    receipt=dict(terminal_fingerprint=row['terminal_hash'],producer_fingerprint=_producer(row),
        accepted_epoch=actor.login_epoch,consumer_epoch=epoch,dream_revived=revived,
        task_id=plan['task_id'],settlement_id=event.settlement_id,
        recovery_revision='2026-10-24.task-terminal-recovery.1')
    db.execute("UPDATE task_pve_runtime_battles SET status='settled',receipt=? "
        "WHERE role_id=? AND battle_id=? AND status='terminal'",(_json(receipt),role,battle_id))
    return committed


def settle(accounts,account,role,epoch,battle_id):
    with closing(accounts.leased(account,role,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        return _settle(db,accounts,account,role,epoch,battle_id)


def recover(accounts,account,role,epoch):
    """Earliest new-lease role load; no conflicting role command runs first.

    Preserve an existing real terminal verbatim. Without one, the current lease
    retires the fenced old host and creates a dedicated no-award terminal from
    its saved combat copy. Source drift leaves everything pending and fails
    this role's load rather than replacing assets or manufacturing a victory.
    """
    from battle_owner import BattleSnapshot
    from task_pve_recovery import abort_checkpoint_terminal
    with closing(accounts.leased(account,role,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        _scope(db,account,role,epoch)
        pending=db.execute("SELECT battle_id FROM task_pve_runtime_battles "
                           "WHERE role_id=? AND status!='settled'",(role,)).fetchall()
        if len(pending)>1:raise ValueError('Conflicting pending Task PVE admissions')
        if not pending:return None
        battle_id=pending[0][0]
        row=_row(db,role,battle_id)
        actor=_participant(json.loads(row['participant']))
        if row['status']=='active':
            if row['terminal'] is not None or row['terminal_hash'] is not None:
                raise ValueError('Active Task PVE record conflicts with its producer outbox')
            if str(actor.login_epoch)==str(epoch):
                raise ValueError('A current live battle cannot be retired as old-lease recovery')
            admission_fingerprint,plan=_admission(db,role,battle_id)
            if (plan['participant']!=json.loads(row['participant'])
                    or plan['epoch']!=actor.login_epoch or row['accepted_epoch']!=str(actor.login_epoch)
                    or row['engine_revision']!=accounts.task_pve_rules.revision
                    or plan['engine_revision']!=row['engine_revision']
                    or plan['task_id'] not in accounts.task_battle_resources.enabled_task_ids):
                raise ValueError('Task PVE retirement differs from its approved admission')
            actual=read_combat_snapshot_transaction(db,accounts,account,role,epoch,
                actor.connection_generation,accounts.task_pve_rules)
            if actual.basis!=row['basis']:
                raise ValueError('Task recovery source drift; original checkpoint remains pending')
            snapshot=BattleSnapshot(battle_id,row['state_version'],row['round_number'],
                row['snapshot_phase'],tuple(_fighter(item) for item in json.loads(row['fighters'])))
            event=abort_checkpoint_terminal(actor,snapshot,accounts.task_pve_rules,current_epoch=epoch)
            # Durable producer has its own current-lease retirement authority;
            # original Participant/event epoch are never edited to match it.
            db.execute("UPDATE task_pve_runtime_battles SET terminal=?,terminal_hash=?,"
                "snapshot_phase='ended',state_version=state_version+1,status='terminal',"
                "producer_kind='lease_abort',producer_epoch=? WHERE role_id=? AND battle_id=? AND status='active'",
                (_json(asdict(event)),_hash(asdict(event)),str(epoch),role,battle_id))
    with closing(accounts.leased(account,role,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        return _settle(db,accounts,account,role,epoch,battle_id,recovery=True)

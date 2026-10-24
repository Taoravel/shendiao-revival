"""Storage Seam: startup preparation and fenced role-scoped transactions."""
from contextlib import closing
from dataclasses import asdict,dataclass,replace
from types import MappingProxyType
import hashlib
import json
from inventory import Inventory,INVENTORY_CURRENT_MUTATION_TYPES
from tasks import TaskStore, prepare_task_store
from social_owner import SQLiteSocialStore
from world_catalog import maps,maze_grids
from task_persistence import load_task_state,apply_task_plan
from inspect_client import OUT
from world_npcs import load_placements,load_npc_definitions
from task_rewards import prepare_reward_storage
from task_workflow import complete_task_transaction,refresh_completion_pet,completion_messages
from task_pet_experience import load_task_pet_experience_rules
from progression import read_experience
import world_transfer_storage
import world_story_instances
from currency import load_currency_rules,prepare_wallet_storage,initialize_wallet,read_wallet,WalletNotInitialized
from role_growth import load_growth_rules,prepare_growth_storage,read_growth,initialize_growth,GrowthResourceContext
from role_attributes import load_attribute_rules
from role_attribute_storage import prepare_attribute_storage,attribute_snapshot_if_initialized,initialize_attribute_baseline
from role_attribute_protocol import growth_refresh,role_detail_vitals
from role_growth_actions import manual_level_transaction,allocation_transaction
import task_newbie_chapter
import task_master_card
import task_cart_dialogue
import task_cart_transfer
import task_prologue_touch
from world_protocol import scene_entry
from role_equipment import EquipmentAttributeBasis,load_equipment_attribute_rules
from role_equipment_storage import (prepare_equipment_attribute_storage,read_equipment_attribute_basis,
    initialize_equipment_attribute_basis,current_equipment_projection,current_equipment_totals,
    current_resource_profile,synchronize_inventory_resource_source)
from role_equipment import resource_caps_from_projection
from role_resource_plan import load_resource_rules,plan_resource_caps
from role_resource_storage import read_role_resources,apply_resource_transition,ResourceNotInitialized
import npc_gameplay
import npc_interaction
from wild_encounters import load_wild_rules
from wild_rewards import load_wild_reward_rules,prepare_wild_reward_storage
import wild_runtime_storage
from world_newbie import NewbieFlow,load_newbie_routes,validate_birth_sites


@dataclass(frozen=True)
class CommittedRoleState:
    role_id: int
    epoch: object
    level: int
    experience: int


@dataclass(frozen=True)
class CommittedTask:
    completion: object
    role: CommittedRoleState
    extra_messages: tuple = ()


@dataclass(frozen=True)
class CommittedGrowth:
    action: object
    role: CommittedRoleState


@dataclass(frozen=True)
class CommittedNewbie:
    action: object
    role: CommittedRoleState


@dataclass(frozen=True)
class CommittedMaster:
    action: object
    role: CommittedRoleState


@dataclass(frozen=True)
class CommittedCart:
    action: object
    role: CommittedRoleState
    scene_body: bytes


@dataclass(frozen=True)
class CommittedTouch:
    action: object
    role: CommittedRoleState
    scene_body: bytes | None


@dataclass(frozen=True)
class RoleLoadProfile:
    role: CommittedRoleState
    growth: object = None
    attributes: object = None
    refresh: object = None
    task_messages: tuple = ()


@dataclass(frozen=True)
class LoginMapRecovery:
    decision: object
    checkpoint: object
    story_instance: object = None


@dataclass(frozen=True)
class OpenedPrologue:
    intent: object
    messages: tuple
    directory: object


def prepare(accounts):
    accounts.inventory_config = Inventory.prepare(accounts)
    tasks = prepare_task_store(accounts)
    social = SQLiteSocialStore(accounts.path)
    social.initialize()
    accounts.npc_resources=(load_placements(),load_npc_definitions())
    npc_interaction.prepare(accounts)
    npc_gameplay.prepare(accounts)
    accounts.currency_rules=load_currency_rules()
    accounts.growth_rules=load_growth_rules()
    accounts.attribute_rules=load_attribute_rules()
    accounts.task_pet_experience_rules=load_task_pet_experience_rules()
    catalog=maps()
    grids=maze_grids()
    accounts.movement_grids=MappingProxyType(dict(grids))
    from runtime_movement import load_movement_policy
    accounts.movement_policy=load_movement_policy()
    routes=load_newbie_routes()
    accounts.newbie_birth_sites=validate_birth_sites(routes,catalog,grids,accounts.npc_resources[0],
        state_byte=0,interaction_radius=32,max_visited=100000)
    newbie_rules=task_newbie_chapter.load_newbie_chapter_rules(tasks,routes,catalog,grids)
    story_rules=world_story_instances.load_story_instance_rules(tasks,newbie_rules)
    touch_resources=task_prologue_touch.load_touch_resources(tasks,task_prologue_touch.load_touch_policy(),
        catalog,grids,chapter_rules=newbie_rules,story_rules=story_rules)
    master_rules=task_master_card.load_master_card_rules(tasks,newbie_rules,accounts.inventory_config)
    cart_resources=task_cart_dialogue.load_cart_resources(tasks,master_rules)
    cart_rules=task_cart_transfer.load_cart_transfer_rules(cart_resources,catalog,grids)
    equipment_rules=load_equipment_attribute_rules()
    resource_rules=load_resource_rules()
    wild_rules=load_wild_rules()
    wild_reward_rules=load_wild_reward_rules()
    # Explicit implemented capabilities: original task metadata alone never
    # enables a fight. Every enabled ID belongs to this reviewed dedicated AI.
    from task_pve import load_task_pve_rules
    from training_battle import DEFAULT_RULES
    from task_battle import load_task_battle_resources
    from task_first_battle import load_first_battle_rules
    from task_first_skill import load_first_skill_rules,prepare_first_skill_storage
    from role_skills import (load_other_skill_rules,prepare_other_skill_storage,
                             load_local_prologue_baseline_rules)
    import task_pve_runtime_storage
    task_pve_rules=load_task_pve_rules(OUT/'design/task-pve-ai8001-v1.json',
                                      pet_templates=DEFAULT_RULES.pet_templates)
    task_battle_resources=load_task_battle_resources(tasks,
        enabled_task_ids=task_pve_rules.enabled_task_ids,engine_revision=task_pve_rules.revision)
    first_battle_rules=load_first_battle_rules(tasks,newbie_rules,story_rules,
        task_battle_resources,accounts.npc_resources[0])
    first_skill_rules=load_first_skill_rules(tasks,newbie_rules,story_rules,accounts.npc_resources[0])
    other_skill_rules=load_other_skill_rules()
    local_skill_baseline_rules=load_local_prologue_baseline_rules(
        path=OUT/'design/local-prologue-other-skills-baseline-v1.json',
        attribute_rules=accounts.attribute_rules,growth_rules=accounts.growth_rules,
        currency_rules=accounts.currency_rules)
    with closing(accounts.connect()) as db,db:
        task_pve_runtime_storage.prepare(db)
        prepare_other_skill_storage(db)
        prepare_first_skill_storage(db)
        prepare_wild_reward_storage(db)
        wild_runtime_storage.prepare(db)
        prepare_reward_storage(db)
        world_transfer_storage.prepare(db)
        world_story_instances.prepare_story_instance_storage(db)
        task_prologue_touch.prepare_touch_storage(db)
        prepare_wallet_storage(db)
        prepare_growth_storage(db)
        prepare_attribute_storage(db)
        task_newbie_chapter.prepare_newbie_chapter_storage(db)
        task_master_card.prepare_master_card_storage(db)
        task_cart_transfer.prepare_cart_transfer_storage(db)
        prepare_equipment_attribute_storage(db)
        db.execute('''CREATE TABLE IF NOT EXISTS role_inventory_commands (
            role_id INTEGER NOT NULL REFERENCES roles(id),request_id TEXT NOT NULL,
            fingerprint TEXT NOT NULL,accepted_epoch TEXT NOT NULL,
            PRIMARY KEY(role_id,request_id))''')
        db.execute('''CREATE TABLE IF NOT EXISTS role_restoration_origins (
            role_id INTEGER PRIMARY KEY REFERENCES roles(id), origin TEXT NOT NULL,
            wallet_policy TEXT NOT NULL, creation_profile TEXT, creation_profile_receipt TEXT)''')
        columns={row[1] for row in db.execute('PRAGMA table_info(role_restoration_origins)')}
        for column in ('creation_profile','creation_profile_receipt'):
            if column not in columns:
                db.execute(f'ALTER TABLE role_restoration_origins ADD COLUMN {column} TEXT')
    policy = json.loads((OUT/'design/recovery-baseline.json').read_text(encoding='utf-8'))['social']
    # Publish creation dependencies only after all startup validation/schema work.
    accounts.task_resources=tasks
    accounts.newbie_rules=newbie_rules
    accounts.story_instance_rules=story_rules
    accounts.prologue_touch_resources=touch_resources
    accounts.master_card_rules=master_rules
    accounts.cart_resources=cart_resources
    accounts.cart_transfer_rules=cart_rules
    accounts.equipment_attribute_rules=equipment_rules
    accounts.resource_rules=resource_rules
    accounts.wild_rules=wild_rules
    accounts.wild_reward_rules=wild_reward_rules
    accounts.task_pve_rules=task_pve_rules
    accounts.task_battle_resources=task_battle_resources
    accounts.first_battle_rules=first_battle_rules
    accounts.first_skill_rules=first_skill_rules
    accounts.other_skill_rules=other_skill_rules
    accounts.local_prologue_skill_baseline_rules=local_skill_baseline_rules
    return tasks, social, policy, catalog


def other_skill_login_messages(accounts,account,role,epoch):
    from role_skills import read_other_skills,other_skill_messages
    with closing(accounts.leased(account,role,epoch).connect()) as db,db:
        db.execute('BEGIN')
        snapshot=read_other_skills(db,account,role,epoch,accounts.other_skill_rules)
        return () if snapshot is None else other_skill_messages(snapshot,accounts.other_skill_rules)


def prepare_login_transfer_recovery(accounts,account_id,role_id,epoch):
    """New lease first: commit the final old handoff decision before map cleanup."""
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        return world_transfer_storage.prepare_transfer_recovery_transaction(db,account_id,role_id,epoch)


def prepare_login_map_recovery(accounts,account_id,role_id,epoch):
    """Resolve old handoff and read its exact instance in the same lease txn."""
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        decision=world_transfer_storage.prepare_transfer_recovery_transaction(db,account_id,role_id,epoch)
        checkpoint=world_transfer_storage.load_map_instance_transaction(db,account_id,role_id,epoch)
        entry=None
        if checkpoint is not None and checkpoint.address.instance_id>=2**62:
            rules=accounts.story_instance_rules
            chapter=task_newbie_chapter.read_newbie_chapter(db,account_id,role_id,epoch,accounts.newbie_rules)
            if chapter is None or chapter.phase!='completed':
                raise ValueError('Private checkpoint requires its completed creation chapter')
            origin=chapter.origin;route=origin.route
            intent=world_story_instances.StoryInstanceIntent(origin.chapter_id,origin.creation_id,
                origin.policy,origin.route_fingerprint,rules.source_tasks[(route.character_id,route.school_id)])
            entry=world_story_instances.load_story_instance_transaction(db,account_id,role_id,epoch,
                intent,rules,expected_address=checkpoint.address)
            if entry is None:raise ValueError('Private checkpoint has no matching durable story identity')
        return LoginMapRecovery(decision,checkpoint,entry)


def load_role(accounts, account_id, role_id, epoch, tasks):
    leased = accounts.leased(account_id,role_id,epoch)
    with closing(leased.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        world_transfer_storage.recover(db,role_id,epoch)
        origin=db.execute('SELECT origin,wallet_policy FROM role_restoration_origins WHERE role_id=?',(role_id,)).fetchone()
        if origin:
            if origin[1]!=accounts.currency_rules.revision: raise ValueError('Wallet creation policy requires migration')
            initialize_wallet(db,account_id,role_id,epoch,tuple(0 for _ in accounts.currency_rules.currencies),
                              origin[0],accounts.currency_rules)
        _initialize_creation_profile(db,accounts,account_id,role_id,epoch)
        flow=NewbieFlow(tasks,accounts.newbie_rules.routes)
        chapter=task_newbie_chapter.initialize_newbie_chapter(db,account_id,role_id,epoch,flow,accounts.newbie_rules)
        if chapter is not None:
            # Only the independently recorded creation operation authorizes the
            # designed sealing basis. Missing legacy fields grant no authority.
            rules=accounts.equipment_attribute_rules
            initialize_equipment_attribute_basis(db,account_id,role_id,epoch,EquipmentAttributeBasis(
                role_id,chapter.origin.route.character_id,0,rules.revision,rules.new_role_seal_strength,
                'newbie-creation:'+chapter.origin.creation_id),rules)
    return (_inventory(accounts,account_id,role_id,epoch), TaskStore(leased,resources=tasks),
            leased.position(account_id,role_id), accounts.position_version(role_id))


def newbie_state(accounts,account_id,role_id,epoch):
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        return task_newbie_chapter.read_newbie_chapter(db,account_id,role_id,epoch,accounts.newbie_rules)


def newbie_playback(accounts,account_id,role_id,epoch,location,generation,request_id,now_ms,ticket=None):
    rules=accounts.newbie_rules
    flow=(NewbieFlow.from_ticket(accounts.task_resources,rules.routes,ticket) if ticket is not None
          else NewbieFlow(accounts.task_resources,rules.routes))
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        return task_newbie_chapter.authorize_newbie_playback(db,account_id,role_id,epoch,flow,rules,location,
            generation=generation,request_id=request_id,now_ms=now_ms)


def newbie_finish(accounts,account_id,role_id,epoch,body,location,generation,now_ms,ticket,inventory):
    rules=accounts.newbie_rules
    flow=(NewbieFlow.from_ticket(accounts.task_resources,rules.routes,ticket) if ticket is not None
          else NewbieFlow(accounts.task_resources,rules.routes))
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        result=task_newbie_chapter.finish_newbie_chapter(db,account_id,role_id,epoch,flow,rules,body,location,inventory,
            generation=generation,now_ms=now_ms,growth_rules=accounts.growth_rules,
            attribute_rules=accounts.attribute_rules,currency_rules=accounts.currency_rules,
            pet_experience_rules=accounts.task_pet_experience_rules,**_task_resource_rules(accounts))
        completion=_project_completion(db,accounts,account_id,role_id,epoch,result.completion,inventory)
        result=replace(result,completion=completion)
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        completion=refresh_completion_pet(db,load_task_state(db,account_id,role_id,epoch)[0],result.completion,inventory)
        messages=completion_messages(completion) if result.evidence is not None else ()
        result=replace(result,completion=completion,messages=messages)
        balance=read_experience(db,account_id,role_id)
        return CommittedNewbie(result,CommittedRoleState(role_id,epoch,balance.level,balance.experience))


def _initialize_creation_profile(db,accounts,account_id,role_id,epoch):
    """Redeem only a durable creation-time template, once, in the lease transaction.

    NULL old provenance is intentionally inert. A changed pre-login character
    needs reconciliation; neither its current level nor an old wallet origin
    authorizes inventing a historical attribute/potential baseline.
    """
    row=db.execute('SELECT origin,creation_profile,creation_profile_receipt '
                   'FROM role_restoration_origins WHERE role_id=?',(role_id,)).fetchone()
    if not row or row[1] is None:
        return
    fingerprint=hashlib.sha256(row[1].encode('utf-8')).hexdigest()
    if row[2] is not None:
        if row[2]!=fingerprint: raise ValueError('Creation profile receipt mismatch')
        for table in ('role_growth','role_attribute_baselines','role_attribute_snapshots'):
            if not db.execute(f'SELECT 1 FROM {table} WHERE role_id=?',(role_id,)).fetchone():
                raise ValueError('Initialized creation profile is incomplete; reconciliation required')
        return
    rules=accounts.attribute_rules
    growth_rules=accounts.growth_rules
    if rules is None or growth_rules is None or rules.initial_profile is None:
        raise ValueError('Creation profile requires prepared policy')
    expected=dict(format=1,source='design/role-attributes-v1.json#new_role_designed_baseline',
        provenance='designed',growth_policy=growth_rules.revision,attribute_policy=rules.revision,
        profile=asdict(rules.initial_profile))
    if (row[0]!='new_restoration_role' or json.loads(row[1])!=json.loads(json.dumps(expected))
            or rules.growth_policy!=growth_rules.revision):
        raise ValueError('Creation profile requires explicit policy reconciliation')
    initial=rules.initial_profile
    balance=read_experience(db,account_id,role_id)
    if initial.level!=1 or (balance.level,balance.experience)!=(initial.level,0):
        raise ValueError('Character advanced before creation profile initialization')
    for table in ('role_growth','role_attribute_baselines','role_attribute_snapshots',
                  'role_growth_receipts','role_settlements','task_journal','task_reward_channels'):
        if db.execute(f'SELECT 1 FROM {table} WHERE role_id=? LIMIT 1',(role_id,)).fetchone():
            raise ValueError('Character has prior progression; creation profile reconciliation required')
    growth=initialize_growth(db,account_id,role_id,epoch,growth_rules,
        expected_level=initial.level,free_points=initial.free_points,known_allocated=(0,0,0,0,0))
    attributes=initialize_attribute_baseline(db,account_id,role_id,epoch,initial.baseline(role_id),
        growth,rules,initial.vitals(role_id))
    role_detail_vitals(role_id,attributes)
    growth_refresh(growth,attributes)
    db.execute('UPDATE role_restoration_origins SET creation_profile_receipt=? WHERE role_id=?',
               (fingerprint,role_id))


def settle(accounts, account_id, role_id, epoch, change):
    """Assets plus common idempotency receipt in the same fenced transaction.

    Only trusted role-owner commands call this; no client packet grants assets.
    Currency/progression/task rewards remain separate until their contracts land.
    """
    inv = _inventory(accounts,account_id,role_id,epoch)
    fingerprint = hashlib.sha256(json.dumps(asdict(change),sort_keys=True).encode()).hexdigest()
    with closing(inv.accounts.connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT fingerprint,receipt FROM role_settlements WHERE role_id=? AND settlement_id=?',
                              (role_id,change.settlement_id)).fetchone()
        if previous:
            if previous[0]!=fingerprint: raise ValueError('Settlement key conflict')
            _synchronize_source(db,accounts,inv,change.settlement_id,replayed=True)
            return json.loads(previous[1])
        receipt = json.loads(json.dumps(asdict(inv.apply_settlement(db,change))))
        _synchronize_source(db,accounts,inv,change.settlement_id,replayed=False)
        if _resource_state(db,accounts,account_id,role_id,epoch) is not None:
            _role_profile_transaction(db,accounts,account_id,role_id,epoch,inv)
        db.execute('INSERT INTO role_settlements VALUES(?,?,?,?)',
                   (role_id,change.settlement_id,fingerprint,json.dumps(receipt)))
        return receipt


def task_state(accounts,account_id,role_id,epoch):
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        return load_task_state(db,account_id,role_id,epoch)


def commit_task(accounts,account_id,role_id,epoch,actor,plan,request_id):
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        return apply_task_plan(db,actor,plan,request_id)


def complete_conversation(accounts,account_id,role_id,epoch,actor,plan,request_id,resources,inventory,prologue_touch=False):
    # Prepared dependencies are required here. Never silently choose legacy
    # defaults for a role whose durable growth/attribute baseline already exists.
    growth_rules=accounts.growth_rules
    attribute_rules=accounts.attribute_rules
    currency_rules=accounts.currency_rules
    pet_experience_rules=accounts.task_pet_experience_rules
    if any(rules is None for rules in (growth_rules,attribute_rules,currency_rules,pet_experience_rules)):
        raise ValueError('Task completion requires prepared growth, attribute, currency and task pet XP rules')
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        completion=complete_task_transaction(db,actor,plan,request_id,resources,inventory,
            growth_rules=growth_rules,attribute_rules=attribute_rules,currency_rules=currency_rules,
            pet_experience_rules=pet_experience_rules,**_task_resource_rules(accounts))
        completion=_project_completion(db,accounts,account_id,role_id,epoch,completion,inventory)
        extra=()
        touch=accounts.prologue_touch_resources
        if prologue_touch and any(plan.task_id==row['incoming_ids'][0] for row in touch.definitions.values()):
            activated=task_prologue_touch.reconcile_touch_successor_transaction(db,account_id,role_id,epoch,
                resources,touch,plan.task_id)
            if activated:
                extra=task_prologue_touch.resume_touch_messages(db,account_id,role_id,epoch,resources,touch)
    # Exiting the first transaction must succeed before any sendable pet state
    # is built. Read the recorded recipient, never the currently selected pet.
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        completion=refresh_completion_pet(db,actor,completion,inventory)
        balance=read_experience(db,account_id,role_id)
        return CommittedTask(completion,CommittedRoleState(role_id,epoch,balance.level,balance.experience),extra)


def prologue_resume(accounts,account_id,role_id,epoch):
    """Explicit runtime opt-in: recover only this chapter's approved pending edge."""
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        chapter=_completed_chapter(db,accounts,account_id,role_id,epoch)
        if chapter is None:return ()
        touch=accounts.prologue_touch_resources;route=chapter.origin.route
        task_id=touch.route_tasks[(route.character_id,route.school_id)]
        predecessor=touch.definitions[task_id]['incoming_ids'][0]
        _,state=load_task_state(db,account_id,role_id,epoch)
        if predecessor in state.completed and task_id not in state.active|state.completed:
            task_prologue_touch.reconcile_touch_successor_transaction(db,account_id,role_id,epoch,
                accounts.task_resources,touch,predecessor)
        return task_prologue_touch.resume_touch_messages(db,account_id,role_id,epoch,
            accounts.task_resources,touch)


def prologue_dialogue(accounts,account_id,role_id,epoch,proof,location,generation,now_ms):
    """Adopt the map-proven source, allocate identity, then open one timed ticket."""
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        chapter=_completed_chapter(db,accounts,account_id,role_id,epoch)
        if chapter is None:return None
        touch=accounts.prologue_touch_resources;origin=chapter.origin;route=origin.route
        task_id=touch.route_tasks[(route.character_id,route.school_id)]
        _,state=load_task_state(db,account_id,role_id,epoch)
        if task_id not in state.active:return None
        world_transfer_storage.bind_map_instance_transaction(db,account_id,role_id,epoch,location)
        directory_intent=world_story_instances.StoryInstanceIntent(origin.chapter_id,origin.creation_id,
            origin.policy,origin.route_fingerprint,task_id)
        entry=world_story_instances.allocate_story_instance_transaction(db,account_id,role_id,epoch,
            directory_intent,accounts.story_instance_rules)
        dialogue=task_prologue_touch.open_touch_transaction(db,account_id,role_id,epoch,
            accounts.task_resources,touch,task_id,proof,location,target_address=entry.address,
            generation=generation,now_ms=now_ms)
        return OpenedPrologue(dialogue.intent,dialogue.messages,entry)


def prologue_authorize(accounts,account_id,role_id,epoch,ticket,command,location,proof,generation,now_ms):
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        return task_prologue_touch.authorize_touch_transfer(db,account_id,role_id,epoch,
            accounts.task_resources,accounts.prologue_touch_resources,ticket,command,location,
            proof=proof,generation=generation,now_ms=now_ms)


def complete_prologue_transfer(accounts,account_id,role_id,epoch,intent,receipt,inventory,generation,now_ms):
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        result=task_prologue_touch.complete_touch_transfer_transaction(db,account_id,role_id,epoch,
            accounts.task_resources,accounts.prologue_touch_resources,intent,receipt,inventory,
            generation=generation,now_ms=now_ms,movement_state=0,**_reward_rules(accounts),**_task_resource_rules(accounts))
        profile=_role_profile_transaction(db,accounts,account_id,role_id,epoch,inventory)
        if result.replayed:return CommittedTouch(result,profile.role,None)
        completion=_project_completion(db,accounts,account_id,role_id,epoch,result.completion,inventory)
        messages=result.messages
        if profile.refresh is not None:
            messages=tuple(message for message in messages if message[0]!=profile.refresh[0])+(profile.refresh,)
        result=replace(result,completion=completion,messages=messages)
        body=scene_entry(result.target.position,reason=0)
        return CommittedTouch(result,profile.role,body)


def experience(accounts,account_id,role_id,epoch):
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        return read_experience(db,account_id,role_id).experience


def manual_level(accounts,account_id,role_id,epoch,opaque_field,request_id):
    """Current explicit profile and encoded logical messages, only after COMMIT."""
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT 1 FROM role_attribute_baselines WHERE role_id=?',(role_id,)).fetchone():
            raise ValueError('Manual level requires a complete explicit role profile')
        result=manual_level_transaction(db,account_id,role_id,epoch,opaque_field,request_id,
            accounts.growth_rules,accounts.attribute_rules,
            resource_context=_growth_context(db,accounts,account_id,role_id,epoch))
        profile=_role_profile_transaction(db,accounts,account_id,role_id,epoch)
        result=replace(result,attributes=profile.attributes,
            messages=tuple(message for message in result.messages if message[0]!=profile.refresh[0])+(profile.refresh,))
        return CommittedGrowth(result,CommittedRoleState(role_id,epoch,result.growth.level,result.growth.experience))


def allocate_potential(accounts,account_id,role_id,epoch,deltas,request_id):
    """Spend current free points on internal stat increments, never create a profile."""
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT 1 FROM role_attribute_baselines WHERE role_id=?',(role_id,)).fetchone():
            raise ValueError('Allocation requires a complete explicit role profile')
        result=allocation_transaction(db,account_id,role_id,epoch,deltas,request_id,
            accounts.growth_rules,accounts.attribute_rules,
            resource_context=_growth_context(db,accounts,account_id,role_id,epoch))
        profile=_role_profile_transaction(db,accounts,account_id,role_id,epoch)
        result=replace(result,attributes=profile.attributes,
            messages=tuple(message for message in result.messages if message[0]!=profile.refresh[0])+(profile.refresh,))
        return CommittedGrowth(result,CommittedRoleState(role_id,epoch,result.growth.level,result.growth.experience))


def role_load_profile(accounts,account_id,role_id,epoch):
    """One consistent explicit profile, or the separate compatibility path.

    Never creates a baseline. Validate native display values in the fenced
    transaction and return immutable data/packets for the connection owner.
    """
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        inventory=_inventory(accounts,account_id,role_id,epoch)
        if (_resource_state(db,accounts,account_id,role_id,epoch) is None
                and _completed_chapter(db,accounts,account_id,role_id,epoch)):
            reconciled=task_master_card.reconcile_master_equipment(db,account_id,role_id,epoch,
                accounts.task_resources,accounts.master_card_rules,inventory,**_reward_rules(accounts))
            if reconciled.completion is not None:
                _project_completion(db,accounts,account_id,role_id,epoch,reconciled.completion,inventory)
        profile=_role_profile_transaction(db,accounts,account_id,role_id,epoch,inventory)
        resumed=task_master_card.master_resume_messages(db,account_id,role_id,epoch,
            accounts.task_resources,accounts.master_card_rules)
        return replace(profile,task_messages=resumed)


def _role_profile_transaction(db,accounts,account_id,role_id,epoch,inventory=None,inventory_snapshot=None):
    """One current naked growth + assets projection, validated before commit."""
    balance=read_experience(db,account_id,role_id)
    role=CommittedRoleState(role_id,epoch,balance.level,balance.experience)
    baseline=db.execute('SELECT 1 FROM role_attribute_baselines WHERE role_id=?',(role_id,)).fetchone()
    resources=_resource_state(db,accounts,account_id,role_id,epoch)
    if resources is not None:
        inventory=inventory or _inventory(accounts,account_id,role_id,epoch)
        snapshot=(inventory_snapshot if inventory_snapshot is not None
                  else inventory.immutable_snapshot_transaction(db,epoch=epoch))
        attributes=current_resource_profile(db,account_id,role_id,epoch,snapshot,
            equipment_rules=accounts.equipment_attribute_rules,resource_rules=accounts.resource_rules)
    else:
        attributes=attribute_snapshot_if_initialized(db,account_id,role_id,epoch)
    if attributes is None:
        if baseline:raise ValueError('Explicit attribute baseline is missing its current snapshot')
        return RoleLoadProfile(role)
    if not baseline:raise ValueError('Attribute snapshot is missing its explicit baseline')
    if accounts.growth_rules is None or accounts.attribute_rules is None:
        raise ValueError('Explicit role profile requires prepared growth and attribute rules')
    growth=read_growth(db,account_id,role_id)
    if (growth.policy!=accounts.growth_rules.revision
            or attributes.attributes.policy_revision!=accounts.attribute_rules.revision):
        raise ValueError('Role profile policy requires explicit migration')
    rules=accounts.equipment_attribute_rules
    if resources is None and read_equipment_attribute_basis(db,account_id,role_id,epoch,rules) is not None:
        inventory=inventory or _inventory(accounts,account_id,role_id,epoch)
        snapshot=(inventory_snapshot if inventory_snapshot is not None
                  else inventory.immutable_snapshot_transaction(db,epoch=epoch))
        attributes=current_equipment_projection(db,account_id,role_id,epoch,snapshot,rules)
    role_detail_vitals(role_id,attributes)
    return RoleLoadProfile(role,growth,attributes,growth_refresh(growth,attributes))


def _project_completion(db,accounts,account_id,role_id,epoch,completion,inventory):
    # TaskWorkflow computes bare growth. Replace its full map with the current
    # composition while the task/rewards/assets can all still roll back.
    profile=_role_profile_transaction(db,accounts,account_id,role_id,epoch,inventory)
    if profile.refresh is None:return completion
    return replace(completion,attributes=profile.attributes,growth_messages=(profile.refresh,))


def _reward_rules(accounts):
    return dict(growth_rules=accounts.growth_rules,attribute_rules=accounts.attribute_rules,
        currency_rules=accounts.currency_rules,pet_experience_rules=accounts.task_pet_experience_rules)


def _task_resource_rules(accounts):
    return dict(resource_rules=accounts.resource_rules,equipment_rules=accounts.equipment_attribute_rules)


def _completed_chapter(db,accounts,account_id,role_id,epoch):
    chapter=task_newbie_chapter.read_newbie_chapter(db,account_id,role_id,epoch,accounts.newbie_rules)
    return chapter if chapter is not None and chapter.phase=='completed' else None


def master_dialogue(accounts,account_id,role_id,epoch,proof,location,generation,now_ms):
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        chapter=_completed_chapter(db,accounts,account_id,role_id,epoch)
        if chapter is None:return None
        route=chapter.origin.route
        if (proof.npc_id,proof.address.map_id)!=(route.first_npc_id,route.home_map_id):return None
        _,state=load_task_state(db,account_id,role_id,epoch)
        if route.successor_task_id not in state.active:return None
        return task_master_card.open_master_dialogue(db,account_id,role_id,epoch,accounts.task_resources,
            accounts.master_card_rules,proof,location,generation=generation,now_ms=now_ms)


def master_authorize(accounts,account_id,role_id,epoch,ticket,intent,location,generation,now_ms):
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        return task_master_card.authorize_master_card(db,account_id,role_id,epoch,accounts.task_resources,
            accounts.master_card_rules,ticket,intent,location,generation=generation,now_ms=now_ms)


def cart_dialogue(accounts,account_id,role_id,epoch,proof,location,generation,now_ms,deadline_ms):
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        chapter=_completed_chapter(db,accounts,account_id,role_id,epoch)
        if chapter is None:return None
        origin=chapter.origin.route
        master=accounts.master_card_rules.routes[(origin.character_id,origin.school_id)]
        route=accounts.cart_resources.routes[master.cart_task_id]
        if (proof.npc_id,proof.address.map_id)!=(route.npc_id,route.map_id):return None
        _,state=load_task_state(db,account_id,role_id,epoch)
        if route.task_id not in state.active:return None
        return task_cart_dialogue.open_cart_dialogue_transaction(db,account_id,role_id,epoch,
            accounts.task_resources,accounts.cart_resources,proof,location,generation=generation,
            now_ms=now_ms,deadline_ms=deadline_ms)


def cart_authorize(accounts,account_id,role_id,epoch,ticket,intent,location,generation,now_ms):
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        accepted=task_cart_dialogue.authorize_cart_transfer_transaction(db,account_id,role_id,epoch,
            accounts.task_resources,accounts.cart_resources,ticket,intent,location,
            generation=generation,now_ms=now_ms)
        # This runtime currently implements normal character movement state0.
        # The approved policy rejects all other/unknown states, with no fallback.
        return task_cart_transfer.resolve_cart_transfer(accepted,accounts.cart_resources,
            accounts.cart_transfer_rules,movement_state=0)


def complete_cart_transfer(accounts,account_id,role_id,epoch,intent,receipt,inventory,generation,now_ms):
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        result=task_cart_transfer.complete_cart_transfer_transaction(db,account_id,role_id,epoch,
            accounts.task_resources,accounts.cart_resources,accounts.cart_transfer_rules,intent,receipt,inventory,
            generation=generation,now_ms=now_ms,movement_state=0,**_reward_rules(accounts),**_task_resource_rules(accounts))
        completion=_project_completion(db,accounts,account_id,role_id,epoch,result.completion,inventory)
        profile=_role_profile_transaction(db,accounts,account_id,role_id,epoch,inventory)
        messages=result.messages
        if profile.refresh is not None:
            messages=tuple(message for message in messages if message[0]!=profile.refresh[0])+(profile.refresh,)
        result=replace(result,completion=completion,messages=messages)
        # Scene and current full role display are both validated while the
        # durable target, task, rewards and receipts can still all roll back.
        body=scene_entry(result.target.position,reason=0)
        return CommittedCart(result,profile.role,body)


def master_choose(accounts,account_id,role_id,epoch,body,location,generation,now_ms,inventory):
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        result=task_master_card.choose_master_card(db,account_id,role_id,epoch,accounts.task_resources,
            accounts.master_card_rules,body,location,inventory,generation=generation,now_ms=now_ms,
            **_reward_rules(accounts),**_task_resource_rules(accounts))
        return _committed_master(db,accounts,account_id,role_id,epoch,inventory,result)


def _committed_master(db,accounts,account_id,role_id,epoch,inventory,result):
    profile=_role_profile_transaction(db,accounts,account_id,role_id,epoch,inventory)
    completion=result.completion
    if completion is not None:
        completion=_project_completion(db,accounts,account_id,role_id,epoch,completion,inventory)
    messages=result.messages
    if profile.refresh is not None:
        messages=tuple(message for message in messages if message[0]!=profile.refresh[0])+(profile.refresh,)
    result=replace(result,completion=completion,messages=messages)
    return CommittedMaster(result,profile.role)


def equip_role(accounts,account_id,role_id,epoch,inventory,kind,body,request_id):
    import struct
    from inventory import EQUIP_ITEM,UNEQUIP_ITEM
    if kind not in (EQUIP_ITEM,UNEQUIP_ITEM) or len(body)!=8:raise ValueError('Invalid equipment request')
    key,slot=struct.unpack('>ii',body)
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        resources=_resource_state(db,accounts,account_id,role_id,epoch)
        chapter=_completed_chapter(db,accounts,account_id,role_id,epoch)
        if resources is not None:
            event=(inventory.equip_transaction(db,key,slot,epoch,request_id) if kind==EQUIP_ITEM
                   else inventory.unequip_transaction(db,key,slot,epoch,request_id))
            _equipment_resource_transition(db,accounts,inventory,resources,
                'equip' if kind==EQUIP_ITEM else 'unequip',request_id,replayed=event.replayed)
            # The resource cap stage is complete BEFORE type59 can award XP or
            # alter naked growth. Its independent reconcile never equips again.
            if kind==EQUIP_ITEM and chapter is not None:
                result=task_master_card.reconcile_master_equipment(db,account_id,role_id,epoch,
                    accounts.task_resources,accounts.master_card_rules,inventory,event=event,
                    **_reward_rules(accounts),**_task_resource_rules(accounts))
            else:
                result=task_master_card.MasterResult(None,None,(),equipment_event=event)
            result=replace(result,messages=inventory.equipment_bag_messages(db,epoch)+result.messages)
            return _committed_master(db,accounts,account_id,role_id,epoch,inventory,result)
        if kind==EQUIP_ITEM:
            if chapter is not None:
                result=task_master_card.equip_master_transaction(db,account_id,role_id,epoch,
                    accounts.task_resources,accounts.master_card_rules,inventory,key,slot,request_id,
                    **_reward_rules(accounts),**_task_resource_rules(accounts))
            else:
                event=inventory.equip_transaction(db,key,slot,epoch,request_id)
                result=task_master_card.MasterResult(None,None,inventory.equipment_bag_messages(db,epoch),equipment_event=event)
        else:
            event=inventory.unequip_transaction(db,key,slot,epoch,request_id)
            result=task_master_card.MasterResult(None,None,inventory.equipment_bag_messages(db,epoch),equipment_event=event)
        return _committed_master(db,accounts,account_id,role_id,epoch,inventory,result)


def repair_role_equipment(accounts,inventory,intent):
    """The NPC transaction owns repair, fee, receipts and final display validation."""
    import npc_repairs
    def precommit(db,current_inventory,snapshot):
        return equipment_projection_messages(db,accounts,current_inventory,snapshot)
    return npc_repairs.repair(accounts,inventory,intent,precommit,
        resource_rules=accounts.resource_rules,equipment_rules=accounts.equipment_attribute_rules)


def npc_recover_resources(accounts,inventory,intent):
    """Both original inn request routes inject the same frozen dependencies."""
    import npc_recovery
    return npc_recovery.settle(accounts,inventory,intent,resource_rules=accounts.resource_rules,
        equipment_rules=accounts.equipment_attribute_rules)


def _inventory(accounts,account_id,role_id,epoch):
    return Inventory(accounts.leased(account_id,role_id,epoch),account_id,role_id,
        resource_rules=accounts.resource_rules,equipment_attribute_rules=accounts.equipment_attribute_rules)


def _resource_state(db,accounts,account_id,role_id,epoch):
    try:return read_role_resources(db,account_id,role_id,epoch,accounts.resource_rules)
    except ResourceNotInitialized:return None


def _growth_context(db,accounts,account_id,role_id,epoch,inventory=None):
    if _resource_state(db,accounts,account_id,role_id,epoch) is None:return None
    inventory=inventory or _inventory(accounts,account_id,role_id,epoch)
    return GrowthResourceContext(inventory.immutable_snapshot_transaction(db,epoch=epoch),
        accounts.equipment_attribute_rules,accounts.resource_rules)


def _synchronize_source(db,accounts,inventory,request_id,*,replayed):
    return synchronize_inventory_resource_source(db,inventory.account_id,inventory.role_id,inventory.epoch,
        inventory.immutable_snapshot_transaction(db),request_id,resource_rules=accounts.resource_rules,
        equipment_rules=accounts.equipment_attribute_rules,replayed=replayed)


def _equipment_resource_transition(db,accounts,inventory,before,cause,request_id,*,replayed):
    assets=inventory.immutable_snapshot_transaction(db)
    if replayed:
        current_resource_profile(db,inventory.account_id,inventory.role_id,inventory.epoch,assets,
            equipment_rules=accounts.equipment_attribute_rules,resource_rules=accounts.resource_rules)
        return
    totals=current_equipment_totals(db,inventory.account_id,inventory.role_id,inventory.epoch,
        assets,accounts.equipment_attribute_rules)
    plan=plan_resource_caps(before,resource_caps_from_projection(totals),cause,accounts.resource_rules)
    if plan.changed:
        key='equipment-resource:'+hashlib.sha256(request_id.encode()).hexdigest()
        apply_resource_transition(db,inventory.account_id,inventory.role_id,inventory.epoch,plan,key,
            rules=accounts.resource_rules,equipment_rules=accounts.equipment_attribute_rules)


def _require_unmigrated_operation(accounts,inventory,reason):
    with closing(inventory.accounts.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if _resource_state(db,accounts,inventory.account_id,inventory.role_id,inventory.epoch) is not None:
            raise ValueError(reason)


def _source_precommit(accounts,inventory,request_id):
    """Only immutable accepted command fields/rules enter the transaction hook."""
    account_id,role_id,epoch=inventory.account_id,inventory.role_id,inventory.epoch
    resource_rules,equipment_rules=accounts.resource_rules,accounts.equipment_attribute_rules
    def precommit(db,current_inventory,snapshot,*,replayed):
        if (current_inventory.account_id,current_inventory.role_id,current_inventory.epoch)!=(account_id,role_id,epoch):
            raise ValueError('Resource hook belongs to another inventory owner')
        synchronize_inventory_resource_source(db,account_id,role_id,epoch,snapshot,request_id,
            resource_rules=resource_rules,equipment_rules=equipment_rules,replayed=replayed)
        return ()
    return precommit


class _InventoryCommandPaid(Exception):
    """Unwind a raced fresh mutation before entering the current read path."""


def _inventory_command_paid(db,role_id,request_id,fingerprint):
    row=db.execute('SELECT fingerprint FROM role_inventory_commands WHERE role_id=? AND request_id=?',
        (role_id,request_id)).fetchone()
    if row is None:return False
    if row[0]!=fingerprint:raise ValueError('Inventory command ID reused with another intent')
    return True


def receive_inventory(accounts,inventory,kind,body,request_id,now_ms=None):
    """One durable accepted command, with current read-only replies on retry.

    The common receipt is written by the actual consumer's precommit hook,
    before its native encoding, so assets/source/receipt share one commit.
    Identical new wire clicks have different trusted owner IDs and execute.
    """
    if kind not in INVENTORY_CURRENT_MUTATION_TYPES:
        return inventory.receive(kind,body)
    if (type(kind) is not int or type(body) is not bytes or type(request_id) is not str
            or not 1<=len(request_id)<=160):
        raise ValueError('Accepted immutable inventory command identity required')
    fingerprint=hashlib.sha256(kind.to_bytes(4,'big')+body).hexdigest()
    account_id,role_id,epoch=inventory.account_id,inventory.role_id,inventory.epoch
    source_precommit=_source_precommit(accounts,inventory,request_id)

    def paid_messages():
        with closing(inventory.accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            snapshot=inventory.immutable_snapshot_transaction(db,epoch=epoch)
            if not _inventory_command_paid(db,role_id,request_id,fingerprint):return None
            source_precommit(db,inventory,snapshot,replayed=True)
            return list(inventory.current_mutation_messages_transaction(db,kind,body,epoch,now_ms))

    paid=paid_messages()
    if paid is not None:return paid

    def precommit(db,current_inventory,snapshot,*,replayed):
        if (current_inventory.account_id,current_inventory.role_id,current_inventory.epoch)!=(account_id,role_id,epoch):
            raise ValueError('Inventory command belongs to another owner')
        # BEGIN IMMEDIATE in the consumer protects this final receipt check.
        # A raced existing command must roll its second mutation back first.
        if _inventory_command_paid(db,role_id,request_id,fingerprint):raise _InventoryCommandPaid()
        if replayed:raise ValueError('Generic fresh command has an unexpected domain receipt')
        source_precommit(db,current_inventory,snapshot,replayed=False)
        db.execute('INSERT INTO role_inventory_commands VALUES(?,?,?,?)',
            (role_id,request_id,fingerprint,str(epoch)))
        return ()

    try:return inventory.receive(kind,body,precommit)
    except _InventoryCommandPaid:
        paid=paid_messages()
        if paid is None:raise ValueError('Paid inventory command receipt disappeared') from None
        return paid


def npc_asset_operation(accounts,inventory,intent,operation):
    return operation(accounts,inventory,intent,_source_precommit(accounts,inventory,intent.service.request_id))


def depot_operation(accounts,inventory,command,kind,body):
    return npc_gameplay.depot_operation(accounts,inventory,command,kind,body,
        _source_precommit(accounts,inventory,command.request_id))


def equipment_projection_messages(db,accounts,inventory,snapshot):
    """Trusted caller-transaction hook for repair or wear; no commit or send.

    Only the immutable current inventory may enter the projection. Errors must
    unwind the asset mutation too; callers cannot invoke this after committing.
    Legacy unknown profiles retain their explicit compatibility path.
    """
    profile=_role_profile_transaction(db,accounts,inventory.account_id,inventory.role_id,inventory.epoch,
        inventory,snapshot)
    return () if profile.refresh is None else (profile.refresh,)


def initialize_role_wallet(accounts,account_id,role_id,epoch,baseline,origin):
    """Explicit trusted role-owner operation; never invoked by client packets."""
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if origin=='new_restoration_role':
            row=db.execute('SELECT origin,wallet_policy FROM role_restoration_origins WHERE role_id=?',(role_id,)).fetchone()
            if not row or tuple(row)!=(origin,accounts.currency_rules.revision):
                raise ValueError('No explicit new-role creation provenance')
        initialize_wallet(db,account_id,role_id,epoch,baseline,origin,accounts.currency_rules)
        return read_wallet(db,account_id,role_id,epoch,accounts.currency_rules)


def wallet_snapshot(accounts,account_id,role_id,epoch):
    """Current authority for login display, or None for an uninitialized wallet.

    This never creates/migrates a wallet and never reuses a historical receipt.
    Policy, ownership and lease errors propagate instead of becoming zeroes.
    """
    with closing(accounts.leased(account_id,role_id,epoch).connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        try:
            return read_wallet(db,account_id,role_id,epoch,accounts.currency_rules)
        except WalletNotInitialized:
            return None

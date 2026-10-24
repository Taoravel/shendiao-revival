"""Opt-in native-client training adapter; visual presentation still needs QA.

Use only for local training. Numeric balance comes from the planner's baseline.
Wire layouts and basic commands are native-verified; animation needs live QA.
"""
import json
import struct
import uuid
import time
from dataclasses import dataclass, asdict, replace
from collections import deque
from pathlib import Path
from battle import Battle, Fighter, Command, Skill
from battle_loadout import OwnedBattlePet, PetTemplate, CombatResources
import battle_protocol as p

ROOT = Path(__file__).parent


@dataclass(frozen=True)
class TrainingRules:
    revision: str
    actor: Fighter
    enemy: Fighter
    timeout: int
    max_rounds: int
    skills: tuple = ()
    pet_policy: object = None
    owner_escape_with_pets: bool = False
    pet_templates: tuple = ()


@dataclass(frozen=True)
class PetFixturePolicy:
    template_id: int
    min_owner_level: int
    min_pet_level: int
    shape: int
    hp: int
    mp: int
    attack: int
    defense: int
    speed: int


@dataclass(frozen=True)
class TrainingPet:
    """Trusted role-owner snapshot, never decoded from a client assertion.

    The role owner verifies real instance ownership/selection/version before
    supplying this message. Battle repeats identity/eligibility validation.
    """
    role_id: int
    key: int
    template_id: int
    inventory_revision: int
    name: str
    level: int
    position: int
    selected: bool
    fixture_authorized: bool


def load_training_rules(path=ROOT/'design/recovery-baseline.json'):
    """Startup-only configuration I/O; pass the frozen result to battle owners."""
    baseline=json.loads(Path(path).read_text(encoding='utf-8'))
    rules=baseline['training_battle'];timing=baseline['historical_battle_reference']
    damage=rules['damage']
    if (damage['formula']!='max(1, attack - defense)' or damage['minimum']!=1
            or damage['defending_multiplier']!=0.5 or damage['rounding']!='floor_before_minimum'
            or rules['order']!='speed_desc_then_battle_position_asc'
            or rules['random_damage'] or rules['critical_hits'] or rules['evasion']
            or rules['currency_reward'] or rules['item_rewards']
            or timing['timeout_action']!='physical_attack'):
        raise ValueError('Training rules require a matching battle implementation')
    actor=rules['missing_actor_stats_only'];enemy=rules['enemy']
    escape=rules.get('owner_escape')
    follow_on_escape=False
    if escape:
        if (escape['scope']!='local_training_only' or escape['on_success']!=
                'withdraw caster and all pets owned by that caster from this battle atomically'):
            raise ValueError('Training escape policy requires a matching implementation')
        follow_on_escape=True
    skills=[]
    overrides=baseline.get('training_skill_overrides',{})
    for key,values in overrides.items():
        if not key.isdigit():continue
        skills.append(Skill(int(key),values['mp_cost_per_command'],values['flat_power'],False,
                            values['max_enemy_targets'],values['attack_multiplier_numerator'],
                            values['attack_multiplier_denominator']))
    fixture=baseline.get('training_pet_fixture')
    pet_policy=None
    pets=json.loads((ROOT/'catalogs/knight.gsp.pet.cpetattr.json').read_text(encoding='utf-8'))
    pet_templates=tuple(PetTemplate(int(row['attributes']['id']),int(row['attributes']['modelid']),
                                   int(row['attributes']['takelevel']),int(row['attributes']['uselevel']))
                        for row in pets)
    if fixture:
        original=next(row['attributes'] for row in pets if int(row['attributes']['id'])==fixture['template_id'])
        pet_policy=PetFixturePolicy(fixture['template_id'],max(int(original['uselevel']),fixture['required_owner_level']),
            fixture['required_pet_level'],int(original['modelid']),fixture['hp'],fixture['mp'],
            fixture['attack'],fixture['defense'],fixture['speed'])
    return TrainingRules(baseline['revision'],Fighter(1,0,max_hp=actor['hp'],**actor),
                         Fighter(21,1,max_hp=enemy['hp'],**enemy),
                         timing['command_timeout_seconds'],timing['max_rounds'],tuple(skills),pet_policy,
                         follow_on_escape,pet_templates)


# Imported before the server's network loop starts. No per-battle disk access.
DEFAULT_RULES=load_training_rules()


@dataclass(frozen=True)
class BattleFinished:
    battle_id: str
    settlement_id: str
    role_id: int
    winner_side: int
    won: bool
    rounds: int
    revision: str
    login_epoch: str
    snapshot_version: int
    scope: str = 'local_training_only'
    currency_reward: int = 0
    item_rewards: tuple = ()
    task_event_eligible: bool = False
    outcome: str = 'completed'
    combat_resources: tuple = ()


class TrainingBattle:
    """Mutable state belongs to self.id; callers serialize commands per battle ID.

    This class owns no network/SQLite objects and creates no worker/queue. Hosts
    must route on their battle partition and send returned logical packets from
    the destination connection owner. It is not a distributed actor scheduler.
    """
    def __init__(self, role, actor_stats=None, clock=None, rules=DEFAULT_RULES,
                 login_epoch='', snapshot_version=0,authorized_skills=(),pet=None):
        stats={k:getattr(rules.actor,k) for k in ('hp','mp','attack','defense','speed')}
        if rules.actor.max_mp is not None:stats['max_mp']=rules.actor.max_mp
        stats.update(actor_stats or {})
        stats.setdefault('max_hp',stats['hp'])
        if type(authorized_skills) is not tuple or any(type(x) is not int for x in authorized_skills):
            raise ValueError('Immutable explicit skill authorization required')
        allowed={s.id:s for s in rules.skills}
        if len(set(authorized_skills))!=len(authorized_skills) or any(s not in allowed for s in authorized_skills):
            raise ValueError('Unknown training skill authorization')
        stats['skills']=authorized_skills
        self.authorized_skills=authorized_skills
        self.role={key:role[key] for key in ('id','name','shape','level')}
        self.id=uuid.uuid4().hex
        self.revision=rules.revision
        self.login_epoch=login_epoch
        self.snapshot_version=snapshot_version
        self.clock=clock or time.monotonic
        self.timeout=rules.timeout
        self.deadline=self.clock()+self.timeout
        fighters=[Fighter(1,0,**stats),rules.enemy]
        self.pet=pet
        self.pet_shape=None
        if isinstance(pet,OwnedBattlePet):
            template=next((row for row in rules.pet_templates if row.id==pet.template_id),None)
            f=pet.stats
            if (not isinstance(f,Fighter) or pet.role_id!=role['id'] or not pet.selected or pet.key<1 or pet.inventory_revision<0
                    or pet.growth_version<0 or not pet.growth_revision
                    or not 2<=pet.position<=14 or f.id!=pet.position or f.side!=0 or f.skills
                    or template is None or pet.shape!=template.shape
                    or role['level']<max(template.take_level,template.use_level)
                    or pet.level<1 or not pet.name or len(pet.name)>8 or not 0<=f.mp<=pet.max_mp):
                raise ValueError('Pet requires owned eligible versioned combat snapshot')
            self.pet_shape=pet.shape
            fighters.append(replace(f,max_mp=pet.max_mp))
        elif pet is not None:
            policy=rules.pet_policy
            if (not isinstance(pet,TrainingPet) or policy is None or not pet.fixture_authorized or not pet.selected
                    or pet.role_id!=role['id'] or pet.template_id!=policy.template_id
                    or min(pet.key,pet.inventory_revision)<1 or not 2<=pet.position<=14
                    or role['level']<policy.min_owner_level or pet.level<policy.min_pet_level
                    or not pet.name or len(pet.name)>8):
                raise ValueError('Pet requires owned selected eligible explicit fixture snapshot')
            self.pet_shape=policy.shape
            fighters.append(Fighter(pet.position,0,policy.hp,policy.hp,policy.mp,
                                    policy.attack,policy.defense,policy.speed))
        followers=((1,pet.position),) if pet is not None and rules.owner_escape_with_pets else ()
        self.battle=Battle(fighters,skills=tuple(allowed[s] for s in authorized_skills),max_rounds=rules.max_rounds,
                           escape_followers=followers)
        self._max_mp={f.id:f.max_mp for f in self.battle.fighters}
        self._result=None
        self.rejections=deque(maxlen=64)
        self.last_rejection=''

    @property
    def result(self):
        return asdict(self._result) if self._result is not None else None

    def finished(self):
        """Immutable message for the role owner; retry with settlement_id.

        Training rewards are zero. No durable settlement or task completion is
        implied by returning this message; the integration owns those writes.
        """
        return self._result

    def opening(self):
        # Fighter type/side bindings remain provisional. Basic operations now
        # follow the native sender/button evidence in research_battle_commands.
        by_id={f.id:f for f in self.battle.fighters}
        player,enemy=by_id[1],by_id[21]
        records=[
                    p.fighter(1,self.role['id'],self.role['shape'],self.role['name'],1,player.hp,self.role['level'],max_hp=player.max_hp),
                    p.fighter(21,20001,6013,'训练小灰狗',3,enemy.hp)]
        if self.pet:
            f=by_id[self.pet.position]
            records.append(p.fighter(f.id,self.pet.key,self.pet_shape,self.pet.name,2,f.hp,self.pet.level,max_hp=f.max_hp))
        packets=[]
        # Domain authorization does not authorize replacing learned-skill UI.
        # Native flag/restore semantics and a complete original display snapshot
        # are not available yet; baseline .3 therefore keeps injection disabled.
        packets.extend(((p.BATTLE_START,p.battle_start()),(p.ADD_FIGHTERS,p.add_fighters(records))))
        if self.authorized_skills or self.pet:packets.extend(self._vitals())
        packets.append((p.ROUND_START,p.round_start(self.timeout)))
        return packets

    def _vitals(self):
        by_id={f.id:f for f in self.battle.fighters}
        actor=by_id[1]
        packets=[(p.ROLE_INIT_ATTRS,p.float_map({60:actor.hp,70:actor.mp,140:actor.max_hp,150:self._max_mp[1]}))]
        if self.pet:
            actor=by_id[self.pet.position]
            packets.append((p.PET_INIT_ATTRS,p.float_map({60:actor.hp,70:actor.mp,140:actor.max_hp,150:self._max_mp[actor.id]})))
        return packets

    def _resources(self):
        by_id={f.id:f for f in self.battle.fighters}
        actor=by_id[1]
        snapshots=[CombatResources('role',self.role['id'],1,self.snapshot_version,
                    actor.hp,actor.max_hp,actor.mp,actor.max_mp,1 in self.battle.escaped)]
        if self.pet:
            pet=self.pet
            actor=by_id[pet.position]
            real=isinstance(pet,OwnedBattlePet)
            snapshots.append(CombatResources('pet' if real else 'pet_fixture',pet.key,pet.position,
                pet.growth_version if real else 0,actor.hp,actor.max_hp,actor.mp,actor.max_mp,
                actor.id in self.battle.escaped,pet.inventory_revision,pet.growth_revision if real else ''))
        return tuple(snapshots)

    def _resolve_if_ready(self):
        by_id={f.id:f for f in self.battle.fighters}
        humans={1} | ({self.pet.position} if self.pet else set())
        if any(i in humans for i in self.battle.pending):return []
        for actor in self.battle.pending:
            targets=[f for f in self.battle.fighters if f.side!=by_id[actor].side and f.hp>0]
            if targets:self.battle.submit(self.battle.round,Command(actor,'attack',targets[0].id))
        events=self.battle.resolve()
        scripts=[]
        for e in events:
            op={'attack':p.ATTACK,'defend':p.DEFEND,'escape':p.ESCAPE,'skill':p.SKILL}[e.kind]
            targets=[p.TargetResult(hit.target,((p.HP_CHANGE,hit.hp_change),)) for hit in e.impacts]
            scripts.append(((e.actor,0,-e.mp_change,0,op,e.skill,0,0,0),targets))
        packets=[(p.ROUND_SCRIPT,p.round_script(scripts))]
        if self.authorized_skills or self.pet:packets.extend(self._vitals())
        return packets

    def receive(self, kind, body):
        self.last_rejection=''
        if kind not in p.BATTLE_TYPES: return None
        if self.battle.phase=='ended': return []
        try:
            if kind==p.SEND_ACTION:
                operation,target,operation_id,is_role,is_auto=p.parse_action(body)
                if self.battle.phase!='commands': return [] # duplicate during playback
                if is_role not in (0,1) or is_auto not in (0,1) or (is_role==0 and self.pet is None):
                    raise ValueError('Training requires an authorized player or pet')
                binding={p.ATTACK:'attack',p.DEFEND:'defend',p.ESCAPE:'escape',p.SKILL:'skill'}
                command=binding.get(operation)
                if (command is None or (command!='skill' and operation_id)
                        or (is_role==0 and command not in ('attack','defend'))):
                    raise ValueError('Training supports attack, defend and escape only')
                actor=1 if is_role else self.pet.position
                if is_auto and target==0 and command=='attack':
                    # Native automatic sender 0x1195aa0 clears the cached target.
                    # Resolve only this sentinel against authoritative live foes.
                    side=next(f.side for f in self.battle.fighters if f.id==actor)
                    target=next((f.id for f in self.battle.fighters
                        if f.side!=side and f.hp>0 and f.id not in self.battle.escaped),0)
                self.battle.submit(self.battle.round,Command(actor,command,target if command in ('attack','skill') else 0,
                                                          operation_id if command=='skill' else 0))
                return self._resolve_if_ready()
            p.parse_play_end(body)
            if self.battle.phase!='playback': return []
            current=self.battle.round
            self.battle.acknowledge(current)
            if self.battle.phase=='ended':
                outcome=('escape' if 1 in self.battle.escaped else
                         'victory' if self.battle.winner==0 else
                         'defeat' if self.battle.winner==1 else 'draw')
                self._result=BattleFinished(self.id,'training:'+self.id,self.role['id'],
                    self.battle.winner,self.battle.winner==0 and outcome!='escape',current,self.revision,
                    self.login_epoch,self.snapshot_version,outcome=outcome,combat_resources=self._resources())
                return [(p.BATTLE_END,p.battle_end())]
            self.deadline=self.clock()+self.timeout
            return [(p.SERVER_PLAY_END,struct.pack('>i',current)),
                    (p.ROUND_START,p.round_start(self.timeout))]
        except ValueError as exc:
            # Bad gameplay input is rejected without disconnecting the world.
            self.rejections.append(str(exc))
            self.last_rejection=str(exc)
            return []

    def tick(self):
        if self.battle.phase=='commands' and self.clock()>=self.deadline:
            humans={1} | ({self.pet.position} if self.pet else set())
            enemies=[f.id for f in self.battle.fighters if f.side==1 and f.hp>0]
            for actor in self.battle.pending:
                if actor in humans and enemies:self.battle.submit(self.battle.round,Command(actor,'attack',enemies[0]))
            return self._resolve_if_ready()
        return []

    def close(self):
        self.battle.cancel()

"""Dedicated AI8001 quest engine; no training/wild result or asset writes.

The role host supplies a real Participant and a registered original definition.
Admission, NPC authority, persistence and delivery remain the host's duties.
Only pure Battle arithmetic and native battle codec are shared with other modes.
"""
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import struct
from uuid import uuid4
from battle import Battle, Command, Fighter
from battle_loadout import CombatResources, OwnedBattlePet, PetTemplate
from training_battle import BattleFinished
import battle_protocol as p


POLICY_SHA256 = '2cbbe2cafe3151e49f21a4ec35dab0dd9d4aa9dca82b4b28016dfcb3c13a3c56'


@dataclass(frozen=True)
class TaskPveRules:
    revision: str
    enabled_task_ids: frozenset
    ai_id: int
    map_id: int
    npc_id: int
    enemy: Fighter
    enemy_template: int
    enemy_shape: int
    enemy_name: str
    enemy_level: int
    background: int
    music: int
    timeout: int
    playback_timeout_ms: int
    max_rounds: int
    pet_templates: tuple = ()


def load_task_pve_rules(path, *, pet_templates=()):
    """Startup only. Bind exactly the approved recipe, including its limits.

    The byte fingerprint deliberately rejects silently edited design policies.
    Pet eligibility comes from an explicit frozen original catalog supplied by
    the host, rather than training fixture statistics or per-battle disk reads.
    """
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != POLICY_SHA256:
        raise ValueError('Task PVE recipe differs from the reviewed implementation contract')
    if (type(pet_templates) is not tuple
            or any(not isinstance(row, PetTemplate) for row in pet_templates)
            or len({row.id for row in pet_templates}) != len(pet_templates)):
        raise ValueError('Explicit immutable original pet catalog required')
    recipe = json.loads(raw)
    enemy = recipe['enemy']
    return TaskPveRules(recipe['revision'], frozenset(recipe['enabled_task_ids']),
        recipe['original_ai_id'], recipe['map_template_id'], recipe['npc_id'],
        Fighter(enemy['position'], enemy['side'], enemy['hp'], enemy['max_hp'],
            enemy['mp'], enemy['physical_attack'], enemy['physical_defense'],
            enemy['speed'], max_mp=enemy['max_mp']),
        enemy['template_id'], enemy['shape_id'], enemy['name'], enemy['level'],
        recipe['background'], recipe['music'], recipe['command_timeout_seconds'],
        recipe['playback_timeout_ms'], recipe['max_rounds'], pet_templates)


def _valid_fighter(fighter, position):
    if not isinstance(fighter, Fighter):
        return False
    values = (fighter.id, fighter.side, fighter.hp, fighter.max_hp, fighter.mp,
              fighter.max_mp, fighter.attack, fighter.defense, fighter.speed)
    return (all(type(value) is int for value in values)
        and fighter.id == position and fighter.side == 0
        and 0 < fighter.hp <= fighter.max_hp <= 0x7fffffff
        and 0 <= fighter.mp <= fighter.max_mp <= 0x7fffffff
        and all(0 <= value <= 0x7fffffff for value in values[-3:]))


class TaskPveBattle:
    """Public engine Interface used by the per-battle BattleOwner scheduler.

    No skill ledger projection, resource healing, task reward, Session or DB
    access occurs here. Actual terminal resources precede the host's explicit
    dream recovery and task settlement transaction.
    """
    def __init__(self, participant, rules, definition, *, clock):
        if (not isinstance(rules, TaskPveRules)
                or definition.task_id not in rules.enabled_task_ids
                or (definition.ai_id, definition.map_id, definition.npc_id)
                    != (rules.ai_id, rules.map_id, rules.npc_id)
                or not _valid_fighter(participant.stats, 1)
                or any(type(value) is not int or value < 1 for value in
                    (participant.role_id, participant.login_epoch,
                     participant.connection_generation, participant.attribute_version,
                     participant.shape, participant.level))
                or not isinstance(participant.name, str) or not 1 <= len(participant.name) <= 64
                or type(participant.authorized_skills) is not tuple
                or any(type(value) is not int or value < 1 for value in participant.authorized_skills)
                or len(set(participant.authorized_skills)) != len(participant.authorized_skills)):
            raise ValueError('Registered quest and real versioned combat participant required')
        self.participant, self.rules, self.definition = participant, rules, definition
        self.clock = clock
        self.id = uuid4().hex
        # This battle grants no skill capability. Preserve the role's complete
        # learned ledger elsewhere and never send a manufactured empty UI map.
        fighters = [replace(participant.stats, skills=()), rules.enemy]
        pet = participant.pet
        if pet is not None:
            template = next((row for row in rules.pet_templates
                             if row.id == getattr(pet, 'template_id', None)), None)
            if (not isinstance(pet, OwnedBattlePet) or type(pet.selected) is not bool or not pet.selected
                    or pet.role_id != participant.role_id or template is None
                    or not 2 <= pet.position <= 14 or not _valid_fighter(pet.stats, pet.position)
                    or pet.stats.skills or pet.shape != template.shape
                    or participant.level < max(template.take_level, template.use_level)
                    or any(type(value) is not int or value < minimum for value, minimum in
                        ((pet.key, 1), (pet.inventory_revision, 0), (pet.growth_version, 0), (pet.level, 1)))
                    or not isinstance(pet.name, str) or not 1 <= len(pet.name) <= 8
                    or not isinstance(pet.growth_revision, str) or not pet.growth_revision
                    or pet.max_mp != pet.stats.max_mp):
                raise ValueError('Actual eligible owned pet with complete versions required')
            fighters.append(pet.stats)
        self.battle = Battle(fighters, max_rounds=rules.max_rounds,
            escape_followers=((1, pet.position),) if pet else ())
        self.deadline = clock() + rules.timeout
        self.last_rejection = ''
        self._opened = False
        self._result = None

    def opening(self):
        if self._opened or self.battle.phase == 'ended':
            return []
        actor, rules = self.participant, self.rules
        by_id = {fighter.id: fighter for fighter in self.battle.fighters}
        own, enemy = by_id[1], by_id[21]
        roster = [p.fighter(1, actor.role_id, actor.shape, actor.name, 1,
                           own.hp, actor.level, max_hp=own.max_hp),
                  p.fighter(21, rules.enemy_template, rules.enemy_shape, rules.enemy_name, 3,
                           enemy.hp, rules.enemy_level, max_hp=enemy.max_hp)]
        if actor.pet:
            pet = actor.pet
            fighter = by_id[pet.position]
            roster.append(p.fighter(pet.position, pet.key, pet.shape, pet.name, 2,
                                   fighter.hp, pet.level, max_hp=fighter.max_hp))
        self._opened = True
        self.deadline = self.clock() + rules.timeout
        return [(p.BATTLE_START, p.battle_start(background=rules.background, music=rules.music)),
                (p.ADD_FIGHTERS, p.add_fighters(roster)), *self._vitals(),
                (p.ROUND_START, p.round_start(rules.timeout))]

    def _vitals(self):
        by_id = {fighter.id: fighter for fighter in self.battle.fighters}
        def attributes(fighter):
            return p.float_map({60: fighter.hp, 70: fighter.mp,
                                140: fighter.max_hp, 150: fighter.max_mp})
        messages = [(p.ROLE_INIT_ATTRS, attributes(by_id[1]))]
        if self.participant.pet:
            messages.append((p.PET_INIT_ATTRS, attributes(by_id[self.participant.pet.position])))
        return messages

    def _resources(self):
        actor = self.participant
        by_id = {fighter.id: fighter for fighter in self.battle.fighters}
        own = by_id[1]
        result = [CombatResources('role', actor.role_id, 1, actor.attribute_version,
            own.hp, own.max_hp, own.mp, own.max_mp, 1 in self.battle.escaped)]
        if actor.pet:
            pet, own = actor.pet, by_id[actor.pet.position]
            result.append(CombatResources('pet', pet.key, pet.position, pet.growth_version,
                own.hp, own.max_hp, own.mp, own.max_mp, pet.position in self.battle.escaped,
                pet.inventory_revision, pet.growth_revision))
        return tuple(result)

    def _terminal(self, outcome, winner):
        actor = self.participant
        return BattleFinished(self.id, 'task-battle:' + self.id, actor.role_id,
            winner, outcome == 'victory', self.battle.round, self.rules.revision,
            actor.login_epoch, actor.attribute_version, scope='task_quest_v1',
            task_event_eligible=True, outcome=outcome, combat_resources=self._resources())

    def _resolve(self):
        humans = {1} | ({self.participant.pet.position} if self.participant.pet else set())
        if any(position in humans for position in self.battle.pending):
            return []
        living = [fighter for fighter in self.battle.fighters
                  if fighter.side == 0 and fighter.hp > 0 and fighter.id not in self.battle.escaped]
        target = next((fighter for fighter in living if fighter.id == 1),
                      min(living, key=lambda fighter: fighter.id) if living else None)
        if target is not None:
            for position in self.battle.pending:
                self.battle.submit(self.battle.round, Command(position, 'attack', target.id))
        events = self.battle.resolve()
        executions = []
        for event in events:
            operation = {'attack': p.ATTACK, 'defend': p.DEFEND, 'escape': p.ESCAPE}[event.kind]
            impacts = [p.TargetResult(hit.target, ((p.HP_CHANGE, hit.hp_change),))
                       for hit in event.impacts]
            executions.append(((event.actor, 0, 0, 0, operation, 0, 0, 0, 0), impacts))
        return [(p.ROUND_SCRIPT, p.round_script(executions)), *self._vitals()]

    def receive(self, kind, body):
        self.last_rejection = ''
        if not self._opened:
            raise ValueError('Quest battle has not opened')
        if self.battle.phase == 'ended':
            return []
        try:
            if kind == p.SEND_ACTION:
                operation, target, operation_id, is_role, is_auto = p.parse_action(body)
                if self.battle.phase != 'commands':
                    return []
                if (is_role not in (0, 1) or is_auto not in (0, 1) or operation_id
                        or operation not in (p.ATTACK, p.DEFEND, p.ESCAPE)
                        or not is_role and (self.participant.pet is None or operation == p.ESCAPE)):
                    raise ValueError('This quest permits ordinary attack, defend and role escape only')
                position = 1 if is_role else self.participant.pet.position
                command = {p.ATTACK: 'attack', p.DEFEND: 'defend', p.ESCAPE: 'escape'}[operation]
                if is_auto and not target and operation == p.ATTACK:
                    target = next((fighter.id for fighter in self.battle.fighters
                        if fighter.side == 1 and fighter.hp > 0 and fighter.id not in self.battle.escaped), 0)
                # Defend/escape native senders use target0; refuse malformed
                # targets rather than discarding client-supplied parameters.
                self.battle.submit(self.battle.round, Command(position, command, target))
                return self._resolve()
            if kind != p.CLIENT_PLAY_END:
                return []
            p.parse_play_end(body)
            if self.battle.phase != 'playback':
                return []
            current = self.battle.round
            self.battle.acknowledge(current)
            if self.battle.phase == 'ended':
                outcome = ('escape' if 1 in self.battle.escaped else
                           'victory' if self.battle.winner == 0 else
                           'defeat' if self.battle.winner == 1 else 'draw')
                self._result = self._terminal(outcome, self.battle.winner)
                return [(p.BATTLE_END, p.battle_end())]
            self.deadline = self.clock() + self.rules.timeout
            return [(p.SERVER_PLAY_END, struct.pack('>i', current)),
                    (p.ROUND_START, p.round_start(self.rules.timeout))]
        except ValueError as error:
            self.last_rejection = str(error)
            return []

    def tick(self):
        if not self._opened or self.battle.phase != 'commands' or self.clock() < self.deadline:
            return []
        humans = {1} | ({self.participant.pet.position} if self.participant.pet else set())
        for position in self.battle.pending:
            if position in humans:
                self.battle.submit(self.battle.round, Command(position, 'attack', 21))
        return self._resolve()

    def finished(self):
        return self._result

    def close(self):
        if self.battle.phase != 'ended':
            self.battle.cancel()

    def abort_finished(self, reason):
        """Actual host abort carries current losses and never grants victory."""
        if not isinstance(reason, str) or not 1 <= len(reason) <= 128:
            raise ValueError('Explicit bounded abort reason required')
        if self._result is not None:
            return self._result
        if self.battle.phase != 'ended':
            raise ValueError('Host must really close this battle before producing an abort')
        self._result = self._terminal('draw', -1)
        return self._result

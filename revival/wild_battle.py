"""Single-enemy native battle Adapter; scheduler and settlement are host-owned."""
from dataclasses import replace
from battle import Fighter
from training_battle import TrainingBattle, BattleFinished
from battle_loadout import CombatResources
import battle_protocol as p


class WildBattle:
    """Compose existing command/playback engine with an original monster model.

    A real versioned role snapshot is mandatory: never give training fallback
    stats to an online role. Pet admission follows the existing owned-pet rules.
    Host serializes per battle ID on a bounded mailbox, fences leases, applies
    playback timeout, and delivers logical messages from the connection owner.
    """
    def __init__(self, participant, ticket, rules, *, clock):
        loc = ticket.location
        if (participant.role_id != loc.role_id or participant.login_epoch != loc.login_epoch
                or min(participant.attribute_version, participant.connection_generation,
                       participant.level, participant.shape) < 1
                or not isinstance(participant.stats, Fighter)
                or ticket.enemy.id != 21 or ticket.enemy.side != 1):
            raise ValueError('Versioned owned role combat snapshot required')
        self.ticket = ticket
        self.participant = participant
        stats = {k:getattr(participant.stats, k) for k in ('hp','max_hp','mp','attack','defense','speed')}
        if participant.stats.max_mp is not None: stats['max_mp'] = participant.stats.max_mp
        # Numeric/identity changes stay local; training configuration is frozen.
        battle_rules = replace(rules, revision=ticket.revision, enemy=ticket.enemy)
        self._engine = TrainingBattle(dict(id=participant.role_id, name=participant.name,
            shape=participant.shape, level=participant.level), actor_stats=stats, clock=clock,
            rules=battle_rules, login_epoch=participant.login_epoch,
            snapshot_version=participant.attribute_version, authorized_skills=participant.authorized_skills,
            pet=participant.pet)
        self.id = self._engine.id
        self._opened = False

    @property
    def battle(self): return self._engine.battle

    @property
    def last_rejection(self): return self._engine.last_rejection

    def abort_finished(self,reason):
        """Trusted abort keeps current resources and grants no victory reward."""
        return aborted_result(self.participant,self.ticket,self.id,self.battle.fighters,self.battle.round)

    def opening(self):
        if self._opened or self.battle.phase == 'ended': return []
        records = list(self._engine.opening())
        fighters = {f.id:f for f in self.battle.fighters}
        role, enemy = fighters[1], fighters[21]
        participant, monster = self.participant, self.ticket.monster
        roster = [p.fighter(1,participant.role_id,participant.shape,participant.name,1,
                           role.hp,participant.level,max_hp=role.max_hp),
                  p.fighter(21,monster.template_id,monster.shape_id,monster.name,3,
                            enemy.hp,self.ticket.level,max_hp=enemy.max_hp)]
        if participant.pet:
            pet = participant.pet; f = fighters[pet.position]
            roster.append(p.fighter(f.id,pet.key,self._engine.pet_shape,pet.name,2,
                                   f.hp,pet.level,max_hp=f.max_hp))
        records = [(kind,p.add_fighters(roster) if kind == p.ADD_FIGHTERS else
                    p.battle_start(background=self.ticket.background, music=1) if kind == p.BATTLE_START else body)
                   for kind,body in records]
        self._opened = True
        return records

    def receive(self, kind, body):
        if not self._opened: raise ValueError('Battle not opened')
        return self._engine.receive(kind, body)

    def tick(self):
        return self._engine.tick() if self._opened else []

    def close(self): self._engine.close()

    def finished(self):
        result = self._engine.finished()
        return (replace(result, settlement_id='wild:'+self.id, scope='wild_encounter_v1')
                if result is not None else None)


def combat_resources(participant,fighters):
    by_id={f.id:f for f in fighters};actor=by_id[1]
    resources=[CombatResources('role',participant.role_id,1,participant.attribute_version,
        actor.hp,actor.max_hp,actor.mp,actor.max_mp,False)]
    if participant.pet:
        pet=participant.pet;actor=by_id[pet.position]
        resources.append(CombatResources('pet',pet.key,pet.position,pet.growth_version,
            actor.hp,actor.max_hp,actor.mp,actor.max_mp,False,pet.inventory_revision,pet.growth_revision))
    return tuple(resources)


def aborted_result(participant,ticket,battle_id,fighters,round_number):
    return BattleFinished(battle_id,'wild:'+battle_id,participant.role_id,-1,False,round_number,
        ticket.revision,participant.login_epoch,participant.attribute_version,scope='wild_encounter_v1',
        outcome='draw',combat_resources=combat_resources(participant,fighters))

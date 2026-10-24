"""Deterministic local restoration rules, NOT recovered original server formulas.

The public seam is Battle.submit -> resolve -> acknowledge. No socket, account,
inventory or reward writes occur here. All arithmetic uses explicit design values.
"""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Fighter:
    id: int
    side: int
    hp: int = 100
    max_hp: int = 100
    mp: int = 100
    attack: int = 25
    defense: int = 5
    speed: int = 10
    skills: tuple = ()
    max_mp: int | None = None


@dataclass(frozen=True)
class Skill:
    id: int
    mp: int
    power: int
    healing: bool = False
    max_targets: int = 1
    attack_numerator: int = 1
    attack_denominator: int = 1


@dataclass(frozen=True)
class Command:
    actor: int
    kind: str
    target: int = 0
    skill: int = 0


@dataclass(frozen=True)
class Event:
    actor: int
    kind: str
    target: int = 0
    hp_change: int = 0
    mp_change: int = 0
    skill: int = 0
    dead: bool = False
    impacts: tuple = ()


@dataclass(frozen=True)
class Impact:
    target: int
    hp_change: int
    dead: bool


class Battle:
    """One battle; each active fighter chooses once, then playback must finish.

    Public state is immutable snapshots. Invalid submissions do not consume a turn.
    The host supplies AI commands through the same validated submit interface.
    """
    def __init__(self, fighters, skills=(), max_rounds=100, *, escape_followers=()):
        fighters = tuple(fighters)
        skills = tuple(skills)
        if len({f.id for f in fighters}) != len(fighters) or not fighters:
            raise ValueError('Fighter IDs must be unique')
        if {f.side for f in fighters} != {0, 1}:
            raise ValueError('Two sides are required')
        for f in fighters:
            maximum_mp=f.mp if f.max_mp is None else f.max_mp
            if (f.id <= 0 or not 0 < f.hp <= f.max_hp or min(f.mp, f.attack, f.defense, f.speed) < 0
                    or not 0 <= f.mp <= maximum_mp):
                raise ValueError('Invalid fighter stats')
        if max_rounds < 1 or len({s.id for s in skills}) != len(skills):
            raise ValueError('Invalid battle settings')
        if any(s.id <= 0 or min(s.mp, s.power,s.attack_numerator) < 0
               or not 1<=s.max_targets<=28 or s.attack_denominator<1 for s in skills):
            raise ValueError('Invalid skill')
        self._fighters = {f.id: replace(f, skills=tuple(f.skills),max_mp=f.mp if f.max_mp is None else f.max_mp)
                          for f in fighters}
        # Ownership is supplied by the trusted host, never inferred from side.
        # A same-side teammate must not leave when someone else escapes.
        pairs = tuple(escape_followers)
        followers = {}
        assigned = set()
        for owner, follower in pairs:
            if (owner not in self._fighters or follower not in self._fighters
                    or owner == follower or follower in assigned
                    or self._fighters[owner].side != self._fighters[follower].side):
                raise ValueError('Invalid escape ownership')
            followers.setdefault(owner, []).append(follower)
            assigned.add(follower)
        if assigned.intersection(followers):
            raise ValueError('Escape ownership must not form chains')
        self._escape_followers = {owner: tuple(sorted(ids)) for owner, ids in followers.items()}
        self._skills = {s.id: s for s in skills}
        if any(s not in self._skills for f in fighters for s in f.skills):
            raise ValueError('Unknown fighter skill')
        self.round = 1
        self.phase = 'commands'
        self.winner = None
        self._commands = {}
        self._escaped = set()
        self.max_rounds = max_rounds

    @property
    def fighters(self):
        return tuple(self._fighters[k] for k in sorted(self._fighters))

    @property
    def pending(self):
        return tuple(f.id for f in self.fighters if self._active(f) and f.id not in self._commands)

    @property
    def escaped(self):
        return tuple(sorted(self._escaped))

    def _active(self, f):
        return f.hp > 0 and f.id not in self._escaped

    def submit(self, round_number, command):
        if self.phase != 'commands' or round_number != self.round:
            raise ValueError('Battle is not accepting this round')
        actor = self._fighters.get(command.actor)
        if actor is None or not self._active(actor) or actor.id in self._commands:
            raise ValueError('Actor cannot act')
        if command.kind not in ('attack', 'skill', 'defend', 'escape'):
            raise ValueError('Unsupported command')
        if command.kind in ('attack', 'skill'):
            target = self._fighters.get(command.target)
            if target is None or not self._active(target):
                raise ValueError('Invalid target')
            if command.kind == 'skill':
                skill = self._skills.get(command.skill)
                if not skill or skill.id not in actor.skills or actor.mp < skill.mp:
                    raise ValueError('Skill unavailable')
                if (actor.side == target.side) != skill.healing:
                    raise ValueError('Skill target side mismatch')
            elif actor.side == target.side or command.skill:
                raise ValueError('Attack target side mismatch')
        elif command.target or command.skill:
            raise ValueError('Command has unexpected parameters')
        self._commands[actor.id] = command

    def resolve(self):
        if self.phase != 'commands' or self.pending:
            raise ValueError('Commands incomplete or already resolved')
        events = []
        # Guard applies for the whole round, including against faster attackers.
        guards = {c.actor for c in self._commands.values() if c.kind == 'defend'}
        order = sorted(self._commands.values(), key=lambda c: (-self._fighters[c.actor].speed, c.actor))
        for c in order:
            actor = self._fighters[c.actor]
            if not self._active(actor): continue
            if c.kind == 'escape':
                self._escaped.add(actor.id)
                events.append(Event(actor.id, 'escape'))
                for follower_id in self._escape_followers.get(actor.id, ()):
                    follower = self._fighters[follower_id]
                    if self._active(follower):
                        events.append(Event(follower_id, 'escape'))
                    self._escaped.add(follower_id)
            elif c.kind == 'defend':
                events.append(Event(actor.id, 'defend'))
            else:
                target = self._fighters[c.target]
                if not self._active(target): continue
                skill = self._skills[c.skill] if c.kind == 'skill' else None
                cost = skill.mp if skill else 0
                targets=[target]
                if skill and skill.max_targets>1:
                    targets += [f for f in self.fighters if self._active(f) and f.side==target.side
                                and f.id!=target.id][:skill.max_targets-1]
                self._fighters[actor.id] = replace(actor, mp=actor.mp-cost)
                impacts=[]
                for selected in targets:
                    # A self-targeted heal must retain the MP deduction.
                    target=self._fighters[selected.id]
                    if skill and skill.healing:
                        change=min(skill.power,target.max_hp-target.hp)
                    else:
                        attack=actor.attack*skill.attack_numerator//skill.attack_denominator if skill else actor.attack
                        damage=max(1,attack+(skill.power if skill else 0)-target.defense)
                        if target.id in guards:damage=max(1,damage//2)
                        change=-min(target.hp,damage)
                    self._fighters[target.id]=replace(target,hp=target.hp+change)
                    impacts.append(Impact(target.id,change,target.hp+change==0))
                first=impacts[0]
                events.append(Event(actor.id,c.kind,first.target,first.hp_change,-cost,c.skill,first.dead,tuple(impacts)))
            sides = {f.side for f in self._fighters.values() if self._active(f)}
            if len(sides) < 2:
                self.winner = next(iter(sides)) if sides else -1
                break
        if self.winner is None and self.round >= self.max_rounds: self.winner = -1
        self.phase = 'playback'
        return tuple(events)

    def acknowledge(self, round_number):
        if self.phase != 'playback' or round_number != self.round:
            raise ValueError('Unexpected playback acknowledgement')
        self._commands.clear()
        if self.winner is not None:
            self.phase = 'ended'
        else:
            self.round += 1
            self.phase = 'commands'

    def cancel(self):
        """Disconnect/cancel releases in-memory commands without rewards."""
        self._commands.clear()
        self.phase = 'ended'

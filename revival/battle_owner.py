"""One training battle's authoritative state and bounded admission mailbox.

No Session, writer, database, shared gameplay queue or executor lives here.
Only this battle's scheduler calls process_one/advance/close sequentially.
Role/connection routers authenticate and stamp envelopes before admission.
"""
from dataclasses import dataclass, replace
from queue import Queue, Empty, Full
from battle import Fighter
from training_battle import TrainingBattle, TrainingRules, BattleFinished, TrainingPet
from battle_loadout import OwnedBattlePet
import battle_protocol as p


@dataclass(frozen=True)
class Participant:
    role_id: int
    login_epoch: int
    connection_generation: int
    attribute_version: int
    name: str
    shape: int
    level: int
    stats: Fighter | None = None
    authorized_skills: tuple = ()
    pet: TrainingPet | OwnedBattlePet | None = None


@dataclass(frozen=True)
class BattleCommand:
    battle_id: str
    role_id: int
    login_epoch: int
    connection_generation: int
    request_id: str
    sequence: int
    state_version: int
    round_number: int
    deadline_ms: int
    kind: int
    body: bytes


@dataclass(frozen=True)
class BattleSnapshot:
    battle_id: str
    state_version: int
    round_number: int
    phase: str
    fighters: tuple[Fighter, ...]
    pending: tuple[int, ...] = ()


@dataclass(frozen=True)
class Delivery:
    role_id: int
    login_epoch: int
    connection_generation: int
    packets: tuple[tuple[int, bytes], ...]


@dataclass(frozen=True)
class BattleAborted:
    battle_id: str
    role_id: int
    login_epoch: int
    reason: str


@dataclass(frozen=True)
class BattleOutcome:
    request_id: str
    snapshot: BattleSnapshot
    delivery: Delivery | None = None
    finished: BattleFinished | None = None
    aborted: BattleAborted | None = None
    rejection: str = ''
    replayed: bool = False


class BattleOwner:
    """Small Interface: initial, submit/process_one, advance, close, snapshot.

    Queue capacity and receipt capacity are required deployment limits. Receipts
    are retained for this instance's lifetime; full receipts reject new commands
    rather than evicting retry evidence. The host frees terminal instances only
    after handing their result to its role owner (durability is host-owned).
    """
    def __init__(self, participant: Participant, rules: TrainingRules, *,
                 mailbox_capacity: int, receipt_capacity: int,
                 playback_timeout_ms: int, now_ms: int, engine_factory=None):
        if min(mailbox_capacity, receipt_capacity, playback_timeout_ms) < 1:
            raise ValueError('Explicit positive battle limits required')
        if min(participant.role_id, participant.login_epoch,
               participant.connection_generation, participant.attribute_version,
               participant.level, participant.shape) < 1:
            raise ValueError('Authoritative versioned participant required')
        if not participant.name or len(participant.name)>64 or now_ms<0:
            raise ValueError('Invalid participant or clock')
        if participant.stats is not None:
            participant=replace(participant,stats=replace(participant.stats,skills=tuple(participant.stats.skills)))
        self.participant=participant
        self._now_ms=now_ms
        stats=None
        if participant.stats is not None:
            stats={k:getattr(participant.stats,k) for k in ('hp','max_hp','mp','attack','defense','speed')}
            if participant.stats.max_mp is not None:stats['max_mp']=participant.stats.max_mp
        if engine_factory is None:
            self._training=TrainingBattle(
                {'id':participant.role_id,'name':participant.name,'shape':participant.shape,'level':participant.level},
                actor_stats=stats,clock=lambda:self._now_ms/1000,rules=rules,
                login_epoch=participant.login_epoch,snapshot_version=participant.attribute_version,
                authorized_skills=participant.authorized_skills,pet=participant.pet)
        else:
            self._training=engine_factory(participant,rules,lambda:self._now_ms/1000)
        self.id=self._training.id
        self._version=1
        self._sequence=0
        self._queue=Queue(maxsize=mailbox_capacity)
        self._receipts={}
        self.receipt_capacity=receipt_capacity
        self.playback_timeout_ms=playback_timeout_ms
        self._playback_deadline=None
        self._terminal=None
        self._started=False

    def snapshot(self):
        b=self._training.battle
        return BattleSnapshot(self.id,self._version,b.round,b.phase,b.fighters,b.pending)

    def _deliver(self, packets):
        q=self.participant
        return Delivery(q.role_id,q.login_epoch,q.connection_generation,tuple(packets))

    def _clock(self, now_ms):
        if now_ms<self._now_ms: raise ValueError('Monotonic battle clock moved backwards')
        self._now_ms=now_ms

    def initial(self):
        """Return initial logical packets once; no encoding or socket access."""
        if self._started or self._terminal is not None:
            return BattleOutcome('',self.snapshot(),rejection='already_started_or_closed')
        self._started=True
        return BattleOutcome('',self.snapshot(),self._deliver(self._training.opening()))

    def _guard(self, c, now_ms, *, admission=False):
        q=self.participant
        if not isinstance(c,BattleCommand): return 'invalid_envelope'
        if c.battle_id!=self.id: return 'wrong_battle'
        if (c.role_id,c.login_epoch,c.connection_generation)!=(q.role_id,q.login_epoch,q.connection_generation):
            return 'stale_lease'
        if (not isinstance(c.body,bytes) or not isinstance(c.request_id,str)
                or not 0<len(c.request_id)<=128
                or any(type(x) is not int for x in (c.sequence,c.state_version,c.round_number,c.deadline_ms,c.kind))
                or c.sequence<1): return 'invalid_envelope'
        if c.kind not in p.BATTLE_TYPES or len(c.body)>257: return 'invalid_protocol'
        if c.deadline_ms<=now_ms: return 'deadline'
        # Admission only reads immutable identity/limits; mutable battle state
        # is rechecked by its sole scheduler after dequeue.
        if admission:return ''
        receipt=self._receipts.get(c.request_id)
        if receipt is not None:
            # A retry may extend its delivery deadline; it may not change content.
            return '' if self._fingerprint(c)==receipt[0] else 'request_id_conflict'
        if not self._started: return 'not_started'
        if self._terminal is not None: return 'battle_ended'
        if len(self._receipts)>=self.receipt_capacity: return 'receipt_backpressure'
        s=self.snapshot()
        if c.state_version!=s.state_version or c.round_number!=s.round_number: return 'stale_state'
        if c.sequence<=self._sequence: return 'stale_sequence'
        return ''

    @staticmethod
    def _fingerprint(c):
        return c.sequence,c.state_version,c.round_number,c.kind,c.body

    def submit(self, command, now_ms):
        """Thread-safe bounded admission; authoritative mutation is process_one."""
        rejection=self._guard(command,now_ms,admission=True)
        if rejection:return rejection
        try:self._queue.put_nowait(command)
        except Full:return 'backpressure'
        return 'accepted'

    def process_one(self, now_ms):
        self._clock(now_ms)
        try:c=self._queue.get_nowait()
        except Empty:return None
        try:
            rejection=self._guard(c,now_ms)
            if rejection:return BattleOutcome(c.request_id,self.snapshot(),rejection=rejection)
            receipt=self._receipts.get(c.request_id)
            if receipt is not None:
                # Receipts report prior state without repeating animations or
                # settlement effects. Durable delivery is the host's outbox.
                old=receipt[1]
                return BattleOutcome(c.request_id,old.snapshot,rejection=old.rejection,replayed=True)
            before=self.snapshot()
            packets=self._training.receive(c.kind,c.body)
            reason=self._training.last_rejection
            after=self.snapshot()
            self._sequence=c.sequence
            if (after.phase,after.round_number,after.fighters,after.pending)!=(before.phase,before.round_number,before.fighters,before.pending):
                self._version+=1
                self._playback_deadline=now_ms+self.playback_timeout_ms if after.phase=='playback' else None
            finished=self._training.finished()
            outcome=BattleOutcome(c.request_id,self.snapshot(),self._deliver(packets) if packets else None,
                                  finished=finished,rejection=reason)
            self._receipts[c.request_id]=(self._fingerprint(c),outcome)
            if finished is not None:self._terminal=outcome
            return outcome
        finally:self._queue.task_done()

    def advance(self, now_ms):
        """Trusted scheduler tick, not a client message; returns only new effects."""
        self._clock(now_ms)
        if self._terminal is not None or not self._started:return None
        if self._playback_deadline is not None and now_ms>=self._playback_deadline:
            return self.close('playback_timeout',now_ms)
        packets=self._training.tick()
        if not packets:return None
        self._version+=1
        self._playback_deadline=now_ms+self.playback_timeout_ms
        return BattleOutcome('',self.snapshot(),self._deliver(packets))

    def close(self, reason, now_ms):
        self._clock(now_ms)
        if self._terminal is not None:return self._terminal
        if not reason or len(reason)>128:raise ValueError('Bounded abort reason required')
        self._training.close();self._version+=1
        q=self.participant
        abort_finished=getattr(self._training,'abort_finished',None)
        if abort_finished is not None:
            self._terminal=BattleOutcome('',self.snapshot(),self._deliver(((p.BATTLE_END,p.battle_end()),)),
                finished=abort_finished(reason))
            return self._terminal
        self._terminal=BattleOutcome('',self.snapshot(),self._deliver(((p.BATTLE_END,p.battle_end()),)),
                                    aborted=BattleAborted(self.id,q.role_id,q.login_epoch,reason))
        return self._terminal

    def terminal(self):
        """Immutable terminal event for host-owned outbox retry/acknowledgement."""
        return self._terminal

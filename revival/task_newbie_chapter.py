"""Durable newbie creation provenance and caller-transaction chapter lifecycle.

Uses original NewbieFlow routes/tickets; owns no connection, spawn writer,
Session or network sender. Each supplied NewbieFlow is TRANSACTION-LOCAL;
only frozen IntroTicket/chapter messages cross the role/persistence seam.
"""
from dataclasses import asdict,dataclass,replace
import hashlib
import json
from types import MappingProxyType
from uuid import uuid4
import struct
from inspect_client import OUT
from tasks import _freeze,_plain
from task_persistence import load_task_state,apply_task_plan
from task_domain import TaskDomain,valid_task_epoch
from task_workflow import (complete_task_transaction,replay_completed_task_transaction,completion_messages)
from task_rewards import update_reward_delivery
from task_protocol import S_ACCEPT_SCENARIO_QUEST,ScenarioQuestInfo,encode_accept_scenario_quest
from world_newbie import NewbieRoute,NewbieFlow
from world_catalog import valid_position
from world_collision import maze_clear
from task_protocol import SCENARIO_ACTIVE


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'))


def _route_fingerprint(policy,route):
    return hashlib.sha256(_json([policy,asdict(route)]).encode()).hexdigest()


@dataclass(frozen=True)
class NewbieChapterRules:
    revision: str
    timeout_ms: int
    routes: object


def load_newbie_chapter_rules(resources,routes,catalog,grids):
    """Startup only: validate all43 routes and designed mask1 spawn choices."""
    policy=json.loads((OUT/'design/newbie-opening-v1.json').read_text(encoding='utf-8'))
    if (policy['revision']!='2026-10-23.newbie.1' or policy['chapter']['timeout_ms']!=1800000
            or policy['routes']['expected_count']!=43 or len(routes)!=43):
        raise ValueError('Newbie chapter policy requires implementation review')
    NewbieFlow(resources,routes)  # original route/root/successor consistency
    for route in routes.values():
        position=route.cinematic_endpoint
        grid=grids.get(route.home_map_id)
        if (position[0]!=route.home_map_id or not valid_position(position,catalog) or grid is None
                or not maze_clear(grid,*position[1:],mask=1)):
            raise ValueError('Newbie designed birth coordinate is unavailable or blocked')
    return NewbieChapterRules(policy['revision'],policy['chapter']['timeout_ms'],MappingProxyType(dict(routes)))


def prepare_newbie_chapter_storage(db):
    """Startup-only DDL; chapter writes themselves join the caller transaction."""
    db.executescript('''CREATE TABLE IF NOT EXISTS task_newbie_origins (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id), creation_id TEXT UNIQUE NOT NULL,
        chapter_id TEXT UNIQUE NOT NULL, policy TEXT NOT NULL, route TEXT NOT NULL,
        route_fingerprint TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS task_newbie_chapters (
        role_id INTEGER PRIMARY KEY REFERENCES roles(id), phase TEXT NOT NULL
          CHECK(phase IN ('authorized','playing','completed')),
        revision INTEGER NOT NULL, payload TEXT NOT NULL);''')
    columns={r[1] for r in db.execute('PRAGMA table_info(task_newbie_origins)')}
    if 'route_fingerprint' not in columns:
        db.execute('ALTER TABLE task_newbie_origins ADD COLUMN route_fingerprint TEXT')
        for role_id,policy,body in db.execute('SELECT role_id,policy,route FROM task_newbie_origins').fetchall():
            data=json.loads(body);data['cinematic_endpoint']=tuple(data['cinematic_endpoint'])
            db.execute('UPDATE task_newbie_origins SET route_fingerprint=? WHERE role_id=?',
                (_route_fingerprint(policy,NewbieRoute(**data)),role_id))


@dataclass(frozen=True)
class NewbieOrigin:
    role_id: int
    creation_id: str
    chapter_id: str
    policy: str
    route: NewbieRoute

    @property
    def spawn(self):
        return self.route.cinematic_endpoint

    @property
    def route_fingerprint(self):
        return _route_fingerprint(self.policy,self.route)


@dataclass(frozen=True)
class NewbieChapter:
    origin: NewbieOrigin
    phase: str
    revision: int
    playback: object

    @property
    def intro_discriminator(self):
        return int(self.phase=='completed')


@dataclass(frozen=True)
class NewbiePlayback:
    chapter: NewbieChapter
    ticket: object
    messages: tuple


@dataclass(frozen=True)
class NewbieCompletion:
    chapter: NewbieChapter
    completion: object
    evidence: object
    messages: tuple


def resume_newbie_messages(chapter,snapshot,*,already_projected=()):
    """Display the provenance-selected active successor without completing it.

    Card objectives cannot pass the plain-dialogue capability check. Their
    durable active journal entry still needs its ordinary tracker bean after
    reconnect. No empty-table, level or reward inference authorizes a task.
    """
    if chapter is None or chapter.phase!='completed':
        return ()
    ident=chapter.origin.route.successor_task_id
    if ident not in snapshot.active or ident in already_projected:
        return ()
    return ((S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(
        ScenarioQuestInfo(ident,SCENARIO_ACTIVE,0,0,0))),)


def _owner(db,account_id,role_id,epoch=None,*,creation=False):
    if not db.in_transaction:
        raise ValueError('Newbie operation requires caller transaction')
    row=db.execute('SELECT level,shape,school FROM roles WHERE id=? AND account_id=?',(role_id,account_id)).fetchone()
    if row is None:
        raise ValueError('Newbie role ownership or current lease mismatch')
    if not creation and (not valid_task_epoch(epoch) or not db.execute(
            'SELECT 1 FROM role_leases WHERE role_id=? AND epoch=? AND active=1',(role_id,epoch)).fetchone()):
        raise ValueError('Newbie role ownership or current lease mismatch')
    return row


def _origin(db,role_id,rules):
    row=db.execute('SELECT creation_id,chapter_id,policy,route,route_fingerprint FROM task_newbie_origins WHERE role_id=?',(role_id,)).fetchone()
    if row is None:
        return None
    data=json.loads(row[3]);data['cinematic_endpoint']=tuple(data['cinematic_endpoint'])
    route=NewbieRoute(**data)
    if (row[2]!=rules.revision or rules.routes.get((route.character_id,route.school_id))!=route
            or row[4]!=_route_fingerprint(row[2],route)):
        raise ValueError('Newbie provenance route/policy migration required')
    return NewbieOrigin(role_id,row[0],row[1],row[2],route)


def read_newbie_chapter(db,account_id,role_id,epoch,rules):
    _owner(db,account_id,role_id,epoch)
    origin=_origin(db,role_id,rules)
    row=db.execute('SELECT phase,revision,payload FROM task_newbie_chapters WHERE role_id=?',(role_id,)).fetchone()
    if row is None:
        return None
    if origin is None:
        raise ValueError('Newbie chapter has no independent creation provenance')
    return NewbieChapter(origin,row[0],row[1],_freeze(json.loads(row[2])))


def record_newbie_creation(db,account_id,role_id,creation_id,resources,rules):
    """Trusted creation-only Interface, in the SAME transaction as the new role.

    Returns validated spawn for the creation/world Adapter to insert once in
    that transaction. This Module never writes or resets role_positions.
    Wallet/growth origins, empty EXP and client intro fields grant no authority.
    """
    level,shape,school=_owner(db,account_id,role_id,creation=True)
    if type(creation_id) is not str or not 1<=len(creation_id)<=128:
        raise ValueError('Stable trusted creation operation identity required')
    route=rules.routes.get((resources.shape_to_role_config.get(shape),school))
    if route is None:
        raise ValueError('No original character/school newbie route')
    old=_origin(db,role_id,rules)
    if old is not None:
        if old.creation_id!=creation_id or old.route!=route:
            raise ValueError('Newbie creation identity reused with different intent')
        return old
    if (level!=1 or db.execute('SELECT 1 FROM role_leases WHERE role_id=?',(role_id,)).fetchone()
            or db.execute('SELECT 1 FROM role_positions WHERE role_id=?',(role_id,)).fetchone()
            or db.execute('SELECT 1 FROM task_journal WHERE role_id=?',(role_id,)).fetchone()
            or db.execute('SELECT 1 FROM task_offers WHERE role_id=?',(role_id,)).fetchone()):
        raise ValueError('Newbie provenance may only be recorded in fresh creation workflow')
    origin=NewbieOrigin(role_id,creation_id,uuid4().hex,rules.revision,route)
    db.execute('INSERT INTO task_newbie_origins VALUES(?,?,?,?,?,?)',
        (role_id,creation_id,origin.chapter_id,rules.revision,_json(asdict(route)),origin.route_fingerprint))
    return origin


def _flow_route(flow,actor,origin,school):
    if not isinstance(flow,NewbieFlow) or flow.route(actor,school_id=school)!=origin.route:
        raise ValueError('Newbie current role/flow disagrees with frozen creation route')


def initialize_newbie_chapter(db,account_id,role_id,epoch,flow,rules):
    """Redeem independent creation provenance once under the first valid lease."""
    _,_,school=_owner(db,account_id,role_id,epoch)
    origin=_origin(db,role_id,rules)
    if origin is None:
        if db.execute('SELECT 1 FROM task_newbie_chapters WHERE role_id=?',(role_id,)).fetchone():
            raise ValueError('Newbie chapter is missing its creation provenance')
        return None  # legacy/growth-only origin stays legacy, no inference
    actor,snapshot=load_task_state(db,account_id,role_id,epoch)
    old=read_newbie_chapter(db,account_id,role_id,epoch,rules)
    if old is not None:
        expected=snapshot.completed if old.phase=='completed' else snapshot.active
        if origin.route.intro_task_id not in expected:
            raise ValueError('Newbie chapter and durable task disagree')
        if old.phase=='completed' and origin.route.successor_task_id not in snapshot.active|snapshot.completed:
            raise ValueError('Newbie selected successor is missing; reconciliation required')
        return old
    _flow_route(flow,actor,origin,school)
    for plan in flow.initial_task_plans(actor,snapshot,school_id=school):
        apply_task_plan(db,actor,plan,f'newbie:{origin.chapter_id}:{plan.action}')
    db.execute('INSERT INTO task_newbie_chapters VALUES(?,?,?,?)',(role_id,'authorized',0,'{}'))
    return read_newbie_chapter(db,account_id,role_id,epoch,rules)


def _update(db,chapter,phase,payload):
    if db.execute('UPDATE task_newbie_chapters SET phase=?,revision=revision+1,payload=? WHERE role_id=? AND revision=?',
            (phase,_json(payload),chapter.origin.role_id,chapter.revision)).rowcount!=1:
        raise ValueError('Stale newbie chapter revision')


def authorize_newbie_playback(db,account_id,role_id,epoch,flow,rules,location,*,generation,request_id,now_ms,trusted_resume=False):
    """Persist authorization before returning root bean then SStartPlayCG.

    Call only after world initialization using a transaction-local flow. For a
    same-request retry restore it from the role owner's frozen IntroTicket via
    NewbieFlow's public factory. Discard the local flow on rollback; only publish
    the returned frozen ticket after commit. Timeout never completes a chapter.
    """
    _,_,school=_owner(db,account_id,role_id,epoch)
    if type(now_ms) is not int or not 0<=now_ms<=2**63-1-rules.timeout_ms:
        raise ValueError('Valid server authorization clock required')
    chapter=read_newbie_chapter(db,account_id,role_id,epoch,rules)
    if chapter is None:
        raise ValueError('Newbie chapter has not been durably authorized')
    if chapter.phase=='completed':
        return NewbiePlayback(chapter,None,())
    actor,snapshot=load_task_state(db,account_id,role_id,epoch)
    _flow_route(flow,actor,chapter.origin,school)
    same=False;deadline=now_ms+rules.timeout_ms
    if chapter.phase=='playing':
        old=chapter.playback
        same_scope=old['actor']['login_epoch']==epoch and old['generation']==generation
        if same_scope and old['request_id']==request_id and now_ms<old['deadline_ms']:
            same=True;deadline=old['deadline_ms']
        elif same_scope and not (trusted_resume and now_ms>=old['deadline_ms']):
            raise ValueError('Another newbie playback remains authorized')
    if not same:
        flow.cancel()
    ticket,starts=flow.start(actor,snapshot,location,school_id=school,generation=generation,
        request_id=request_id,now_ms=now_ms,deadline_ms=deadline)
    if same and ticket.source_id!=chapter.playback['source_id']:
        flow.cancel()
        raise ValueError('Same-request playback requires the original restored IntroTicket')
    if not same:
        _update(db,chapter,'playing',asdict(ticket))
        chapter=read_newbie_chapter(db,account_id,role_id,epoch,rules)
    bean=ScenarioQuestInfo(chapter.origin.route.intro_task_id,SCENARIO_ACTIVE,0,0,0)
    return NewbiePlayback(chapter,ticket,((S_ACCEPT_SCENARIO_QUEST,encode_accept_scenario_quest(bean)),)+starts)


def _resolve_intro_effect(db,chapter):
    route=chapter.origin.route
    row=db.execute('SELECT payload FROM task_effects WHERE role_id=? AND task_id=?',
        (chapter.origin.role_id,route.intro_task_id)).fetchone()
    if row is None:
        raise ValueError('Newbie completion effect missing')
    effect=json.loads(row[0])
    if int(effect.get('continuation_fields',{}).get('ScenarioInfoAnimationID',0))!=route.intro_movie_id:
        raise ValueError('Newbie movie effect differs from frozen route')
    effect.update(chain_status='activated',chain_reason='newbie_original_character_route',
        chain_target=route.successor_task_id,chain_resolved=True,chapter_id=chapter.origin.chapter_id)
    resolved=set(effect.get('continuation_resolved_fields',()))
    resolved.add('ScenarioInfoAnimationID')
    effect['continuation_resolved_fields']=sorted(resolved)
    delivered=update_reward_delivery(effect)
    db.execute('UPDATE task_effects SET payload=?,delivered=? WHERE role_id=? AND task_id=?',
        (_json(effect),int(delivered),chapter.origin.role_id,route.intro_task_id))


def finish_newbie_chapter(db,account_id,role_id,epoch,flow,rules,body,location,inventory,*,generation,now_ms,
                          growth_rules=None,attribute_rules=None,currency_rules=None,pet_experience_rules=None,
                          resource_rules=None,equipment_rules=None):
    """Match memory+durable permit, then complete root/award/activate next once.

    Restore a transaction-local flow from the owner's frozen IntroTicket first.
    After commit the owner clears its ticket; failures discard only this local
    flow and can retry from the same immutable permit. Duplicates return
    evidence=None and no messages. No role-owned mutable flow enters this worker.
    """
    _,_,school=_owner(db,account_id,role_id,epoch)
    if type(now_ms) is not int or now_ms<0:
        raise ValueError('Valid server completion clock required')
    chapter=read_newbie_chapter(db,account_id,role_id,epoch,rules)
    if chapter is None or type(body) is not bytes or len(body)!=4 or struct.unpack('>i',body)[0]!=chapter.origin.route.intro_movie_id:
        raise ValueError('Unsolicited newbie movie completion')
    actor,snapshot=load_task_state(db,account_id,role_id,epoch)
    if chapter.phase=='completed':
        completed=replay_completed_task_transaction(db,actor,chapter.origin.route.intro_task_id,flow.resources,inventory,
            growth_rules,attribute_rules,currency_rules,pet_experience_rules,
            resource_rules=resource_rules,equipment_rules=equipment_rules)
        _resolve_intro_effect(db,chapter)
        return NewbieCompletion(chapter,completed,None,())
    _flow_route(flow,actor,chapter.origin,school)
    if chapter.phase!='playing':
        raise ValueError('No persisted newbie playback')
    permit=chapter.playback
    if (permit['actor']['login_epoch']!=epoch or permit['generation']!=generation
            or now_ms>=permit['deadline_ms'] or _json(asdict(location))!=_json(_plain(permit['location']))):
        raise ValueError('Stale persisted newbie playback scope')
    evidence=flow.finish(body,actor,snapshot,location,generation=generation,now_ms=now_ms)
    if evidence.source_id!=permit['source_id']:
        raise ValueError('Movie completion does not match persisted playback identity')
    plan=TaskDomain(flow.resources).plan(actor,snapshot,'complete',chapter.origin.route.intro_task_id,evidence=evidence)
    completed=complete_task_transaction(db,actor,plan,f'newbie:{chapter.origin.chapter_id}:complete',flow.resources,inventory,
        growth_rules,attribute_rules,currency_rules,pet_experience_rules,
        resource_rules=resource_rules,equipment_rules=equipment_rules)
    actor,snapshot=load_task_state(db,account_id,role_id,epoch)
    started=list(completed.started_tasks)
    for next_plan in flow.successor_task_plans(actor,snapshot,school_id=school):
        apply_task_plan(db,actor,next_plan,f'newbie:{chapter.origin.chapter_id}:next:{next_plan.action}')
        if next_plan.action=='accept':
            started.append(next_plan.task_id)
    _resolve_intro_effect(db,chapter)
    payload=_plain(permit)
    payload['completion_key']=f'newbie:{chapter.origin.chapter_id}:complete'
    _update(db,chapter,'completed',payload)
    chapter=read_newbie_chapter(db,account_id,role_id,epoch,rules)
    ids=tuple(dict.fromkeys(started))
    completed=replace(completed,started_tasks=ids,started_infos=tuple(ScenarioQuestInfo(q,SCENARIO_ACTIVE,0,0,0) for q in ids))
    return NewbieCompletion(chapter,completed,evidence,completion_messages(completed))

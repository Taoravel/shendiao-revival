"""Stable private story identities in the role caller's existing transaction.

Directory allocation is neither task completion nor map admission. Map owners
and their live projections are outside this SQLite compatibility Adapter.
"""
from dataclasses import dataclass
import json
import secrets
from types import MappingProxyType

from inspect_client import OUT
from task_newbie_chapter import read_newbie_chapter
from world_owner import MapAddress


@dataclass(frozen=True)
class StoryInstanceIntent:
    chapter_id: str
    creation_id: str
    origin_policy: str
    route_fingerprint: str
    source_task_id: int


@dataclass(frozen=True)
class StoryInstanceRules:
    revision: str
    kind: str
    map_id: int
    partition_id: int
    minimum_id: int
    maximum_id: int
    collision_attempts: int
    member_capacity: int
    loaded_capacity: int
    idle_unload_after_ms: int
    pins_per_projection: int
    scene_delivery_capacity: int
    chapter_rules: object
    source_tasks: object


@dataclass(frozen=True)
class StoryInstance:
    kind: str
    account_id: int
    role_id: int
    intent: StoryInstanceIntent
    directory_policy: str
    address: MapAddress


def load_story_instance_rules(resources,chapter_rules,*,path=OUT/'design/story-instance-v1.json',
                              bloodmark_path=OUT/'design/newbie-bloodmark-v1.json'):
    """Startup only: freeze published policy and actual43 original task paths."""
    policy=json.loads(path.read_text(encoding='utf-8'))
    bloodmark=json.loads(bloodmark_path.read_text(encoding='utf-8'))
    if (policy['revision']!='2026-10-23.story-instance.1'
            or policy['scope']!={'kind':'newbie_bloodmark_dream','map_id':1501,'partition_id':0}
            or policy['instance_id_min_inclusive']!=2**62 or policy['instance_id_max_exclusive']!=2**63
            or policy['collision_attempts']!=8 or policy['member_capacity']!=1
            or policy['loaded_instance_capacity_per_process']!=128 or policy['idle_unload_after_ms']!=60000
            or any(type(policy.get(name)) is not int or policy[name]!=64
                for name in ('pins_per_projection','scene_delivery_capacity'))
            or bloodmark['revision']!='2026-10-23.newbie-bloodmark.1'
            or bloodmark['private_directory_policy']!=policy['revision']
            or set(bloodmark['tasks'])!={100106,100206,100306,100406,100506,100606,100706,100806,100906,103206}
            or len(chapter_rules.routes)!=43):
        raise ValueError('Story instance policy requires implementation review')
    tasks=set(bloodmark['tasks']);sources={}
    for key,route in chapter_rules.routes.items():
        ident=route.successor_task_id;seen=set()
        while ident not in tasks:
            if ident in seen or ident not in resources.definitions:
                raise ValueError('Story source route is missing or cyclic')
            seen.add(ident);next_ids=resources.definitions[ident]['next_ids']
            if len(next_ids)!=1:
                raise ValueError('Story source route is ambiguous')
            ident=next_ids[0]
        row=resources.definitions[ident]
        attrs=row['attributes']
        if (row['type']!=10 or row['target']['map_id']!=1006 or row['target']['npc_id']!=10498
                or any(int(attrs[k])!=value for k,value in
                    (('RewardMapJumpType',3),('RewardMapID',1501),('RewardMapXPos',63),('RewardMapYPos',79)))):
            raise ValueError('Story source disagrees with original bloodmark task')
        sources[key]=ident
    if set(sources.values())!=tasks:
        raise ValueError('Story source routes do not cover the published ten tasks')
    return StoryInstanceRules(policy['revision'],policy['scope']['kind'],1501,0,2**62,2**63,8,1,128,60000,
        policy['pins_per_projection'],policy['scene_delivery_capacity'],
        chapter_rules,MappingProxyType(sources))


def prepare_story_instance_storage(db):
    """Startup DDL only; never called by allocate/load."""
    db.execute('''CREATE TABLE IF NOT EXISTS world_story_instances (
        kind TEXT NOT NULL, role_id INTEGER NOT NULL REFERENCES roles(id), chapter_id TEXT NOT NULL,
        account_id INTEGER NOT NULL, creation_id TEXT NOT NULL, origin_policy TEXT NOT NULL,
        route_fingerprint TEXT NOT NULL, source_task_id INTEGER NOT NULL, directory_policy TEXT NOT NULL,
        map_id INTEGER NOT NULL, instance_id INTEGER UNIQUE NOT NULL, partition_id INTEGER NOT NULL,
        PRIMARY KEY(kind,role_id,chapter_id))''')


def _scope(db,account_id,role_id,epoch,intent,rules):
    if (not db.in_transaction or type(account_id) is not int or not 0<account_id<2**63
            or type(role_id) is not int or not 0<role_id<2**63
            or not ((type(epoch) is int and 0<epoch<2**63) or (type(epoch) is str and 1<=len(epoch)<=128))
            or type(intent) is not StoryInstanceIntent or type(intent.source_task_id) is not int
            or any(type(v) is not str or not 1<=len(v)<=128 for v in
                (intent.chapter_id,intent.creation_id,intent.origin_policy,intent.route_fingerprint))
            or not db.execute('SELECT 1 FROM roles r JOIN role_leases l ON l.role_id=r.id '
                'WHERE r.id=? AND r.account_id=? AND l.epoch=? AND l.active=1 '
                'AND NOT EXISTS(SELECT 1 FROM role_deletions d WHERE d.role_id=r.id)',
                (role_id,account_id,str(epoch))).fetchone()):
        raise ValueError('Story directory requires the current role caller transaction and frozen intent')
    chapter=read_newbie_chapter(db,account_id,role_id,epoch,rules.chapter_rules)
    if chapter is None or chapter.phase!='completed':
        raise ValueError('Story directory requires a completed original chapter')
    origin=chapter.origin;route=origin.route
    expected=StoryInstanceIntent(origin.chapter_id,origin.creation_id,origin.policy,
        origin.route_fingerprint,rules.source_tasks.get((route.character_id,route.school_id)))
    if (intent!=expected or not db.execute('SELECT 1 FROM task_journal WHERE role_id=? AND task_id=? '
            "AND state='completed'",(role_id,route.intro_task_id)).fetchone()):
        raise ValueError('Story directory intent differs from durable creation and original route')


def _valid_address(address,rules):
    return (type(address) is MapAddress
        and all(type(v) is int for v in (address.map_id,address.instance_id,address.partition_id))
        and address.map_id==rules.map_id and address.partition_id==rules.partition_id
        and rules.minimum_id<=address.instance_id<rules.maximum_id)


def _read(db,account_id,role_id,intent,rules):
    row=db.execute('SELECT account_id,creation_id,origin_policy,route_fingerprint,source_task_id,'
        'directory_policy,map_id,instance_id,partition_id FROM world_story_instances '
        'WHERE kind=? AND role_id=? AND chapter_id=?',(rules.kind,role_id,intent.chapter_id)).fetchone()
    if row is None:return None
    address=MapAddress(*row[6:])
    if (row[:6]!=(account_id,intent.creation_id,intent.origin_policy,intent.route_fingerprint,
                   intent.source_task_id,rules.revision)
            or not _valid_address(address,rules)):
        raise ValueError('Persistent story directory identity conflicts; migration required')
    return StoryInstance(rules.kind,account_id,role_id,intent,rules.revision,address)


def load_story_instance_transaction(db,account_id,role_id,epoch,intent,rules,*,expected_address=None):
    """Current lease + frozen intent -> exact durable identity, or None.

    On recovery callers first commit transfer recovery, load the full current
    checkpoint, and supply its address here. Missing identity never reallocates
    or selects a public map. No position, membership or task write occurs.
    """
    _scope(db,account_id,role_id,epoch,intent,rules)
    result=_read(db,account_id,role_id,intent,rules)
    if expected_address is not None and (not _valid_address(expected_address,rules)
            or result is None or expected_address!=result.address):
        raise ValueError('Current private address has no matching story directory')
    return result


def allocate_story_instance_transaction(db,account_id,role_id,epoch,intent,rules,*,random_bits=None):
    """Trusted task caller allocates identity only, joining its open transaction.

    Caller validates its current task/ticket and completes entry atomically with
    the exact handoff, full checkpoint, task and receipt. Publish after commit.
    A directory row alone grants neither entry nor a completed bloodmark task.
    """
    _scope(db,account_id,role_id,epoch,intent,rules)
    old=_read(db,account_id,role_id,intent,rules)
    if old is not None:return old
    entropy=secrets.randbits if random_bits is None else random_bits
    for _ in range(rules.collision_attempts):
        bits=entropy(62)
        if type(bits) is not int or not 0<=bits<2**62:
            raise ValueError('Story entropy source must return exactly a62bit nonnegative integer')
        inserted=db.execute('INSERT INTO world_story_instances VALUES(?,?,?,?,?,?,?,?,?,?,?,?) '
            'ON CONFLICT(instance_id) DO NOTHING',
            (rules.kind,role_id,intent.chapter_id,account_id,intent.creation_id,intent.origin_policy,
             intent.route_fingerprint,intent.source_task_id,rules.revision,rules.map_id,bits|2**62,rules.partition_id))
        if inserted.rowcount==1:return _read(db,account_id,role_id,intent,rules)
    raise ValueError('Private story instance ID collision budget exhausted')

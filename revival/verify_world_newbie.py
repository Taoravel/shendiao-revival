"""Original school/character route and role-owned cinematic authorization."""
from world_newbie import load_newbie_routes, NewbieFlow, check_birth_site, validate_birth_sites
from tasks import TaskResources
from task_domain import TaskActor, TaskSnapshot
from world_owner import MapAddress, Location
import json
from pathlib import Path
from types import MappingProxyType
from dataclasses import replace
from task_domain import TaskDomain
from inspect_client import OUT, write_json
from world_grids import SceneGrid
from world_npcs import NpcPlacement


def refused(action):
    try: action()
    except ValueError: return
    raise AssertionError('Unauthorized or stale cinematic accepted')


def main():
    root = Path(__file__).parent
    tasks = json.loads((root/'catalogs/tasks.json').read_text(encoding='utf-8'))['missions']
    choices = json.loads((root/'catalogs/knight.gsp.role.createroleconfig.json').read_text(encoding='utf-8'))
    resources = TaskResources(MappingProxyType({r['id']:r for r in tasks}), MappingProxyType({
        int(r['attributes'][c]):int(r['attributes']['id']) for r in choices for c in ('color1','color2','color3')}))
    routes = load_newbie_routes()
    assert len(routes) == 43
    flow = NewbieFlow(resources, routes)
    actor = TaskActor(1, 7, 'newbie-epoch', 1, 1010109)
    route = flow.route(actor, school_id=111)
    assert (route.home_map_id,route.intro_task_id,route.intro_movie_id,route.successor_task_id) == (
        1110,103201,11032,103286)
    assert route.cinematic_endpoint == (1110,1408,1488)
    assert route.successor_card_effect_id == 20044
    other = flow.route(actor, school_id=11)
    assert (other.home_map_id,other.intro_task_id,other.successor_task_id) == (1100,100101,100186)
    empty = TaskSnapshot(actor.role_id)
    plans = flow.initial_task_plans(actor,empty,school_id=111)
    assert [p.action for p in plans] == ['offer','accept']
    assert plans[-1].after.active == frozenset({103201}) and not empty.active
    location = Location(actor.role_id, actor.login_epoch, MapAddress(1110, 1, 0), 1, 1408, 1488)
    arguments = dict(school_id=111, generation=1, request_id='intro-1', now_ms=0, deadline_ms=100)
    refused(lambda: flow.start(actor, empty, location, **arguments))
    snapshot = plans[-1].after
    refused(lambda: flow.initial_task_plans(actor,snapshot,school_id=111))
    ticket, messages = flow.start(actor, snapshot, location, **arguments)
    assert messages == ((0xc0017, bytes.fromhex('00002b18')),)
    assert flow.start(actor, snapshot, location, **arguments) == (ticket,messages)
    refused(lambda: flow.finish(bytes.fromhex('00002af9'), actor, snapshot, location,
                                generation=1, now_ms=1))
    refused(lambda: flow.finish(bytes.fromhex('00002b18'), actor, snapshot,
        replace(location,version=2), generation=1, now_ms=1))
    refused(lambda: flow.finish(bytes.fromhex('00002b18'), actor, snapshot, location,
                                generation=2, now_ms=1))
    evidence = flow.finish(bytes.fromhex('00002b18'), actor, snapshot, location,
                           generation=1, now_ms=1)
    resumed = NewbieFlow.from_ticket(resources,routes,ticket)
    assert resumed.finish(bytes.fromhex('00002b18'),actor,snapshot,location,
                          generation=1,now_ms=1) == evidence
    assert resumed.start(actor,snapshot,location,**arguments) == (ticket,messages)
    refused(lambda: NewbieFlow.from_ticket(resources,routes,replace(ticket,source_id='other')))
    refused(lambda: NewbieFlow.from_ticket(resources,routes,replace(ticket,route=other)))
    refused(lambda: NewbieFlow.from_ticket(resources,routes,
        replace(ticket,route=replace(route,school_id=[]))))
    refused(lambda: NewbieFlow.from_ticket(resources,routes,replace(ticket,generation=0)))
    refused(lambda: NewbieFlow.from_ticket(resources,routes,replace(ticket,deadline_ms=-1)))
    refused(lambda: NewbieFlow.from_ticket(resources,routes,
        replace(ticket,location=replace(location,login_epoch='old'))))
    refused(lambda: NewbieFlow.from_ticket(resources,routes,
        replace(ticket,location=replace(location,state='loading'))))
    refused(lambda: resumed.finish(bytes.fromhex('00002b18'),actor,snapshot,location,
                                   generation=1,now_ms=100))
    completed = TaskDomain(resources).plan(actor, snapshot, 'complete',103201,evidence=evidence)
    assert completed.after.completed == frozenset({103201})
    assert completed.next_ids == (103284,103285,103286,103287,103283)
    next_plans = flow.successor_task_plans(actor, completed.after, school_id=111)
    assert [p.task_id for p in next_plans] == [103286,103286]
    assert next_plans[-1].after.active == frozenset({103286})
    assert flow.successor_task_plans(actor,next_plans[-1].after,school_id=111) == ()
    flow.committed(evidence)
    refused(lambda: flow.finish(bytes.fromhex('00002b18'), actor, snapshot, location,
                                generation=1, now_ms=2))
    fixture = replace(route,home_map_id=7,first_npc_id=9,cinematic_endpoint=(7,8,8))
    catalog = {7:dict(available=True,width=48,height=48,portals={})}
    placements = (NpcPlacement(1,9,7,40,8,0),)
    # A wall blocks the direct line; the lower gap permits a real route around it.
    maze = SceneGrid(3,3,bytes([0,1,0,0,1,0,0,0,0]),12)
    checked = check_birth_site(fixture,catalog,maze,placements,state_byte=0,
                               interaction_radius=1,max_visited=20)
    assert checked.status == 'reachable' and checked.path[0] == (8,8) and checked.path[-1] == (40,8)
    limited = check_birth_site(fixture,catalog,maze,placements,state_byte=0,
                               interaction_radius=1,max_visited=1)
    assert limited.status == 'search_budget' and not limited.path
    checked_sites = validate_birth_sites({(9,111):fixture},catalog,{7:maze},{7:placements},
        state_byte=0,interaction_radius=1,max_visited=20)
    assert checked_sites[(9,111)] == checked
    refused(lambda: validate_birth_sites({(9,111):fixture},catalog,{7:maze},{7:placements},
        state_byte=0,interaction_radius=1,max_visited=1))
    write_json(OUT/'evidence/world-newbie-flow-verification.json',dict(
        original_character_school_routes=len(routes), tested_home_map=1110,
        tested_intro_task=103201, tested_movie=11032, selected_successor=103286,
        initial_task_plans=['offer','accept'], completion_uses_existing_TaskDomain=True,
        guards=['unoffered intro','wrong movie','changed position version','wrong connection',
                'duplicate completion after commit','reinitializing existing progress',
                'restored ticket source/route/generation/deadline/epoch/structure'],
        restored_ticket_preserves_source_and_request=True,
        source_spawn_confirmed=False, durable_playback_journal_tested=False,
        shared_runtime_tested=False,
        live_role_modified=False, client_launched=False, gui_verified=False))
    print('PASS original routes, authorized intro packet, scoped completion and TaskDomain proof')


if __name__ == '__main__':
    main()

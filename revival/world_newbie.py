"""Original newbie routes and role-owned opening authorization.

Startup loading is separate from commands. The route's cinematic endpoint is
an original actor coordinate, not a proven original server spawn position.
"""
from dataclasses import dataclass
import json
from types import MappingProxyType
from uuid import uuid4
import struct
import re
from inspect_client import OUT
from task_domain import TaskDomain, TaskEvidence, TaskActor, valid_task_epoch
from world_owner import Location, MapAddress
from collections import deque
from world_catalog import valid_position
from world_collision import character_movement_mask, maze_clear, maze_segment_clear

START_PLAY_CG = 0xc0017
END_PLAY_CG = 0xc0018


@dataclass(frozen=True)
class NewbieRoute:
    character_id: int
    school_id: int
    home_map_id: int
    intro_task_id: int
    intro_movie_id: int
    successor_task_id: int
    successor_card_effect_id: int
    first_npc_id: int
    cinematic_endpoint: tuple


@dataclass(frozen=True)
class IntroTicket:
    actor: object
    location: object
    generation: int
    route: NewbieRoute
    request_id: str
    source_id: str
    deadline_ms: int


@dataclass(frozen=True)
class BirthSiteCheck:
    status: str
    path: tuple = ()
    visited: int = 0
    placement_id: int | None = None
    movement_mask: int = 0


def check_birth_site(route, catalog, maze, placements, *, state_byte,
                     interaction_radius=None, max_visited, interaction_allowed=None):
    """Find an immutable native-clear witness from the movie endpoint to its NPC.

    This is an offline design check, not the original client's path finder and
    not proof of an original server spawn. The caller explicitly chooses the
    character state, interaction goal and search budget. Choose exactly one:
    a legacy nonnegative radius, or a trusted startup-frozen synchronous
    predicate(placement, (map_id,x,y)) returning a strict bool. This module does
    not load or approximate the predicate's policy. Coordinates are
    logical pixels; NPC placements must come from the scene placement catalog.
    A budget exhausted result says nothing about global unreachability.
    """
    if (type(max_visited) is not int or max_visited < 1
            or (interaction_allowed is None
                and (type(interaction_radius) is not int or interaction_radius < 0))
            or (interaction_allowed is not None
                and (interaction_radius is not None or not callable(interaction_allowed)))):
        raise ValueError('Choose one explicit interaction goal and a positive search budget')
    mask = character_movement_mask(state_byte)
    start_map, x, y = route.cinematic_endpoint
    if start_map != route.home_map_id or not valid_position(route.cinematic_endpoint, catalog):
        return BirthSiteCheck('outside_map', movement_mask=mask)
    if not maze_clear(maze, x, y, mask=mask):
        return BirthSiteCheck('blocked_start', movement_mask=mask)
    targets = tuple(p for p in placements if p.map_id == route.home_map_id
                    and p.npc_id == route.first_npc_id
                    and valid_position((p.map_id, p.x, p.y), catalog))
    if not targets:
        return BirthSiteCheck('missing_npc', movement_mask=mask)

    def allowed(npc, point):
        if interaction_allowed is None:
            return (point[0]-npc.x)**2+(point[1]-npc.y)**2 <= interaction_radius**2
        decision = interaction_allowed(npc, (start_map, *point))
        if type(decision) is not bool:
            raise ValueError('Trusted interaction predicate must return a bool')
        return decision

    start = (x, y)
    frontier = deque([start])
    parents = {start: None}
    seen_cells = {(x//16, y//16)}
    budget_hit = False
    width, height = catalog[start_map]['width'], catalog[start_map]['height']
    while frontier:
        point = frontier.popleft()
        target = next((p for p in targets if allowed(p, point)), None)
        if target is not None:
            reverse = []
            cursor = point
            while cursor is not None:
                reverse.append(cursor)
                cursor = parents[cursor]
            return BirthSiteCheck('reachable', tuple(reversed(reverse)), len(parents),
                                  target.placement_id, mask)
        cx, cy = point[0]//16, point[1]//16
        for dx, dy in ((0,-1),(-1,0),(1,0),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)):
            cell = (cx+dx, cy+dy)
            if cell in seen_cells or not 0 <= cell[0] < maze.width or not 0 <= cell[1] < maze.height:
                continue
            candidate = (min(cell[0]*16+8, width-1), min(cell[1]*16+8, height-1))
            if (not valid_position((start_map,*candidate), catalog)
                    or not maze_clear(maze,*candidate,mask=mask)):
                continue
            if not maze_segment_clear(maze,point,candidate,mask=mask):
                continue
            if len(parents) >= max_visited:
                budget_hit = True
                continue
            seen_cells.add(cell)
            parents[candidate] = point
            frontier.append(candidate)
    # Failure only establishes absence on this sampled graph, not native A*.
    return BirthSiteCheck('search_budget' if budget_hit else 'no_witness',
                          visited=len(parents), movement_mask=mask)


def validate_birth_sites(routes, catalog, grids, placements, *, state_byte,
                         interaction_radius=None, max_visited, interaction_allowed=None):
    """Startup-only fail-closed approval of every configured design candidate.

    Dependencies are already loaded snapshots; this performs no file/DB reads.
    Select the same single interaction goal as check_birth_site; production
    callers pass their frozen rules.allows, legacy radius callers stay explicit.
    Shared home/NPC checks are deduplicated across character choices. A missing
    resource, key mismatch, failed witness or budget exhaustion rejects startup
    instead of moving a fresh role to an unvalidated fallback location.
    """
    checks, sites = {}, {}
    for key, route in routes.items():
        if key != (route.character_id,route.school_id):
            raise ValueError('Newbie route key disagrees with character/school')
        grid = grids.get(route.home_map_id)
        if grid is None:
            raise ValueError(f'Newbie home map {route.home_map_id} lacks a loaded maze')
        site = (route.home_map_id,route.cinematic_endpoint,route.first_npc_id)
        if site not in sites:
            sites[site] = check_birth_site(route,catalog,grid,
                placements.get(route.home_map_id,()),state_byte=state_byte,
                interaction_radius=interaction_radius,max_visited=max_visited,
                interaction_allowed=interaction_allowed)
        check = sites[site]
        if check.status != 'reachable':
            raise ValueError(f'Newbie birth candidate {key}: {check.status}')
        checks[key] = check
    return MappingProxyType(checks)


def load_newbie_routes(path=OUT/'catalogs/newbie-routes.json'):
    doc = json.loads(path.read_text(encoding='utf-8'))
    if doc['schema'] != 1 or doc['source_status'] != 'client_verified':
        raise ValueError('Unverified newbie route catalog')
    routes = {}
    for r in doc['routes']:
        route = NewbieRoute(r['role_id'], r['school_id'], r['home_map_id'], r['intro_task_id'],
            r['intro_movie_id'], r['successor_task_id'], r['successor_card_effect_id'], r['first_npc_id'],
            (r['home_map_id'], *r['cinematic_endpoint']['logical_pixels']))
        key = (route.character_id, route.school_id)
        if key in routes:
            raise ValueError('Ambiguous character/school newbie route')
        routes[key] = route
    return MappingProxyType(routes)


class NewbieFlow:
    def __init__(self, resources, routes):
        self.resources, self.routes = resources, routes
        self._ticket = None
        self._completion = None
        for route in routes.values():
            intro = resources.definitions.get(route.intro_task_id)
            successor = resources.definitions.get(route.successor_task_id)
            if (intro is None or successor is None or intro['type'] != 50
                    or int(intro['attributes']['ScenarioInfoAnimationID']) != route.intro_movie_id
                    or int(successor['attributes']['ScenarioInfoAnimationID']) != route.successor_card_effect_id
                    or route.successor_task_id not in intro['next_ids']
                    or route.character_id not in successor['role_config_ids']
                    or successor['target']['map_id'] != route.home_map_id
                    or successor['target']['npc_id'] != route.first_npc_id):
                raise ValueError('Newbie route disagrees with original task resources')

    @classmethod
    def from_ticket(cls, resources, routes, ticket):
        """Rehydrate a LOCAL flow from the role owner's frozen playback ticket.

        This is not a client decoder or durable authorization substitute. The
        storage Adapter separately checks its current chapter/lease/revision;
        finish still checks the current snapshot, location and deadline. The
        worker discards this flow after its transaction. Only the immutable
        ticket crosses owner/I/O execution contexts, preserving source/request
        identities instead of creating a second playback instance.
        """
        if type(ticket) is not IntroTicket:
            raise ValueError('Frozen intro ticket required')
        actor, location = ticket.actor, ticket.location
        if (type(actor) is not TaskActor or type(location) is not Location
                or type(location.address) is not MapAddress
                or type(ticket.route) is not NewbieRoute
                or any(type(v) is not int or v < 1 for v in
                       (actor.account_id,actor.role_id,actor.shape,location.version,
                        location.address.map_id,location.address.instance_id))
                or type(actor.level) is not int or actor.level < 0
                or type(location.address.partition_id) is not int or location.address.partition_id < 0
                or not valid_task_epoch(actor.login_epoch)
                or location.role_id != actor.role_id or location.login_epoch != actor.login_epoch
                or location.state != 'active'
                or any(type(v) is not int or not 0 <= v < 32768 for v in (location.x,location.y))
                or type(ticket.generation) is not int or ticket.generation < 1
                or type(ticket.deadline_ms) is not int or ticket.deadline_ms < 1
                or type(ticket.request_id) is not str or not 1 <= len(ticket.request_id) <= 128
                or type(ticket.source_id) is not str
                or re.fullmatch(r'intro:[0-9a-f]{32}',ticket.source_id) is None):
            raise ValueError('Invalid frozen intro ticket scope')
        route = ticket.route
        if (any(type(v) is not int or v < 1 for v in (
                route.character_id,route.school_id,route.home_map_id,route.intro_task_id,
                route.intro_movie_id,route.successor_task_id,route.successor_card_effect_id,route.first_npc_id))
                or type(route.cinematic_endpoint) is not tuple or len(route.cinematic_endpoint) != 3
                or route.cinematic_endpoint[0] != route.home_map_id
                or any(type(v) is not int or not 0 <= v < 32768 for v in route.cinematic_endpoint[1:])):
            raise ValueError('Invalid frozen intro route structure')
        flow = cls(resources,routes)
        if (flow.route(actor,school_id=ticket.route.school_id) != ticket.route
                or location.address.map_id != ticket.route.home_map_id):
            raise ValueError('Frozen intro ticket disagrees with original route')
        flow._ticket = ticket
        return flow

    def route(self, actor, *, school_id):
        character_id = self.resources.shape_to_role_config.get(actor.shape)
        route = self.routes.get((character_id, school_id))
        if route is None:
            raise ValueError('Character cannot start this school route')
        return route

    def initial_task_plans(self, actor, snapshot, *, school_id):
        """Only the trusted creation workflow may call this for a fresh role.

        The caller proves durable creation provenance, applies both plans in
        its fenced role transaction, and records the newbie chapter instance.
        EXP and this packet's intro discriminator are never authorization.
        Existing story progress must resume through its stored chapter state.
        """
        if snapshot.active or snapshot.completed or snapshot.offered:
            raise ValueError('Existing task progress cannot be initialized as a fresh birth')
        route = self.route(actor, school_id=school_id)
        domain = TaskDomain(self.resources)
        offer = domain.plan(actor, snapshot, 'offer', route.intro_task_id)
        accept = domain.plan(actor, offer.after, 'accept', route.intro_task_id)
        return offer, accept

    def successor_task_plans(self, actor, snapshot, *, school_id):
        """Choose the original role-specific first task after committed intro.

        Activation is distinct from completion. The first NPC conversation's
        own animation, weapon reward and equipment objective stay authoritative
        operations in their existing task/inventory Modules.
        """
        route = self.route(actor, school_id=school_id)
        if snapshot.role_id != actor.role_id or route.intro_task_id not in snapshot.completed:
            raise ValueError('Newbie intro is not committed')
        if route.successor_task_id in snapshot.active | snapshot.completed:
            return ()
        domain = TaskDomain(self.resources)
        plans = ()
        current = snapshot
        if route.successor_task_id not in snapshot.offered:
            offer = domain.plan(actor, snapshot, 'offer', route.successor_task_id)
            plans = (offer,)
            current = offer.after
        return plans+(domain.plan(actor,current,'accept',route.successor_task_id),)

    @staticmethod
    def _scope(actor, snapshot, location, generation):
        if (not valid_task_epoch(actor.login_epoch) or actor.role_id != snapshot.role_id
                or location.role_id != actor.role_id or location.login_epoch != actor.login_epoch
                or location.state != 'active' or type(generation) is not int or generation < 1):
            raise ValueError('Invalid newbie role/connection scope')

    def start(self, actor, snapshot, location, *, school_id, generation, request_id,
              now_ms, deadline_ms):
        """After durable task authorization and scene entry, emit the real CG.

        The role owner persists its activation/playback journal and blocks world
        actions for the ticket's lifetime. This Module neither activates a quest
        from EXP nor writes a spawn, changes a lease, or sends network bytes.
        """
        self._scope(actor, snapshot, location, generation)
        route = self.route(actor, school_id=school_id)
        if (route.intro_task_id not in snapshot.active or route.intro_task_id in snapshot.completed
                or location.address.map_id != route.home_map_id
                or type(request_id) is not str or not 1 <= len(request_id) <= 128
                or now_ms >= deadline_ms):
            raise ValueError('Intro requires an authorized active school task and home scene')
        if self._ticket is not None:
            t = self._ticket
            if (t.actor != actor or t.location != location or t.generation != generation
                    or t.route != route or t.request_id != request_id or t.deadline_ms != deadline_ms):
                raise ValueError('Another newbie intro is pending')
        else:
            self._ticket = IntroTicket(actor, location, generation, route, request_id,
                                       'intro:'+uuid4().hex, deadline_ms)
            self._completion = None
        return self._ticket, ((START_PLAY_CG, struct.pack('>i', route.intro_movie_id)),)

    def finish(self, body, actor, snapshot, location, *, generation, now_ms):
        """Validate CEndPlayCG against the one authorized playback instance.

        The returned evidence is usable by the existing TaskDomain/transaction.
        Keep this ticket until that transaction has committed successfully.
        Arbitrary movie IDs, another connection and changed map/position fail.
        """
        self._scope(actor, snapshot, location, generation)
        t = self._ticket
        if (t is None or not isinstance(body, bytes) or len(body) != 4
                or struct.unpack('>i', body)[0] != t.route.intro_movie_id
                or t.actor != actor or t.location != location or t.generation != generation
                or now_ms >= t.deadline_ms or t.route.intro_task_id not in snapshot.active):
            raise ValueError('Unsolicited or stale intro completion')
        if self._completion is None:
            self._completion = TaskEvidence(t.route.intro_task_id, actor.role_id, actor.login_epoch,
                'scenario_finished', t.source_id, location.address.map_id,
                reference_id=t.route.intro_movie_id)
        return self._completion

    def committed(self, evidence):
        """Role owner calls only after its existing task/reward transaction commits."""
        if self._completion is None or evidence != self._completion:
            raise ValueError('Intro completion has not been validated')
        self._ticket = self._completion = None

    def cancel(self):
        """Drop local authorization on logout/map change; no client or DB mutation."""
        self._ticket = self._completion = None

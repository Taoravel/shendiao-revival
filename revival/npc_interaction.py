"""Startup-frozen NPC proximity; legacy circles and exact current cell policy."""
from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from inspect_client import OUT


@dataclass(frozen=True)
class NpcInteractionOverride:
    map_id: int
    placement_id: int
    npc_id: int
    radius: int
    original_x: int
    original_y: int


@dataclass(frozen=True)
class NpcInteractionRules:
    revision: str
    default_radius: int | None
    overrides: tuple
    distance_mode: str = 'logical_pixel_circle'
    logical_pixels_per_cell: int | None = None
    cell_distance_limit_exclusive: int | None = None
    cell_squared_distance_limit_exclusive: int | None = None

    def __post_init__(self):
        cells=(self.logical_pixels_per_cell,self.cell_distance_limit_exclusive,
            self.cell_squared_distance_limit_exclusive)
        legacy=(self.revision=='2026-10-23.npc-interaction.1'
                and self.distance_mode=='logical_pixel_circle'
                and type(self.default_radius) is int and self.default_radius==32
                and type(self.overrides) is tuple
                and not any(type(row) is not NpcInteractionOverride or any(type(v) is not int for v in
                    (row.map_id,row.placement_id,row.npc_id,row.radius,row.original_x,row.original_y))
                    for row in self.overrides)
                and self.overrides==(NpcInteractionOverride(1006,13,10498,48,1668,970),)
                and cells==(None,None,None))
        current=(self.revision=='2026-10-23.npc-interaction.2'
                and self.distance_mode=='logical_cell_euclidean' and self.default_radius is None
                and type(self.overrides) is tuple and self.overrides==()
                and all(type(value) is int for value in cells) and cells==(16,13,169))
        if not (legacy or current):
            raise ValueError('Explicit supported NPC interaction policy required')

    def radius_for(self,map_id,placement_id,npc_id):
        if self.default_radius is None:
            raise ValueError('NPC cell policy is not a pixel circle; use allows')
        if any(type(v) is not int or v<=0 for v in (map_id,placement_id,npc_id)):
            raise ValueError('Current exact NPC placement identity required')
        return next((row.radius for row in self.overrides
            if (row.map_id,row.placement_id,row.npc_id)==(map_id,placement_id,npc_id)),self.default_radius)

    def allows(self,npc,role_position):
        """Proximity only, with one three-part logical position shape.

        The owner still proves full address, role/position freshness and current
        entity binding before calling. This grants no task or asset authority.
        """
        if (type(role_position) is not tuple or len(role_position)!=3
                or any(type(value) is not int or value<0 for value in role_position)
                or role_position[0]==0
                or role_position[0]!=npc.map_id
                or any(type(value) is not int or value<0 for value in (npc.map_id,npc.x,npc.y))):
            return False
        _,x,y=role_position
        if self.default_radius is not None:
            radius=self.radius_for(npc.map_id,npc.placement_id,npc.npc_id)
            return (x-npc.x)**2+(y-npc.y)**2<=radius**2
        size=self.logical_pixels_per_cell
        return (x//size-npc.x//size)**2+(y//size-npc.y//size)**2<self.cell_squared_distance_limit_exclusive


def resolve_interaction_radius(rules,radius):
    """Constructor compatibility only; current cell rules have no circle.

    Existing explicit32 callers may migrate without redefining v2 admission.
    New callers can omit it; allows remains the sole configured predicate.
    """
    if rules is None:return radius
    if type(rules) is not NpcInteractionRules:
        raise ValueError('Frozen supported NPC interaction rules required')
    if radius is not None and (type(radius) is not int or radius!=32):
        raise ValueError('NPC legacy radius must match the original32 constructor contract')
    return rules.default_radius


def load_npc_interaction_rules(placements,definitions,path=None):
    """Startup only: validate the approved original placement before activation."""
    policy=json.loads((Path(path) if path is not None else OUT/'design/npc-interaction-v2.json')
        .read_text(encoding='utf-8'))
    if type(policy) is dict and policy.get('revision')=='2026-10-23.npc-interaction.2':
        if 'overrides' in policy or 'default_radius' in policy:
            raise ValueError('NPC cell policy cannot include circle overrides')
        rules=NpcInteractionRules(policy['revision'],None,(),policy.get('distance_mode'),
            policy.get('logical_pixels_per_cell'),policy.get('cell_distance_limit_exclusive'),
            policy.get('cell_squared_distance_limit_exclusive'))
        if not isinstance(placements,Mapping) or not isinstance(definitions,Mapping) or not placements:
            raise ValueError('Current original NPC resource snapshots required')
        for map_id,rows in placements.items():
            if type(map_id) is not int or map_id<=0:raise ValueError('Invalid original NPC map identity')
            seen=set()
            for p in rows:
                values=tuple(getattr(p,key,None) for key in ('map_id','placement_id','npc_id','x','y'))
                if any(type(v) is not int for v in values):
                    raise ValueError('Integer original NPC placement fields required')
                definition=definitions.get(values[2])
                if (values[0]!=map_id
                        or values[1]<=0 or values[1] in seen or values[2]<=0
                        or not all(0<=v<32768 for v in values[3:])
                        or not isinstance(definition,Mapping) or str(definition.get('id'))!=str(values[2])):
                    raise ValueError('Invalid or mismatched original NPC placement/definition')
                seen.add(values[1])
        return rules
    if (type(policy) is not dict or type(policy.get('overrides')) is not list
            or not all(type(row) is dict for row in policy['overrides'])):
        raise ValueError('Invalid NPC interaction policy structure')
    fields=('map_id','placement_id','npc_id','radius','original_x','original_y')
    if any(any(name not in row for name in fields) for row in policy['overrides']):
        raise ValueError('Incomplete NPC interaction override')
    rules=NpcInteractionRules(policy.get('revision'),policy.get('default_radius'),
        tuple(NpcInteractionOverride(*(row[name] for name in fields)) for row in policy['overrides']))
    for row in rules.overrides:
        original=tuple(p for p in placements.get(row.map_id,()) if p.placement_id==row.placement_id)
        definition=definitions.get(row.npc_id)
        if (not isinstance(definition,Mapping) or str(definition.get('id'))!=str(row.npc_id) or len(original)!=1
                or (original[0].map_id,original[0].npc_id,original[0].x,original[0].y)
                    !=(row.map_id,row.npc_id,row.original_x,row.original_y)):
            raise ValueError('NPC interaction override requires its exact original placement')
    return rules


def prepare(accounts,*,path=None):
    """Call at startup before map creation; preserve the NPC resource tuple."""
    rules=load_npc_interaction_rules(*accounts.npc_resources,path=path)
    accounts.npc_interaction_rules=rules
    return rules

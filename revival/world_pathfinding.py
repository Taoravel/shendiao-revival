"""Pure bounded port of the original 0x6212f0 grid search.

Grid coordinates, explicit native mask and explicit caller budgets only. This
returns planning advice, never permission to move or proof of client travel.
The actor/click target adjustment and 0x6138d0 pixel wrapper are separate layers.
The original kernel can leave a blocked start: callers must independently
validate their authoritative start before using any resulting route.
"""
from dataclasses import dataclass
from math import isqrt
from world_grids import SceneGrid
from world_collision import maze_segment_result


@dataclass(frozen=True)
class GridPathResult:
    status: str
    path: tuple
    expanded_nodes: int
    discovered_nodes: int


@dataclass(frozen=True)
class PixelPathResult:
    status: str
    native_result: int | None
    points: tuple
    expanded_nodes: int
    discovered_nodes: int
    sample_budget_used: int


@dataclass
class _Node:
    point: tuple
    parent: object = None
    g: int = 0
    f: int = 0
    closed: bool = False
    index: int = 0


class _Heap:
    """Native f-only order: stable rise; equal children select the right."""
    def __init__(self):
        self.items=[]

    def rise(self,node):
        at=node.index
        while at:
            parent=(at-1)//2
            if self.items[parent].f<=node.f:
                break
            self.items[at]=self.items[parent]
            self.items[at].index=at
            at=parent
        self.items[at]=node
        node.index=at

    def push(self,node):
        node.index=len(self.items)
        self.items.append(node)
        self.rise(node)

    def pop(self):
        first=self.items[0]
        last=self.items.pop()
        if self.items:
            at=0
            while at*2+1<len(self.items):
                child=at*2+1
                if child+1<len(self.items) and self.items[child+1].f<=self.items[child].f:
                    child+=1
                if self.items[child].f>=last.f:
                    break
                self.items[at]=self.items[child]
                self.items[at].index=at
                at=child
            self.items[at]=last
            last.index=at
        return first


def find_grid_path(grid,start,end,*,mask,max_expansions,max_nodes):
    """Return an immutable forward grid path, excluding start, including end.

    Mirrors native neighbor order, 5/7 costs, integer-distance heuristic,
    f-only heap and target-discovered termination. Grid dimensions are limited
    to the native 1920 cap. All input positions must be in that dense grid.
    Budgets are caller-designed safeguards, NOT original server parameters.
    'budget' returns no partial route and does not mean 'not_found'. No I/O,
    cache, actor/owner mutation or production defaults are introduced here.
    """
    if (type(grid) is not SceneGrid or type(grid.cells) is not bytes
            or grid.present is not None
            or any(type(n) is not int or not 1<=n<=1920 for n in (grid.width,grid.height))
            or len(grid.cells)!=grid.width*grid.height):
        raise ValueError('Dense native grid with dimensions 1..1920 required')
    if (type(mask) is not int or not 0<=mask<=255
            or any(type(n) is not int or n<1 for n in (max_expansions,max_nodes))):
        raise ValueError('Explicit byte mask and positive search budgets required')
    for point in (start,end):
        if (type(point) is not tuple or len(point)!=2
                or any(type(n) is not int for n in point)
                or not 0<=point[0]<grid.width or not 0<=point[1]<grid.height):
            raise ValueError('Two in-bounds native grid coordinate tuples required')
    if start==end:
        return GridPathResult('same_cell',(),0,0)
    def clear(point):
        return not (grid.cells[point[1]*grid.width+point[0]]&mask)
    if not clear(end):
        return GridPathResult('blocked_goal',(),0,0)
    root=_Node(start)
    nodes={start:root}
    heap=_Heap();heap.push(root)
    expanded=0
    while heap.items:
        if expanded>=max_expansions:
            return GridPathResult('budget',(),expanded,len(nodes))
        current=heap.pop();current.closed=True
        expanded+=1
        x,y=current.point
        for dx,dy in ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)):
            point=(x+dx,y+dy)
            if not 0<=point[0]<grid.width or not 0<=point[1]<grid.height or not clear(point):
                continue
            if dx and dy and (not clear((x+dx,y)) or not clear((x,y+dy))):
                continue
            node=nodes.get(point)
            if node is not None and node.closed:
                continue
            cost=current.g+(7 if dx and dy else 5)
            if node is None:
                if len(nodes)>=max_nodes:
                    return GridPathResult('budget',(),expanded,len(nodes))
                # Original 0x5f87e0 equals floor sqrt throughout the squared
                # distance domain induced by coordinates 0..1919; separately
                # checked against original instructions, not Python hypot.
                distance=isqrt((end[0]-point[0])**2+(end[1]-point[1])**2)
                node=_Node(point,current,cost,cost+5*distance)
                nodes[point]=node
                heap.push(node)
            elif cost<node.g:
                node.f+=cost-node.g
                node.g=cost;node.parent=current
                heap.rise(node)
        goal=nodes.get(end)
        if goal is not None and not goal.closed:
            reverse=[]
            while goal is not root:
                reverse.append(goal.point)
                goal=goal.parent
            return GridPathResult('found',tuple(reversed(reverse)),expanded,len(nodes))
    return GridPathResult('not_found',(),expanded,len(nodes))


def find_pixel_path(grid,start,end,*,mask,max_expansions,max_nodes,max_samples):
    """Port 0x6138d0's mode0/zero-distance-limits path for integer pixels.

    Preserve its initial DDA shortcut and 0x61bc60 sequential compression for
    both short and long searches. Search endpoints become grid centers; a
    direct clear leg retains the exact requested pixel. No click adjustment,
    float current reconstruction or automatic world movement is performed.

    max_samples is a conservative work reservation: before each DDA, charge
    its full major-axis length even if a wall would stop it early. This bounds
    the real sample count from above. Insufficient budget returns no partial
    route, with native_result=None, distinct from native failure/same-point.
    """
    if (type(grid) is not SceneGrid or type(grid.cells) is not bytes
            or grid.present is not None
            or any(type(n) is not int or not 1<=n<=1920 for n in (grid.width,grid.height))
            or len(grid.cells)!=grid.width*grid.height):
        raise ValueError('Dense native grid with dimensions 1..1920 required')
    if (type(mask) is not int or not 0<=mask<=255
            or any(type(n) is not int or n<1 for n in (max_expansions,max_nodes,max_samples))):
        raise ValueError('Explicit byte mask and positive search/sample budgets required')
    for point in (start,end):
        if (type(point) is not tuple or len(point)!=2
                or any(type(n) is not int for n in point)
                or not 0<=point[0]<grid.width*16 or not 0<=point[1]<grid.height*16):
            raise ValueError('Two in-bounds nonnegative logical integer pixel tuples required')
    used=0
    def query(a,b):
        nonlocal used
        cost=max(abs(a[0]-b[0]),abs(a[1]-b[1]))
        if used+cost>max_samples:
            return None
        used+=cost
        return maze_segment_result(grid,a,b,mask=mask)
    code=query(start,end)
    if code is None:
        return PixelPathResult('budget',None,(),0,0,used)
    if code==0:
        return PixelPathResult('found',0,(end,),0,0,used)
    if code==3:
        return PixelPathResult('same_point',3,(),0,0,used)
    raw=find_grid_path(grid,(start[0]//16,start[1]//16),(end[0]//16,end[1]//16),
        mask=mask,max_expansions=max_expansions,max_nodes=max_nodes)
    if raw.status!='found':
        budget=raw.status=='budget'
        return PixelPathResult('budget' if budget else 'not_found',None if budget else 1,(),
            raw.expanded_nodes,raw.discovered_nodes,used)
    centers=tuple((x*16+8,y*16+8) for x,y in raw.path)
    anchor=start
    previous=centers[0]
    points=[]
    for candidate in centers[1:]:
        result=query(anchor,candidate)
        if result is None:
            return PixelPathResult('budget',None,(),raw.expanded_nodes,raw.discovered_nodes,used)
        if result==1:
            points.append(previous)
            anchor=previous
        previous=candidate
    if previous!=anchor:
        points.append(previous)
    return PixelPathResult('found' if points else 'not_found',0 if points else 2,
        tuple(points),raw.expanded_nodes,raw.discovered_nodes,used)

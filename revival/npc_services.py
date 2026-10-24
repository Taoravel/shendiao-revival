"""Startup-only service policy; pure map-proof to role-owner command seam.

No default NPC/service guesses. Plans are intents, never success receipts.
The role owner must recheck its lease/deadline and settle through the owning
module. No Session, mutable asset, database connection or network is retained.
"""
from dataclasses import dataclass
import json
from types import MappingProxyType
from inspect_client import OUT
from world_npcs import NpcInteraction
from world_entity_protocol import read_npc_service, visit_npc_reply


def load_services(bindings=(), path=OUT/'catalogs/knight.gsp.npc.cnpcserverconfig.json', *, menu_groups=()):
    """Startup only: original labels plus explicit, reviewed NPC/handler policy."""
    rows = json.loads(path.read_text(encoding='utf-8'))
    labels = {};children={}
    for row in rows:
        ident = int(row['attributes']['id'])
        if ident in labels:
            raise ValueError('Duplicate NPC service definition')
        labels[ident] = row['attributes'].get('severStr', '')
        children[ident]=tuple(map(int,row.get('lists',{}).get('childservice',())))
    return NpcServices(labels, bindings,child_services=children,menu_groups=menu_groups)


@dataclass(frozen=True)
class ServiceBinding:
    npc_id: int
    service_id: int
    handler: str
    source_status: str
    evidence: str


@dataclass(frozen=True)
class NpcServiceCommand:
    request_id: str
    deadline_ms: int
    role_id: int
    login_epoch: int | str
    address: object
    position_version: int
    entity_key: int
    npc_id: int
    placement_id: int
    service_id: int
    handler: str
    source_status: str
    evidence: str


class NpcServices:
    def __init__(self, service_labels, bindings=(), *, child_services=None,menu_groups=()):
        self.labels = MappingProxyType(dict(service_labels))
        policy = {}
        for b in bindings:
            key = (b.npc_id, b.service_id)
            if (b.npc_id <= 0 or b.service_id not in self.labels or key in policy
                    or b.service_id in (10001,10002,10003,10004)
                    or not 0 < b.service_id <= 0x7fffffff or not b.handler or not b.evidence
                    or b.source_status not in ('client_verified', 'guide_supported', 'designed')):
                raise ValueError('Invalid or duplicate explicit NPC service binding')
            policy[key] = b
        self.bindings = MappingProxyType(policy)
        children={key:tuple(ids) for key,ids in (child_services or {}).items()}
        if any(key not in self.labels or len(ids)>4096 or len(set(ids))!=len(ids)
               or any(type(ident) is not int or not 0<ident<=0x7fffffff for ident in ids)
               for key,ids in children.items()):
            raise ValueError('Invalid NPC child-service catalog')
        self.children=MappingProxyType(children)
        menus = {}
        for npc_id, service_id in policy:
            menus.setdefault(npc_id, []).append(service_id)
        grouped={};roots=set()
        for group in menu_groups:
            if (type(group) is not tuple or len(group)!=2 or any(type(i) is not int or i<=0 for i in group)
                    or group in roots):
                raise ValueError('Explicit NPC display group required')
            npc_id,root_id=group
            leaves,local_services=self._group_members(root_id)
            if (any((npc_id,leaf) not in policy for leaf in leaves)
                    or any((npc_id,service) in policy for service in local_services)
                    or leaves & grouped.get(npc_id,set())):
                raise ValueError('NPC submenu has conflicting local actions or unauthorized/overlapping leaves')
            roots.add(group);grouped.setdefault(npc_id,set()).update(leaves)
            menus[npc_id]=[i for i in menus.get(npc_id,()) if i not in leaves]+[root_id]
        if any(len(ids) > 4096 for ids in menus.values()):
            raise ValueError('NPC service menu capacity')
        self.menus = MappingProxyType({key: tuple(sorted(ids)) for key, ids in menus.items()})

    def _group_members(self,root):
        """Startup-only exact client tree; display parents grant no commands.

        Unused broken references in the original catalog stay unactivated.
        Every exposed action leaf must have this NPC's separate real binding.
        Native10001..10004 navigate cached menus or call the local window;
        none grants a server action permission, including pure information trees.
        """
        if not self.children.get(root):raise ValueError('NPC display root has no original children')
        pending=[(root,False)];active=set();visited=set();leaves=set();steps=0
        while pending:
            ident,finished=pending.pop();steps+=1
            if steps>16384 or len(visited)+len(active)>4096:raise ValueError('NPC submenu traversal capacity')
            if finished:
                active.remove(ident);visited.add(ident);continue
            if ident in active:raise ValueError('Cyclic NPC submenu')
            if ident in visited:continue
            if ident not in self.labels:raise ValueError('Unknown NPC child service')
            ids=self.children.get(ident,())
            if ident in (10001,10002,10003,10004):
                if ids:raise ValueError('Native local navigation cannot contain actions')
                visited.add(ident)
            elif not ids:
                leaves.add(ident);visited.add(ident)
            else:
                active.add(ident);pending.append((ident,True))
                pending.extend((child,False) for child in reversed(ids))
        return leaves,visited-leaves

    @staticmethod
    def _scope(proof, current):
        if (not isinstance(proof, NpcInteraction) or proof.kind != 'npc_interacted'
                or proof.position_validation != 'bounds_version_distance'
                or (proof.role_id, proof.login_epoch, proof.address, proof.position_version)
                != (current.role_id, current.login_epoch, current.address, current.version)
                or current.state != 'active'):
            raise ValueError('Stale NPC service scope')

    def menu(self, proof, current, *, quest_ids=()):
        """Return native SVisitNpc body; the task owner supplies vector 2."""
        self._scope(proof, current)
        return visit_npc_reply(proof.entity_key, self.menus.get(proof.npc_id, ()), quest_ids)

    def plan(self, body, proof, current, *, request_id, now_ms, deadline_ms):
        self._scope(proof, current)
        if (not request_id or len(request_id) > 128 or request_id != proof.source_id
                or now_ms >= deadline_ms):
            raise ValueError('Invalid or expired NPC service request')
        key, service_id = read_npc_service(body)
        binding = self.bindings.get((proof.npc_id, service_id))
        if key != proof.entity_key or binding is None:
            raise ValueError('NPC service is not authorized')
        return NpcServiceCommand(request_id, deadline_ms, proof.role_id, proof.login_epoch,
            proof.address, proof.position_version, key, proof.npc_id, proof.placement_id,
            service_id, binding.handler, binding.source_status, binding.evidence)

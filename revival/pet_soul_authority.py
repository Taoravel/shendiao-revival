"""Compose current external operation clearance with actual Mingwen source22.

No wire-supplied permission/flag, source mutation or missing-ledger fallback.
World/operation and actual material flags still belong to their trusted owner.
"""
from dataclasses import dataclass
import hashlib
import inspect
import json
from pet_soul_actions import SoulActionAuthority
from role_mingwen import MingwenRules,read


@dataclass(frozen=True)
class SoulOperationClearance:
    role_id: int
    pet_id: int
    login_epoch: int | str
    policy: str
    version: int
    allowed: bool
    material_flags: tuple

    def __post_init__(self):
        if (type(self.role_id) is not int or not 0<self.role_id<2**63
                or type(self.pet_id) is not int or not 0<self.pet_id<=0x7fffffff
                or not (type(self.login_epoch) is int and 0<self.login_epoch<2**63
                    or type(self.login_epoch) is str and 1<=len(self.login_epoch)<=128)
                or type(self.policy) is not str or not 1<=len(self.policy)<=160
                or type(self.version) is not int or not 0<=self.version<2**63-1
                or type(self.allowed) is not bool or type(self.material_flags) is not tuple or len(self.material_flags)>40
                or any(type(p) is not tuple or len(p)!=2 or type(p[0]) is not int or not 0<p[0]<=0x7fffffff
                    or type(p[1]) is not int or not 0<=p[1]<=0xfffffffe or p[1]&1 for p in self.material_flags)
                or tuple(p[0] for p in self.material_flags)!=tuple(sorted({p[0] for p in self.material_flags}))):
            raise ValueError('Complete current owned operation clearance without invented inscription flags required')


def resolve(db,inventory,rules,pet_id,material_keys,*,clearance_reader):
    """Reader for the actual soul controller's authority_reader Interface.

    Hash only the independent source history, not inventory revision or material
    list: own asset writes/consumption cannot change clearance identity. Current
    Mingwen changes and the external clearance version still fence new payment.
    """
    if (type(rules) is not MingwenRules or type(pet_id) is not int or not 0<pet_id<=0x7fffffff
            or type(material_keys) is not tuple or len(material_keys)>40
            or any(type(key) is not int or not 0<key<=0x7fffffff for key in material_keys)
            or material_keys!=tuple(sorted(set(material_keys))) or not callable(clearance_reader)):
        raise ValueError('Trusted current soul clearance reader and exact material keys required')
    snapshot=inventory.immutable_snapshot_transaction(db)
    if not any(p.id==pet_id and p.role_id==inventory.role_id and p.released==0 for p in snapshot.pets):
        raise ValueError('Current owned unreleased pet required for soul clearance')
    clearance=clearance_reader(db,inventory,pet_id,material_keys)
    if inspect.isawaitable(clearance):
        if inspect.iscoroutine(clearance):clearance.close()
        raise ValueError('Soul operation clearance must complete synchronously')
    if (type(clearance) is not SoulOperationClearance or clearance.role_id!=inventory.role_id
            or clearance.pet_id!=pet_id or clearance.login_epoch!=inventory.epoch
            or tuple(key for key,_ in clearance.material_flags)!=material_keys):
        raise ValueError('Missing, incomplete or stale real operation clearance')
    source=read(db,inventory,rules)
    if source is None:raise ValueError('Mingwen22 source is unknown, never implicitly inactive')
    stamp=json.dumps([clearance.policy,rules.revision,source.origin,source.baseline_source,source.raw_state],
        ensure_ascii=False,separators=(',',':')).encode('utf-8')
    policy='2026-10-24.soul-mingwen-clearance.1:'+hashlib.sha256(stamp).hexdigest()
    return SoulActionAuthority(inventory.role_id,pet_id,inventory.epoch,policy,clearance.version,
        clearance.allowed,source.state.soul_cap_increment,clearance.material_flags)

"""No-award producer for a retired old-lease Task combat checkpoint.

Caller must have acquired the new role lease and fenced the old host, verified
its durable admission/checkpoint and confirmed that NO terminal is recorded.
Existing producer terminals always take precedence and are never replaced here.
"""
from dataclasses import replace
from battle import Fighter
from battle_owner import Participant, BattleSnapshot
from battle_loadout import CombatResources
from training_battle import BattleFinished
from task_pve import TaskPveRules


def abort_checkpoint_terminal(participant, snapshot, rules, *, current_epoch):
    """Keep actual raw losses, original event identity, and no task victory."""
    if (type(participant) is not Participant or type(snapshot) is not BattleSnapshot
            or type(rules) is not TaskPveRules
            or not ((type(current_epoch) is int and current_epoch>0)
                or (type(current_epoch) is str and 1<=len(current_epoch)<=128))
            or str(current_epoch)==str(participant.login_epoch)
            or type(snapshot.battle_id) is not str or not 1<=len(snapshot.battle_id)<=128
            or type(snapshot.state_version) is not int or snapshot.state_version<1
            or type(snapshot.round_number) is not int or not 1<=snapshot.round_number<=rules.max_rounds
            or snapshot.phase not in ('commands','playback')):
        raise ValueError('Retired previous lease and complete persisted active checkpoint required')
    initial=(replace(participant.stats,skills=()),rules.enemy)
    if participant.pet is not None:initial+=(participant.pet.stats,)
    initial=tuple(sorted(initial,key=lambda fighter:fighter.id))
    if type(snapshot.fighters) is not tuple or len(snapshot.fighters)!=len(initial):
        raise ValueError('Checkpoint differs from original admitted roster')
    for before,after in zip(initial,snapshot.fighters):
        if (type(after) is not Fighter or replace(after,hp=before.hp,mp=before.mp)!=before
                or type(after.hp) is not int or type(after.mp) is not int
                or not 0<=after.hp<=before.hp or not 0<=after.mp<=before.mp):
            raise ValueError('Recovery checkpoint changed stats or increased original resources')
    by_id={fighter.id:fighter for fighter in snapshot.fighters}
    role=by_id[1]
    resources=[CombatResources('role',participant.role_id,1,participant.attribute_version,
        role.hp,role.max_hp,role.mp,role.max_mp,False)]
    if participant.pet is not None:
        pet=participant.pet;raw=by_id[pet.position]
        resources.append(CombatResources('pet',pet.key,pet.position,pet.growth_version,
            raw.hp,raw.max_hp,raw.mp,raw.max_mp,False,pet.inventory_revision,pet.growth_revision))
    return BattleFinished(snapshot.battle_id,'task-battle:'+snapshot.battle_id,
        participant.role_id,-1,False,snapshot.round_number,rules.revision,
        participant.login_epoch,participant.attribute_version,scope='task_quest_v1',
        task_event_eligible=True,outcome='draw',combat_resources=tuple(resources))

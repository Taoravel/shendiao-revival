"""Pure conversion of role-owned immutable pet state into battle messages.

The role owner obtains InventorySnapshot on its fenced storage worker, then
calls selected_pet before handing the result to the battle owner. No storage,
configuration loading, learning, growth generation or resource writes occur here.
"""
from dataclasses import dataclass
from battle import Fighter


@dataclass(frozen=True)
class PetTemplate:
    id: int
    shape: int
    take_level: int
    use_level: int


@dataclass(frozen=True)
class OwnedBattlePet:
    role_id: int
    key: int
    template_id: int
    inventory_revision: int
    growth_version: int
    growth_revision: str
    name: str
    level: int
    position: int
    shape: int
    stats: Fighter
    max_mp: int
    selected: bool = True


@dataclass(frozen=True)
class CombatResources:
    """Terminal combat copy, not an instruction to write resources or rewards.

    Source version is the role attribute version or the pet growth version.
    Fixture resources never authorize persisted-resource reconciliation.
    """
    kind: str
    entity_id: int
    position: int
    source_version: int
    hp: int
    max_hp: int
    mp: int
    max_mp: int
    escaped: bool
    inventory_revision: int | None = None
    growth_revision: str = ''


def selected_pet(snapshot, *, role_id, role_level, templates, growth_revision, position=6):
    """Copy the one selected, living pet from a trusted InventorySnapshot.

    Missing growth requires explicit inventory migration; it is never replaced
    with training fixture stats. A valid dead selected pet stays in the save but
    does not join. The caller fences the snapshot to its current role lease and
    serializes asset/selection changes while this battle owns the combat copy.
    """
    if (snapshot.role_id != role_id or type(snapshot.pets) is not tuple
            or type(snapshot.inventory_revision) is not int or snapshot.inventory_revision < 0
            or type(role_level) is not int or role_level < 1
            or type(position) is not int or not 2 <= position <= 14
            or type(templates) is not tuple or type(growth_revision) is not str or not growth_revision):
        raise ValueError('Trusted versioned role inventory and startup pet rules required')
    chosen = tuple(pet for pet in snapshot.pets if pet.fighting and not pet.released)
    if len(chosen) > 1:
        raise ValueError('Only one selected pet can join this battle')
    if not chosen:
        return None
    pet = chosen[0]
    template = next((row for row in templates if row.id == pet.template_id), None)
    progress = pet.progress
    if (pet.role_id != role_id or pet.id < 1 or pet.fighting != 1 or pet.released != 0
            or template is None or template.shape < 1
            or role_level < max(template.take_level, template.use_level)
            or progress is None or progress.role_id != role_id or progress.pet_id != pet.id
            or progress.profile.template_id != pet.template_id):
        raise ValueError('Selected pet needs owned eligible persisted growth')
    state, attr = progress.state, progress.attributes
    values = (state.version, state.level, state.hp, state.mp, attr.max_hp,
              attr.max_mp, attr.physical_attack, attr.physical_defense, attr.speed)
    if (any(type(value) is not int for value in values)
            or state.version < 0 or state.level < 1
            or not 0 <= state.hp <= attr.max_hp or attr.max_hp < 1
            or not 0 <= state.mp <= attr.max_mp
            or min(attr.max_mp, attr.physical_attack, attr.physical_defense, attr.speed) < 0
            or max(values) > 0x7fffffff or not pet.name or len(pet.name) > 8):
        raise ValueError('Invalid persisted pet combat resources')
    if state.hp == 0:
        return None
    return OwnedBattlePet(role_id, pet.id, pet.template_id, snapshot.inventory_revision,
                          state.version, growth_revision, pet.name, state.level, position,
                          template.shape, Fighter(position, 0, state.hp, attr.max_hp, state.mp,
                                                  attr.physical_attack, attr.physical_defense, attr.speed,
                                                  max_mp=attr.max_mp),
                          attr.max_mp)

"""Pure consumable effects. Caller owns/persists the returned target snapshot."""
from dataclasses import dataclass, replace
from decimal import Decimal
import json
from types import MappingProxyType
from inspect_client import OUT


@dataclass(frozen=True)
class VitalState:
    target_id: int
    version: int
    hp: int
    max_hp: int
    mp: int
    max_mp: int

    def __post_init__(self):
        if (self.target_id <= 0 or self.version < 0 or self.max_hp <= 0
                or self.max_mp < 0 or not 0 <= self.hp <= self.max_hp
                or not 0 <= self.mp <= self.max_mp):
            raise ValueError('Invalid target vital snapshot')


@dataclass(frozen=True)
class Consumables:
    effects: object
    formulas: object

    @classmethod
    def load(cls):
        def rows(name):
            return json.loads((OUT / f'catalogs/knight.gsp.item.{name}.json').read_text(encoding='utf-8'))
        effects = {int(x['attributes']['id']): (int(x['attributes']['funtionid']), tuple(map(int, x['lists'].get('effect', []))))
                   for x in rows('cfoodanddrugeffect')}
        formulas = {int(x['attributes']['id']): tuple(zip(map(Decimal, x['lists'].get('ai', [])), map(int, x['lists'].get('bi', []))))
                    for x in rows('cfooddrugeffectformula')}
        return cls(MappingProxyType(effects), MappingProxyType(formulas))

    def apply(self, template_id, target, quality=None):
        if not isinstance(target, VitalState) or target.hp == 0:
            raise ValueError('Healing requires a living target')
        rule = self.effects.get(template_id)
        if rule is None or rule[0] not in (1, 2, 4):
            raise ValueError('Consumable effect requires another handler')
        kind, amounts = rule
        if template_id in self.formulas:
            if type(quality) is not int or not 0 <= quality <= 0x7fffffff:
                raise ValueError('Server-owned item quality required')
            # Native tooltip 1081a59..1081a70: abs(quality * ai + bi).
            # Decimal and truncation define this restoration's deterministic math.
            amounts = tuple(int(abs(quality * a + b)) for a,b in self.formulas[template_id])
        required = 2 if kind == 4 else 1
        if len(amounts) < required:
            raise ValueError('Missing consumable effect parameters')
        hp, mp = target.hp, target.mp
        if kind in (1, 4):
            hp = min(target.max_hp, hp + amounts[0])
        if kind in (2, 4):
            mp = min(target.max_mp, mp + amounts[1 if kind == 4 else 0])
        if (hp, mp) == (target.hp, target.mp):
            raise ValueError('Consumable would have no effect')
        return replace(target, version=target.version + 1, hp=hp, mp=mp)

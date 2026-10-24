"""Startup-only ordinary shop payment recipes; no wallet or inventory writes."""
from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from inspect_client import OUT


@dataclass(frozen=True)
class ShopPayment:
    mode: int
    currency: str
    purpose: str
    binding: int


@dataclass(frozen=True)
class ShopPayments:
    revision: str
    modes: object

    def recipe(self,mode):
        if type(mode) is not int or mode not in self.modes:
            raise ValueError('Unsupported ordinary NPC shop payment mode')
        return self.modes[mode]


def load_shop_payments(path=None):
    """Load the approved two-mode recipe once; changed semantics need review."""
    policy=json.loads((Path(path) if path is not None else
        OUT/'design/npc-shop-payments-v1.json').read_text(encoding='utf-8'))
    revision=policy['revision'];modes=policy['modes']
    if (type(revision) is not str or not 1<=len(revision)<=128
            or type(modes) is not dict or set(modes)!={'0','1'}):
        raise ValueError('Explicit ordinary NPC shop payment policy required')
    recipes={}
    for mode,currency,purpose,binding in ((0,'cash','npc_shop',0),(1,'bound_silver','npc_shop_bound',1)):
        row=modes[str(mode)]
        if (row['currency']!=currency or row['purpose']!=purpose
                or type(row['binding']) is not int or row['binding']!=binding):
            raise ValueError('NPC shop payment recipe requires explicit implementation review')
        recipes[mode]=ShopPayment(mode,currency,purpose,binding)
    return ShopPayments(revision,MappingProxyType(recipes))

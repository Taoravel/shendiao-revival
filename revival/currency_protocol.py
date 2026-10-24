"""Native absolute-wallet refresh codecs and proven UI display routes.

Slots describe verified native handlers, not the UI's separate 1..4 enum.
Only the target connection owner may encode/send these logical messages.
"""
import struct
from types import MappingProxyType

REFRESH_MONEY = 0xc03fa
REFRESH_SMONEY = 0xc0012
REFRESH_YUANBAO = 0xc659a
SLOTS = MappingProxyType({
    'money_1': (REFRESH_MONEY, 1),  # wallet +b0/+b4
    'money_2': (REFRESH_MONEY, 2),  # wallet +b8/+bc
    'smoney': (REFRESH_SMONEY, None),  # wallet +c8/+cc
})
# UI layout -> panel label -> wallet getter -> native handler chain. This
# proves display routing, not the separate task reward-field business mapping.
CURRENCY_SLOTS = MappingProxyType({'cash':'money_1','bound_silver':'smoney'})


def encode_balance(slot, absolute_balance):
    """Return (protocol type, body) for a proven native slot and current balance.

    Callers must independently prove which logical currency maps to the slot.
    The amount is an absolute balance; historical reward deltas are not valid
    substitutes. Unknown slots and values outside nonnegative signed64 fail.
    """
    if type(slot) is not str or slot not in SLOTS:
        raise ValueError('Unverified native wallet slot')
    if type(absolute_balance) is not int or not 0 <= absolute_balance < 2**63:
        raise ValueError('Invalid native absolute wallet balance')
    kind, discriminator = SLOTS[slot]
    body = struct.pack('>q',absolute_balance)
    if discriminator is not None:
        body = struct.pack('>i',discriminator)+body
    return kind,body


def encode_currency_balance(currency, absolute_balance):
    """Encode proven cash/bound-silver routing; yuanbao requires its full pair.

    See evidence/CURRENCY_UI_BRIDGE_RESEARCH.md. Always read current authority
    after settlement: a reward amount or historical retry receipt is not the
    current balance. This helper never grants, spends or sends currency.
    """
    if type(currency) is not str or currency not in CURRENCY_SLOTS:
        raise ValueError('Currency requires paired refresh or has no verified display route')
    return encode_balance(CURRENCY_SLOTS[currency],absolute_balance)


def encode_yuanbao_balances(yuanbao, bound_yuanbao):
    """The native message replaces BOTH balances: never fill a missing one with 0.

    Native UI consumers sign-extend both int32 fields. Until a wider compatible
    path is proven, refuse values outside nonnegative signed32 rather than
    truncating a signed64 ledger balance. Business caps remain separately owned.
    """
    if any(type(value) is not int or not 0 <= value < 2**31 for value in (yuanbao,bound_yuanbao)):
        raise ValueError('Invalid native yuanbao absolute balance pair')
    return REFRESH_YUANBAO,struct.pack('>ii',yuanbao,bound_yuanbao)

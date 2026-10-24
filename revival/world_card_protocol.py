"""Original weapon card wire bodies; task/choice authorization lives elsewhere."""
import struct

S_PLAY_CARD_EFFECT = 0xC001C
C_GET_CARD_ITEM = 0xC041F


def play_card_effect(effect_id):
    if type(effect_id) is not int or not 0 < effect_id < 2**31:
        raise ValueError('Original SPlayCardEffect requires a positive signed i32')
    return struct.pack('>i', effect_id)


def decode_get_card_item(body):
    """Returns effect ID, requested item ID; neither grants reward authority."""
    if len(body) != 8:
        raise ValueError('Unexpected CGetCardItem body length')
    return struct.unpack('>ii', body)

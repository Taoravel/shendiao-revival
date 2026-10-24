"""Original family production formats; NPC/organization admission is upstream."""
import struct

SET_PRODUCTS=0xc5607
PRODUCTS_INFO=0xc5606


def decode_set(body):
    if not isinstance(body,bytes) or len(body)!=8:
        raise ValueError('invalid_family_product_packet')
    choices=struct.unpack('>ii',body)
    if any(value not in (-1,0,1) for value in choices) or sum(value!=-1 for value in choices)!=1:
        raise ValueError('invalid_family_product_choice')
    return choices


def information(state,drug_cost,special_cost):
    """Two Q maintenance quotes, each followed by current stock and open flag."""
    if any(type(value) is not int or not 0<=value<2**63 for value in (drug_cost,special_cost)):
        raise ValueError('invalid_family_product_quote')
    if (any(type(value) is not int or not 0<=value<2**31 for value in (state.drug_stock,state.special_stock))
            or type(state.drug_open) is not bool or type(state.special_open) is not bool):
        raise ValueError('invalid_family_product_state')
    return struct.pack('>QiiQii',drug_cost,state.drug_stock,int(state.drug_open),
        special_cost,state.special_stock,int(state.special_open))

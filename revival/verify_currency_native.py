"""Offline execution of the original x86 money serializers; no live packets."""
import hashlib
import struct
from currency_protocol import encode_balance,encode_currency_balance,encode_yuanbao_balances
from inspect_client import OUT,write_json
from verify_social_native import native_payload
from native_inspect import DATA


def main():
    cases=(('money_1',0xe4e9a0,[(8,1)],0x10,2**32+7),
           ('money_2',0xe4e9a0,[(8,2)],0x10,2**63-1),
           ('smoney',0xe40e70,[],8,2**40+123))
    passed=[]
    for slot,serializer,scalars,offset,amount in cases:
        kind,expected=encode_balance(slot,amount)
        actual=native_payload(serializer,scalars=scalars,raw=[(offset,struct.pack('<q',amount))])
        assert actual==expected,(slot,actual.hex(),expected.hex())
        passed.append({'slot':slot,'type':hex(kind),'serializer':hex(serializer),
                       'balance':amount,'bytes':len(actual)})
    for slot,value in (('cash',1),('3',1),('money_1',-1),('smoney',2**63),('money_2',True),('smoney',1.5)):
        try: encode_balance(slot,value)
        except ValueError: pass
        else: raise AssertionError('Invalid wallet refresh accepted')
    assert encode_currency_balance('cash',2**32+7)==encode_balance('money_1',2**32+7)
    assert encode_currency_balance('bound_silver',2**40+123)==encode_balance('smoney',2**40+123)
    for currency in ('yuanbao','bound_yuanbao','3'):
        try: encode_currency_balance(currency,1)
        except ValueError: pass
        else: raise AssertionError('Unverified currency mapping accepted')
    kind,expected=encode_yuanbao_balances(123456,2**31-1)
    actual=native_payload(0xe5bb70,scalars=[(8,123456),(0xc,2**31-1)])
    assert actual==expected
    passed.append({'slot':'yuanbao_then_bound_yuanbao','type':hex(kind),'serializer':'0xe5bb70',
                   'balances':[123456,2**31-1],'bytes':len(actual)})
    for pair in ((1,2**31),(-1,0),(True,1),(0,None)):
        try: encode_yuanbao_balances(*pair)
        except ValueError: pass
        else: raise AssertionError('Invalid yuanbao pair accepted')
    report={'image_sha256':hashlib.sha256(DATA).hexdigest(),'passed':passed,
            'native_ui_slot_mapping_verified':['cash','bound_silver','yuanbao','bound_yuanbao'],
            'task_reward_currency_mapping':'designed','real_client_display_verified':False,
            'live_server_changed':False}
    write_json(OUT/'evidence/currency-native-verification.json',report)
    print(report)


if __name__=='__main__': main()

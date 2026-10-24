"""Original x86 codecs for sale, repurchase, buyback listing and NPC repair."""
import hashlib
import struct
from native_inspect import DATA,u32
from verify_social_native import native_payload
from native_gameplay_probe import probe
from inventory import item_record
from inspect_client import OUT,write_json


def main():
    key=(1007<<32)|7
    expected=struct.pack('>q',key)+b'\2'+struct.pack('>ii',7,9)
    actual=native_payload(0xe6f2b0,raw=[(8,struct.pack('<q',key)),
        (0x14,struct.pack('<III',0x5001400,0x5001408,0x5001408)),(0x400,struct.pack('<ii',7,9))])
    assert actual==expected
    assert native_payload(0xe51c60,scalars=[(0x10,7)],raw=[(8,struct.pack('<q',key))])==struct.pack('>qi',key,7)
    assert native_payload(0xe4cf30,scalars=[(8,2),(0x18,1),(0x1c,7)],
        raw=[(0x10,struct.pack('<q',key))])==struct.pack('>iqii',2,key,1,7)
    item=item_record(dict(id=7,template_id=40200,slot=0,quantity=1,binding=1))
    listing=struct.pack('>Qi',1000,20)+b'\1'+item+b'\1'+struct.pack('>ii',7,250)
    actual,_=probe(0xef64e0,u32(0x2284258),u32(0x228425c),payload=listing)
    assert actual==listing,(actual.hex(),listing.hex())
    report={'image_sha256':hashlib.sha256(DATA).hexdigest(),'passed':[
        'CSellItemToNpc BE64 NPC key + compact vector of whole-stack signed32 keys',
        'CRepurchaseFromNpc BE64 NPC key + signed32 item key',
        'CRepairEquipItem method2 + BE64 NPC key + column + item key',
        'SGetRepurchaseItems nonempty ItemBag plus key->total cash price map original decode/marshal'],
        'native_gui_verified':False,'live_client_changed':False}
    write_json(OUT/'evidence/npc-trade-repair-native.json',report);print(report)


if __name__=='__main__':main()

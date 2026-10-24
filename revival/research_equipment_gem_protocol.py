"""Repeatable original ordinary-gem codecs; no production route or asset writes."""
from native_gameplay_probe import probe
import struct
from inspect_client import OUT,write_json


def main():
    cases=[]
    protocols=(
        ('add',0xc0425,0xd8d0d0,0xe4b710,0xd8d100),
        ('remove',0xc04ea,0xd94dc0,0xe4ce00,0xd94df0),
        ('combine',0xc0424,0xd8f270,0xe4bcd0,0xd8f2a0))
    for name,typ,factory,marshal,decoder in protocols:
        values=((701,0,901),(701,1,901)) if name=='add' else (
            ((35001,701,0),(35001,701,1),(-1,701,0),(-1,701,1)) if name=='remove' else ((901,902),(901,901)))
        for args in values:
            if name=='add':
                key,mode,gem=args;expected=struct.pack('>iBi',*args)
                fields={8:struct.pack('<i',key),12:bytes([mode]),16:struct.pack('<i',gem)}
            elif name=='remove':
                gem,key,mode=args;expected=struct.pack('>iiB',*args)
                fields={8:struct.pack('<i',gem),12:struct.pack('<i',key),16:bytes([mode])}
            else:
                expected=struct.pack('>ii',*args);fields={8:struct.pack('<i',args[0]),12:struct.pack('<i',args[1])}
            encoded,raw=probe(factory,marshal,decoder,fields,factory=True)
            assert encoded==expected,(name,args,encoded.hex(),expected.hex())
            assert struct.unpack_from('<I',raw,4)[0]==typ
            for offset,value in fields.items():assert raw[offset:offset+len(value)]==value
            cases.append({'message':name,'type':hex(typ),'values':args,'wire':encoded.hex()})
    assert cases[0]['wire']=='000002bd0000000385'
    assert next(c['wire'] for c in cases if c['message']=='remove' and c['values']==(-1,701,0))=='ffffffff000002bd00'
    write_json(OUT/'evidence/equipment-gem-protocol-native.json',{'source_status':'client_verified','passed':len(cases),
        'cases':cases,'oracle':'actual allocating original factories, original marshalling/unmarshalling and decoded field/type checks',
        'scope':'wire only; actual send/selection semantic evidence is EQUIPMENT_GEMS_SOURCE_RESEARCH.md; same-key combine still needs owned quantity>=2',
        'not_ordinary':'CRemoveGem c0533 belongs another187xxx UI; not registered here',
        'source_modes':'only actual source bytes0/1 exercised; business source-container interpretation still needs precise native/owner mapping',
        'production_route_changed':False,'live_server_changed':False,'native_gui_verified':False})
    print('PASS8 original ordinary-gem factory/codec roundtrips: add, selected/all removal, distinct/same-key combine')


if __name__=='__main__':main()

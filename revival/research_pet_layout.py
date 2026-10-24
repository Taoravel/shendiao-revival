"""Differential original pet serializer probes; unnamed fields stay unnamed."""
import struct
from native_gameplay_probe import probe
from inspect_client import OUT, write_json


def main():
    common = {4: struct.pack('<i',500001),8:struct.pack('<i',7)}
    original, _ = probe(0xf89ba0,0xf5df70,0xf5f1f0,common)
    candidates = list(range(0x28,0x64,4)) + list(range(0x80,0xb8,4)) + [0x110,0x120,0x128]
    rows = []
    for offset in candidates:
        try:
            output, raw = probe(0xf89ba0,0xf5df70,0xf5f1f0,
                                dict(common, **{}) | {offset:struct.pack('<I',0x1020304)})
            differences = [i for i,(a,b) in enumerate(zip(original,output)) if a != b]
            rows.append({'native_offset':hex(offset),'wire_offsets':differences,
                         'wire_bytes':[output[i] for i in differences],
                         'length':len(output),'decoded_word':struct.unpack_from('<I',raw,offset)[0],
                         'semantic_name':None})
        except (ValueError,RuntimeError,AssertionError) as error:
            rows.append({'native_offset':hex(offset),'probe_error':str(error),'semantic_name':None})
    write_json(OUT/'evidence/pet-native-field-layout.json',
               {'default_bytes':len(original),'fields':rows,'business_semantics_not_proven':True})
    print('Original pet scalar layout probes:',len(rows))


if __name__ == '__main__':
    main()

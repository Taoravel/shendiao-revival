"""Inspect fixed original role screen/movement entry points, offline only."""
import argparse
import hashlib
import json
from pathlib import Path
from native_inspect import DATA,disasm,u32

FUNCTIONS={
    'RoleBasicOctets_constructor':(0xfad590,183),
    'RoleBasicOctets_marshal':(0xfad940,437),
    'RoleBasicOctets_decode':(0xfae280,496),
    'RoleBasic_constructor':(0xfc6bf0,142),
    'RoleBasic_marshal':(0xfc6d30,206),
    'RoleBasic_decode':(0xfc6c80,169),
    'screen_process_role_decode_create':(0x11e6f56,110),
    'role_projection':(0x11dd901,122),
    'role_shape_conversion_other':(0x11ddaa8,37),
    'create_player':(0x11da214,80),
    'role_move_constructor':(0xdacd10,39),
    'role_move_marshal':(0xe50d90,39),
    'role_move_process':(0x11d7fc0,412),
    'role_move_remote_dispatch':(0x11d8147,14),
    'role_stop_constructor':(0xdad130,45),
    'role_stop_process':(0x11c56c0,3),
}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--disasm',choices=FUNCTIONS)
    args=p.parse_args()
    if args.disasm:disasm(*FUNCTIONS[args.disasm])
    else:
        result={'original_image_sha256':hashlib.sha256(DATA).hexdigest(),
                'functions':{name:hex(value[0]) for name,value in FUNCTIONS.items()},
                'vtables':{'RoleBasicOctets':hex(0x2286424),'RoleBasic':hex(0x228683c),
                           'SRoleMove':hex(0x22792cc),'SRoleStop':hex(0x2279350)},
                'SRoleStop_Process_first_three_bytes':DATA[0x11c56c0-0x400000:0x11c56c3-0x400000].hex(),
                'scope':'original image only; no client or server started'}
        path=Path(__file__).parent/'evidence/world-role-native-addresses.json'
        path.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2))

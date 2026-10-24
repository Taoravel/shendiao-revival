"""Capture reproducible first-party mapped-image evidence for scene entities."""
from contextlib import redirect_stdout
import hashlib
import json
from pathlib import Path
from native_inspect import DATA, disasm


def main():
    out = Path(__file__).parent / 'evidence'
    spans = {'SAddUserScreen-ctor': (0xfc5f40, 130),
             'SVisitNpc-ctor-codecs': (0xe70050, 530),
             'SVisitNpc-process': (0x1214250, 344),
             'Npc-initialize-shape-override': (0x1201bd0, 920),
             'SAddUserScreen-codecs': (0xfc68f0, 350),
             'SAddUserScreen-npc-handler': (0x11e7015, 900),
             'Npc-scene-create': (0x11d9ed8, 360),
             'Npc-scene-key-index': (0x11d9c70, 130),
             'SRemoveUserScreen-ctor-codecs': (0xe6e9e0, 500),
             'ActivityNpc-dedup': (0x1228d20, 110),
             'NpcBasic-marshal': (0xfc6f70, 620),
             'NpcBasic-ctor': (0xfc71e0, 180),
             'NpcBasic-unmarshal': (0xfc73a0, 1250),
             'SAddActivityNpc-ctor': (0xf0f740, 84),
             'SAddActivityNpc-codecs': (0xf0fef0, 350),
             'SAddActivityNpc-handler': (0x1230b20, 560),
             'SRemoveActivityNpc-ctor-codecs': (0xe6e6c0, 320),
             'Pos-marshal': (0xe50690, 140),
             'Npc-property-pair': (0xec0070, 118),
             'CVisitNpc-ctor-decoder': (0xdb3450, 233),
             'CVisitNpc-marshal': (0xe52020, 57),
             'CNpcService-ctor': (0xdb1710, 27),
             'CNpcService-marshal': (0x83b5a0, 39),
             'CNpcService-unmarshal': (0x8392d0, 90)}
    with (out / 'world-entities-native-disassembly.txt').open('w', encoding='utf-8') as f:
        with redirect_stdout(f):
            print('native-image.bin SHA256', hashlib.sha256(DATA).hexdigest())
            for label, (address, size) in spans.items():
                print('\n', label)
                disasm(address, size)
    print(json.dumps({'spans': len(spans), 'sha256': hashlib.sha256(DATA).hexdigest()}))


if __name__ == '__main__':
    main()

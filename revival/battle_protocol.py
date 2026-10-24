"""Native 1.6.1 battle wire layouts. No inferred operation enum mapping here."""
import struct
from dataclasses import dataclass
from wire import compact, octets, read_compact, NeedMoreData

BATTLE_START = 0xc1b59
ADD_FIGHTERS = 0xc1b5a
ROUND_START = 0xc1b5b
SEND_ACTION = 0xc1b5c
CLIENT_PLAY_END = 0xc1b5e
BATTLE_END = 0xc1b5f
ROUND_SCRIPT = 0xc1b71
SERVER_PLAY_END = 0xc1b76
BATTLE_TYPES = frozenset((SEND_ACTION, CLIENT_PLAY_END))
ATTACK = 1
DEFEND = 4
ESCAPE = 9
SKILL = 2
ROLE_INIT_ATTRS = 0xc1b6f
PET_INIT_ATTRS = 0xc1b70
OTHER_SKILLS = 0xc36c3
HP_CHANGE = 1


@dataclass(frozen=True)
class TargetResult:
    """Separate native result values from the unrelated DemoAttr collection."""
    target: int
    values: tuple = ()       # ((native result key, signed value), ...)
    demo_attrs: tuple = ()   # raw DemoAttr triples; not HP/MP result values


def int_map(values):
    return compact(len(values)) + b''.join(struct.pack('>ii',k,v) for k,v in sorted(values.items()))


def float_map(values):
    return compact(len(values))+b''.join(struct.pack('>if',k,v) for k,v in sorted(values.items()))


def other_skills(levels, flag=1):
    return int_map(levels)+struct.pack('B',flag)


def battle_start(enemy_side=0, background=6, music=1, battle_id=1, battle_type=0):
    # Native offsets 8..24: enemy side, friend formation/level, enemy formation/
    # level, background, music, round number; then two signed bytes.
    return struct.pack('>8i2b',enemy_side,0,0,0,0,background,music,0,battle_id,battle_type)


def fighter(position, data_id, shape, name, fighter_type, hp=100, level=1, *, max_hp=None, injured_hp=None):
    """FighterInfo with empty appearance/buff maps and original default tails."""
    max_hp=hp if max_hp is None else max_hp
    injured_hp=max_hp if injured_hp is None else injured_hp
    if not 0 < hp <= injured_hp <= max_hp <= 0x7fffffff: raise ValueError('Invalid HP')
    # Native consumer offsets: type +4, dataID +8, level +0x10, name
    # +0x14, battle position +0x4c, base model +0x64, optional model +0x60,
    # talent +0x68 and aura +0xa8. Confirmed in AddFighters Process consumers.
    return (struct.pack('>iQi',fighter_type,data_id,level)
            + octets(name.encode('utf-16-le')) + octets(b'')
            + struct.pack('>iB6iB',position,0,max_hp,injured_hp,hp,0,shape,0,0)
            + b'\0\0\0' + octets(b'') + struct.pack('>i',0))


def add_fighters(fighters):
    return compact(len(fighters)) + b''.join(fighters)


def round_start(wait_seconds=30, environment=0):
    # Process 0x1196013 reads offset8 then multiplies by1000 into timer 0xf0.
    # The client increments its own round number; this field is not that index.
    return struct.pack('>ii',wait_seconds,environment) + b'\0'


def parse_action(body):
    # Original SendBattleCommand's player branch 0x11962bf writes type, target,
    # operation ID, is-role=1, manual=0 before calling the native network sender.
    if len(body)!=14: raise ValueError('Invalid CSendAction length')
    return struct.unpack('>iiiBB',body)


def parse_play_end(body):
    try:
        size,pos=read_compact(body)
    except NeedMoreData as exc: raise ValueError('Truncated playback reply') from exc
    if size>64 or len(body)!=pos+size*4: raise ValueError('Invalid playback reply')
    return tuple(struct.unpack_from('>i',body,pos+i*4)[0] for i in range(size))


def battle_end(values=None):
    return int_map(values or {})


def round_script(executions):
    """NewResultItem list, no AI/actions, summons or removals.

    Each tuple: nine DemoExecute scalars, then TargetResult objects. The native
    result map carries hpchange/key1, mpchange/key2, etc. DemoAttr is a different
    collection: putting HP there decodes successfully but the HP consumer sees0.
    """
    items=[]
    for scalars,targets in executions:
        if len(scalars)!=9: raise ValueError('DemoExecute needs nine scalars')
        execute=struct.pack('>9i',*scalars)+b'\0' # empty attacker buff list
        results=[]
        for target in targets:
            if not isinstance(target,TargetResult):raise ValueError('Explicit native TargetResult required')
            values=dict(target.values)
            if len(values)!=len(target.values):raise ValueError('Duplicate result key')
            results.append(struct.pack('>i',target.target)+b'\0'+compact(len(target.demo_attrs))
                           +b''.join(struct.pack('>iii',*a) for a in target.demo_attrs)+int_map(values))
        items.append(execute+compact(len(results))+b''.join(results)+bytes(3))
    return compact(len(items))+b''.join(items)+bytes(3)

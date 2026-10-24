"""Social wire layouts recovered from this client's native x86 serializers.

Unknown profile fields retain native defaults. See evidence/SOCIAL_PROTOCOL.md.
"""
import struct
from wire import octets, read_octets, NeedMoreData

FRIENDS_INIT = 0xc4e21
ONLINE = 0xc4e22
PRIVATE_SEND, PRIVATE_RECEIVE = 0xc4e23, 0xc4e24
DELETE_SEND, DELETE_RECEIVE = 0xc4e25, 0xc4e26
SEARCH_ID_RECEIVE, SEARCH_ID_SEND = 0xc4e27, 0xc4e28
ADD_RECEIVE, ADD_SEND = 0xc4e31, 0xc4e32
SEARCH_NAME_SEND, SEARCH_NAME_RECEIVE = 0xc4e3e, 0xc4e3f
CHAT_SEND, CHAT_RECEIVE = 0xc1771, 0xc1772
REQUEST_SEND, REQUEST_RECEIVE = 0xc4e30, 0xc4e2f
AGREE_SEND = 0xc4e43
REFUSE_SEND, REFUSE_RECEIVE = 0xc4e34, 0xc4e33
MOVE_GROUP_SEND, MOVE_GROUP_RECEIVE = 0xc4e2d, 0xc4e2e
UNBLOCK_SEND, UNBLOCK_RECEIVE = 0xc4e66, 0xc4e65
TRY_ADD_SEND, TRY_ADD_RECEIVE = 0xc4e36, 0xc4e3d
GROUP_FRIEND, GROUP_BLACK = '我的好友', '黑名单'
SOCIAL_TYPES = {SEARCH_ID_SEND, SEARCH_NAME_SEND, ADD_SEND, DELETE_SEND, PRIVATE_SEND, CHAT_SEND,
                REQUEST_SEND, AGREE_SEND, REFUSE_SEND, MOVE_GROUP_SEND, UNBLOCK_SEND, TRY_ADD_SEND}
from group_protocol import GROUP_TYPES
SOCIAL_TYPES.update(GROUP_TYPES)
from faction_types import FAMILY_NATIVE_TYPES
SOCIAL_TYPES.update(FAMILY_NATIVE_TYPES)
from faction_types import GUILD_NATIVE_TYPES
SOCIAL_TYPES.update(GUILD_NATIVE_TYPES)
CURRENT_CHANNEL, SCHOOL_CHANNEL, WORLD_CHANNEL = 2, 3, 5


def text(value):
    return octets(value.encode('utf-16-le'))


def read_text(body, pos=0, limit=2048):
    value, pos = read_octets(body, pos, limit=limit)
    return value.decode('utf-16-le'), pos


def end(body, pos):
    if pos != len(body):
        raise ValueError('Social message trailing data')


def target_request(body, with_name=False):
    if len(body) < 8:
        raise ValueError('Truncated social target')
    target = struct.unpack_from('>Q', body)[0]
    name, pos = read_text(body, 8, 32) if with_name else ('', 8)
    end(body, pos)
    return target, name


def friend_info(role, online=False, group=''):
    # FriendInfo: Q, wstr, byte, int, wstr, short, wstr, byte,
    # byte, int, byte, int. Group/affinity/profile fields remain defaults.
    return (struct.pack('>Q', role['id']) + text(role['name']) + bytes(5)
            + text('') + struct.pack('>h', role['level']) + text(group)
            + bytes([int(online), 0]) + bytes(9))


def friend_added(role, online=False, group=''):
    return (struct.pack('>Q', role['id']) + text(role['name']) + b'\0' + text('')
            + struct.pack('>h', role['level']) + text(group) + bytes([int(online), 0])
            + bytes(4) + b'\0\x01\0' + bytes(4))


def profile(role=None, by_name=False):
    role = role or {'id': 0, 'name': '', 'level': 0, 'school': 0, 'shape': 0}
    first = struct.pack('>Q', role['id']) + text(role['name']) + struct.pack(
        '>iii', role['level'], role['school'], role['shape']) + text('')
    if not by_name:
        first += bytes(12) + text('')
    return first + text('') + text('') + bytes(8 if not by_name else 12) + b'\0' + bytes(4)


def private_request(body):
    if len(body) < 8:
        raise ValueError('Truncated private message')
    target = struct.unpack_from('>Q', body)[0]
    content, pos = read_text(body, 8)
    extra, pos = read_text(body, pos)
    if pos+5 != len(body) or body[-1] != 0:
        raise ValueError('Unsupported private attachments')
    mode = struct.unpack_from('>i', body, pos)[0]
    return target, content, extra, mode


def private_message(role, content, extra=''):
    return (struct.pack('>Q', role['id']) + text(role['name']) + text(content) + text(extra)
            + bytes(10) + text('') + bytes(16))


def chat_request(body):
    if len(body) < 4:
        raise ValueError('Truncated chat message')
    channel = struct.unpack_from('>i', body)[0]
    content, pos = read_text(body, 4)
    extra, pos = read_text(body, pos)
    if body[pos:] != b'\0':
        raise ValueError('Unsupported chat attachments')
    return channel, content, extra


def chat_message(role, channel, content, extra=''):
    return (struct.pack('>Q', role['id']) + text(role['name'])
            + struct.pack('>ii', role['level'], channel) + text(content) + b'\0\0')


def request_with_text(body):
    message, pos = read_text(body,limit=512)
    target, _ = target_request(body[pos:])
    return target, message


def request_notice(role, greeting):
    return text(greeting)+struct.pack('>Q',role['id'])+text(role['name'])+text('')+struct.pack('>i',role['level'])


def refusal_notice(role, reason):
    return text(role['name'])+text(reason)+struct.pack('>Q',role['id'])


def group_request(body):
    group,pos = read_text(body,limit=64)
    target,name = target_request(body[pos:],True)
    return group,target,name


def moved_group(target,group):
    return text(group)+struct.pack('>Q',target)


def try_add_info(role):
    return struct.pack('>Q',role['id'])+text(role['name'])+struct.pack('>i',role['level'])

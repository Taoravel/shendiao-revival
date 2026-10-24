"""Role messages confirmed against the original mapped client."""
import struct
import json
from pathlib import Path
from inspect_client import OUT
from wire import compact, octets, read_octets

ROLE_LIST_REQUEST = 0xc0001
ROLE_LIST = 0xc0002
CREATE_ROLE_REQUEST = 0xc0003
CREATE_ROLE = 0xc0004
ENTER_WORLD_REQUEST = 0xc0005
ROLE_OFFLINE_REQUEST = 0xc0011
DELETE_ROLE_REQUEST = 0xc0028
DELETE_ROLE = 0xc0029
RETURN_ROLE_LIST_REQUEST = 0xc002d
RETURN_ROLE_LIST = 0xc002e
ROLE_OFFLINE = 0xc0031
RETURN_LOGIN_REQUEST = 0xc0032
RETURN_LOGIN = 0xc0033
FIRST_DAY_EXIT_GAME = 0xc0039


def load_exit_ui_message(path=None):
    """Startup-only ordinary exit Adapter; zero selects a different native UI."""
    path=Path(path) if path is not None else OUT/'design/role-exit-ui-v1.json'
    policy=json.loads(path.read_text(encoding='utf-8'))
    if (policy.get('revision')!='2026-10-23.role-exit-ui.1'
            or type(policy.get('message_type')) is not int or policy['message_type']!=FIRST_DAY_EXIT_GAME
            or type(policy.get('value')) is not int or policy['value']!=-1):
        raise ValueError('Ordinary exit UI policy requires explicit review')
    return policy['message_type'],struct.pack('>i',policy['value'])


def parse_delete(body):
    if type(body) is not bytes or len(body)!=8:raise ValueError('Delete request must contain one role ID')
    ident=struct.unpack('>Q',body)[0]
    if not 0<ident<2**63:raise ValueError('Invalid persisted role ID')
    return ident


def role_info(role):
    return (struct.pack('>Q', role['id']) + octets(role['name'].encode('utf-16-le'))
            + struct.pack('>iii', role['school'], role['shape'], role['level'])
            + compact(0) + struct.pack('>Bii', 0, 0, 0))


def role_list(last_role_id, roles):
    return (struct.pack('>QB', last_role_id, 0) + compact(len(roles))
            + b''.join(role_info(role) for role in roles) + struct.pack('>i', 0))


def parse_create(body):
    name, pos = read_octets(body, limit=96)
    if pos + 8 != len(body) or len(name) % 2:
        raise ValueError('Invalid create-role payload')
    school, shape = struct.unpack_from('>ii', body, pos)
    return name.decode('utf-16-le'), school, shape


def parse_enter(body):
    if len(body) < 10:
        raise ValueError('Invalid enter-world payload')
    role_id = struct.unpack_from('>Q', body)[0]
    extra, pos = read_octets(body, 8, limit=4096)
    if pos + 1 != len(body):
        raise ValueError('Invalid enter-world tail')
    return role_id, extra, body[pos]

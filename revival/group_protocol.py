"""Native 1.6.1 CommonGroup wire layouts; no storage or online objects."""
import struct
from wire import compact,octets,read_octets


def text(value): return octets(value.encode('utf-16-le'))


def read_text(body,pos=0,limit=2048):
    raw,pos=read_octets(body,pos,limit=limit)
    return raw.decode('utf-16-le'),pos


def end(body,pos):
    if len(body)!=pos:raise ValueError('Group message trailing data')

CREATE, CREATED = 0xc4e46, 0xc4e47
SEARCH, SEARCHED = 0xc4e48, 0xc4e49
JOIN, RESPOND = 0xc4e4a, 0xc4e4b
SEND, MESSAGE = 0xc4e4c, 0xc4e4d
CONFIG = 0xc4e4e
CONFIGURED = 0xc4e5e
LEAVE, LEFT = 0xc4e4f, 0xc4e50
INVITE, INVITED, INVITE_REPLY = 0xc4e51, 0xc4e52, 0xc4e53
ADDED, EXPEL = 0xc4e54, 0xc4e55
MANAGER = 0xc4e58
CREATE_READY, NAME, JOIN_NOTICE = 0xc4e5b, 0xc4e5c, 0xc4e5d
UPDATED, INITIAL = 0xc4e63, 0xc4e64
INVITE_ACK = 0xc4e62
HISTORY, HISTORY_PAGE = 0xc4e91, 0xc4e92
GROUP_TYPES = frozenset((CREATE, NAME, SEARCH, JOIN, RESPOND, SEND, LEAVE,
                        INVITE, INVITE_REPLY, EXPEL, MANAGER, CONFIG, HISTORY))


def identity(body):
    if len(body) != 8: raise ValueError('Group identity length')
    return struct.unpack('>Q', body)[0]


def search_request(body):
    name, pos = read_text(body, limit=32)
    if len(body) != pos+12: raise ValueError('Group search length')
    group, mode = struct.unpack_from('>Qi', body, pos)
    return name, group, mode


def response_request(body):
    if len(body) != 20: raise ValueError('Group approval length')
    decision, applicant, group = struct.unpack('>iQQ', body)
    if decision not in (0, 1): raise ValueError('Group approval decision')
    return decision, applicant, group


def message_request(body):
    plain, pos = read_text(body, limit=2048)
    formatted, pos = read_text(body, pos, limit=4096)
    if len(body) != pos+9 or body[-1] != 0:
        raise ValueError('Unsupported group attachments')
    return struct.unpack_from('>Q', body, pos)[0], plain, formatted


def member_request(body):
    # Invite/expel UI 16e9ccb/16e9e83: selected role first, group second.
    if len(body)!=16:raise ValueError('Group member request length')
    role,group=struct.unpack('>QQ',body)
    if not 0<role<2**63:raise ValueError('Group member identity')
    return role,group


def manager_request(body):
    if len(body)!=24:raise ValueError('Group manager request length')
    appoint,group,role=struct.unpack('>QQQ',body)
    if appoint not in (0,1) or not 0<role<2**63:raise ValueError('Group manager request')
    return appoint,group,role


def invite_reply(body):
    # Invite Agree=1 (16ef820), Refuse=0 (16ef8b0); public applications
    # have their own opposite enum. Never use one shared approval decoder.
    if len(body)!=12:raise ValueError('Group invitation reply length')
    agree,group=struct.unpack('>iQ',body)
    if agree not in (0,1):raise ValueError('Group invitation decision')
    return agree,group


def config_request(body):
    if len(body)<16:raise ValueError('Group config length')
    group,scope,flash=struct.unpack_from('>Qii',body)
    notice,pos=read_text(body,16,limit=2048)
    extra,pos=read_text(body,pos,limit=4096)
    if len(body)!=pos+4:raise ValueError('Group config trailing data')
    allow=struct.unpack_from('>i',body,pos)[0]
    if scope not in (0,1) or flash not in (0,1) or allow not in (0,1):raise ValueError('Group config enum')
    return group,scope,flash,notice,extra,allow


def history_request(body):
    if len(body)!=12:raise ValueError('Group history request length')
    group,page=struct.unpack('>Qi',body)
    if page!=-1 and page<1:raise ValueError('Group history page')
    return group,page


def created(group, name): return struct.pack('>Q', group)+text(name)


def member(role, online=False):
    # Native consumer copies +2c to the friend's level and +30 to online.
    return struct.pack('>Q', role['id'])+text(role['name'])+struct.pack('>ii', role['level'], int(online))


def member_flash(group,recipient=None):
    return next((m.get('flash',1) for m in group['members'] if m['id']==recipient),group['flash'])


def info(group, online=(), recipient=None):
    managers = group['managers']
    members = group['members']
    # Consumer 128fda0 looks up by +10 and copies +8 into leader fields.
    return (struct.pack('>QQ', group['owner'], group['id'])+text(group['name'])
            +compact(len(managers))+b''.join(struct.pack('>Q', r) for r in managers)
            +compact(len(members))+b''.join(member(r,r['id'] in online) for r in members)
            +text(group['notice'])+struct.pack('>ii',member_flash(group,recipient),group['allow_join']))


def initial(groups, online=(), recipient=None):
    return compact(len(groups))+b''.join(info(g,online,recipient) for g in groups)


def updated(group, online=(), recipient=None): return struct.pack('>Q', group['id'])+info(group,online,recipient)


def searched(group):
    return (struct.pack('>Q', group['id'])+text(group['name'])+text(group['notice'])
            +struct.pack('>i',len(group['members']))+text(group['owner_name']))


def join_notice(applicant, group, name):
    return struct.pack('>QQ', applicant, group)+text(name)


def message(group,sender,content,sent_time=''):
    # History rendering 16e854a/16e856c formats the third string as "  (%s)";
    # it is a server timestamp, not the client's second edit-control string.
    return text(content)+text(sender)+text(sent_time)+struct.pack('>QB',group,0)+bytes(2)


def invited(group,inviter,name):return struct.pack('>Q',group)+text(inviter)+text(name)


def configured(group,recipient=None):
    return (struct.pack('>Qi',group['id'],member_flash(group,recipient))+text(group['notice'])
            +struct.pack('>i',group['allow_join']))


def history_entry(row,separator=False):
    return text(row['plain'])+text(row['name'])+text(row['timestamp'])+bytes([int(separator)])+bytes(2)


def history_page(page,last,rows):
    return struct.pack('>iB',page,int(last))+compact(len(rows))+b''.join(
        history_entry(row,i==0 or row['timestamp'][:10]!=rows[i-1]['timestamp'][:10]) for i,row in enumerate(rows))

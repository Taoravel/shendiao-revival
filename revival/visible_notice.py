"""Designed local system-labelled chat notice, not a guessed system protocol.

Call after the original chat UI is initialized. The caller targets its current
connection owner and supplies trusted user-facing text, never a raw exception.
No broadcast, persistence, operation retry, asset change or send occurs here.
"""
from dataclasses import dataclass
from social_protocol import CHAT_RECEIVE,CURRENT_CHANNEL,chat_message


@dataclass(frozen=True)
class VisibleNotice:
    kind: int
    body: bytes


def visible_notice(reason):
    if type(reason) is not str or not 1<=len(reason)<=256 or not reason.isprintable():
        raise ValueError('invalid_visible_notice_text')
    try:reason.encode('utf-16-le')
    except UnicodeEncodeError:raise ValueError('invalid_visible_notice_text') from None
    body=chat_message({'id':0,'name':'系统通知','level':0},CURRENT_CHANNEL,reason)
    return VisibleNotice(CHAT_RECEIVE,body)

"""Bounded original task Post presentation and active-family research.

Synthetic memory fixtures; no client process, DB, server or task policy.
"""
from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_inspect import DATA
from research_battle import NativeBattleDecoder
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESI

IMAGE_SHA = '2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791'


def native_post_presentation(next_ids, experience=0, smoney=0):
    """Execute actual state1 presentation conditional, stopping before UI work."""
    p = NativeBattleDecoder()
    cfg, ui = p.allocate(0x400), p.allocate(0x100)
    if next_ids:
        values = p.allocate(4 * len(next_ids))
        p.write(values, *next_ids)
        p.write(cfg + 0x70, values, values + 4 * len(next_ids), values + 4 * len(next_ids))
    p.write(cfg + 0xa0, experience & 0xffffffff, experience >> 32)
    p.write(cfg + 0xc0, smoney & 0xffffffff, smoney >> 32)
    p.write(0x294560c, ui)
    hit = []

    def hook(uc, address, _size, _user):
        if address == 0x174d320:
            hit.append(address)
            uc.emu_stop()

    p.u.hook_add(UC_HOOK_CODE, hook)
    p.write(p.stack, p.stop)
    p.u.reg_write(p.sp, p.stack)
    p.u.reg_write(UC_X86_REG_ESI, cfg)
    p.u.emu_start(0x125c1cd, 0x125c238, count=1000)
    end = p.u.reg_read(p.ip)
    assert end in (0x125c238, 0x174d320), hex(end)
    return {'post': next_ids, 'experience': experience, 'smoney': smoney,
            'presentation_call': bool(hit), 'stopped_at': hex(end)}


def native_active_queries(active_ids, query):
    p = NativeBattleDecoder()
    manager, head = p.allocate(0x100), p.allocate(0x20)
    nodes = [p.allocate(0x30) for _ in active_ids]
    p.write(manager + 0x28, head)
    p.write(head, nodes[0] if nodes else head)
    for index, (node, task) in enumerate(zip(nodes, active_ids)):
        p.write(node, nodes[index + 1] if index + 1 < len(nodes) else head)
        p.write(node + 0xc, task)
    p.obj = manager
    p.call(0x1257a40, query)
    family = bool(p.u.reg_read(p.ax) & 255)
    p.call(0x1257ac0, query)
    exact = bool(p.u.reg_read(p.ax))
    return {'active_ids': active_ids, 'query': query, 'hundred_group_match': family,
            'exact_active_match': exact}


def native_empty_config_lookup(query):
    """Execute original missing-key getter with an explicit empty-tree fixture."""
    p = NativeBattleDecoder()
    table, head = p.allocate(0x400), p.allocate(0x400)
    p.write(table + 8, head)
    p.write(head + 4, head)
    p.u.mem_write(head + 0x339, bytes([1]))
    # Original constructor d38d62 sets the default bean id to -1.
    p.write(table + 0x10, 0xffffffff)
    p.obj = table
    p.call(0xd390d0, query & 0xffffffff)
    returned = p.u.reg_read(p.ax)
    assert returned == table + 0x10
    return {'query': query, 'returned_default_bean': True,
            'default_bean_id_signed': -1}


def main():
    assert hashlib.sha256(DATA).hexdigest() == IMAGE_SHA
    inputs = [([100199], 0, 0), ([100198], 0, 0), ([101199], 0, 0),
              ([103399], 0, 0), ([100198, 100199], 0, 0), ([], 0, 0),
              ([], 1, 0), ([], 0, 1)]
    posts = [native_post_presentation(*args) for args in inputs]
    assert [v['presentation_call'] for v in posts] == [True, False, True, True, False, False, True, True]
    inputs = [([], 100199), ([100121], 100199), ([100121], 100198),
              ([100121], 101199), ([101121], 101199), ([100121], 100121)]
    groups = [native_active_queries(*args) for args in inputs]
    assert [v['hundred_group_match'] for v in groups] == [False, True, True, False, True, True]
    assert [v['exact_active_match'] for v in groups] == [False, False, False, False, False, True]
    print(json.dumps({'image_sha256': IMAGE_SHA, 'synthetic_fixtures': True,
                      'post_presentation': posts, 'active_queries': groups,
                      'empty_config_queries': [native_empty_config_lookup(q)
                                               for q in (-1, 100199, 101199, 103399)],
                      'gui_verified': False, 'server_stage_semantics_verified': False},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

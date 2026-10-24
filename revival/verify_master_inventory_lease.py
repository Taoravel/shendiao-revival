"""Actual master-card grant/equip with an opaque epoch and public Inventory."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import struct

from accounts import AccountStore
from inventory import Inventory
from inventory_test_support import known_cash_context
from tasks import prepare_task_store
from task_rewards import prepare_reward_storage
from task_persistence import load_task_state
from task_session import TaskIntent
from task_protocol import C_QUEST_DIALOG_END
from task_newbie_chapter import (load_newbie_chapter_rules, prepare_newbie_chapter_storage,
    record_newbie_creation, initialize_newbie_chapter, authorize_newbie_playback, finish_newbie_chapter)
from task_master_card import (load_master_card_rules, prepare_master_card_storage,
    open_master_dialogue, authorize_master_card, choose_master_card, equip_master_transaction)
from world_newbie import NewbieFlow, load_newbie_routes
from world_catalog import maps, maze_grids
from world_owner import Location, MapAddress
from world_npcs import NpcInteraction
from inspect_client import OUT, write_json


def main():
    with TemporaryDirectory() as tmp:
        store = AccountStore(Path(tmp) / 'state.sqlite3')
        resources = prepare_task_store(store)
        config = Inventory.prepare(store)
        routes = load_newbie_routes()
        chapter_rules = load_newbie_chapter_rules(resources, routes, maps(), maze_grids())
        cards = load_master_card_rules(resources, chapter_rules, config)
        with closing(store.connect()) as db:
            prepare_reward_storage(db)
            prepare_newbie_chapter_storage(db)
            prepare_master_card_storage(db)
        route = next(r for r in routes.values() if r.character_id == 9)
        shape = next(s for s, c in resources.shape_to_role_config.items() if c == 9)
        role = store.create_role(1111, '师承字符串', route.school_id, shape)
        epoch = 'master-owner:角色:0001'
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            origin = record_newbie_creation(db, 1111, role['id'], 'controlled-master-token', resources, chapter_rules)
            db.execute('INSERT INTO role_positions VALUES(?,?,?,?)', (role['id'], *origin.spawn))
        store.acquire_lease(1111, role['id'])
        with closing(store.connect()) as db, db:
            db.execute('UPDATE role_leases SET epoch=? WHERE role_id=?', (epoch, role['id']))
        inv = Inventory(store, 1111, role['id'], config,
                        **known_cash_context(store, 1111, role['id'], epoch=epoch, balances=(31,0,0,0)))
        location = Location(role['id'], epoch, MapAddress(route.home_map_id, 1, 0), 1, *origin.spawn[1:])
        flow = NewbieFlow(resources, routes)
        cash = inv.currency_rules
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            initialize_newbie_chapter(db, 1111, role['id'], epoch, flow, chapter_rules)
            playback = authorize_newbie_playback(db, 1111, role['id'], epoch, flow, chapter_rules,
                location, generation=1, request_id='intro', now_ms=1)
            finish_newbie_chapter(db, 1111, role['id'], epoch,
                NewbieFlow.from_ticket(resources, routes, playback.ticket), chapter_rules,
                struct.pack('>i', route.intro_movie_id), location, inv,
                generation=1, now_ms=2, currency_rules=cash)
        card = cards.routes[(route.character_id, route.school_id)]
        proof = NpcInteraction('master-token-proof', role['id'], epoch, location.address,
                               location.version, 9100, card.npc_id, 1)
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            dialogue = open_master_dialogue(db, 1111, role['id'], epoch, resources, cards,
                                            proof, location, generation=1, now_ms=3)
            authorize_master_card(db, 1111, role['id'], epoch, resources, cards, dialogue.ticket,
                TaskIntent(C_QUEST_DIALOG_END, card.master_task_id), location, generation=1, now_ms=4)
        body = struct.pack('>ii', card.card_effect_id, card.choices[0][0])
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            chosen = choose_master_card(db, 1111, role['id'], epoch, resources, cards, body,
                location, inv, generation=1, now_ms=5, currency_rules=cash)
            state = inv.immutable_snapshot_transaction(db)
            item = next(i for i in state.items if i.id == chosen.choice.item_key)
            assert item.binding == 1 and item.condition.current == 100 and item.detail.score == 0
            assert item.equipment_slot is None
        before = inv.immutable_snapshot()
        try:
            with closing(store.connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                result = equip_master_transaction(db, 1111, role['id'], epoch, resources, cards,
                    inv, item.id, 0, 'master-token:equip', currency_rules=cash)
                assert result.completion is not None
                raise RuntimeError('downstream projection rejected')
        except RuntimeError:
            pass
        assert inv.immutable_snapshot() == before
        with closing(store.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            result = equip_master_transaction(db, 1111, role['id'], epoch, resources, cards,
                inv, item.id, 0, 'master-token:equip', currency_rules=cash)
            actor, task = load_task_state(db, 1111, role['id'], epoch)
            assert actor.login_epoch == epoch and result.equipment_event.login_epoch == epoch
            assert card.equipment_task_id in task.completed and card.cart_task_id in task.active
            replay = equip_master_transaction(db, 1111, role['id'], epoch, resources, cards,
                inv, item.id, 0, 'master-token:equip', currency_rules=cash)
            assert replay.completion is None and replay.equipment_event.replayed
    report = {'passed': ['opaque role epoch crosses intro/master authorization/asset grant/equip/type59/cart activation',
        'actual public Inventory same-transaction snapshots and ordinary condition/detail factory used',
        'downstream failure rolls equipment/event/task59/cart back together',
        'exact received instance completes once; stable equip retry preserves opaque epoch'],
        'live_runtime_routing_tested': False, 'native_gui_tested': False, 'live_server_changed': False}
    write_json(OUT / 'evidence/master-inventory-lease-verification.json', report)
    print('PASS:', ', '.join(report['passed']))


if __name__ == '__main__':
    main()

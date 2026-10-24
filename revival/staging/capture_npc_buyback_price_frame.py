"""Produce a real published sale reply for independent original-client pricing.

Only new temporary roles/assets are used. No price is manually inserted into a
cache or packet; the actual NPC transaction produces every captured value.
"""
import asyncio
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'runtime/deployments/npc-repair-20261024T023920Z'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    published = json.loads((RELEASE / 'manifest.json').read_text(encoding='utf8'))
    context = json.loads((RELEASE / 'candidate.json').read_text(encoding='utf8'))
    source, harness = RELEASE / 'source', RELEASE / 'harness'

    def verify():
        for directory, entries in ((source, published['sha256']), (harness, context['harness_sha256']),
                (harness, context['harness_resource_sha256']),
                (harness / 'workspace', context['workspace_sha256'])):
            for name, digest in entries.items():
                assert sha(directory / name) == digest, name

    verify()
    sys.path[:0] = [str(harness), str(source)]
    import inspect_client
    inspect_client.ROOT, inspect_client.OUT = ROOT.parent, harness / 'workspace'
    from accounts import AccountStore
    from game_runtime import GameRuntime
    from inventory import AssetChange
    from world_entity_protocol import VISIT_NPC
    from task_dialog_protocol import S_VISIT_NPC, decode_visit_npc
    from verify_runtime import Peer
    from wire import compact, read_compact
    import runtime_storage
    import npc_shop_sales

    async def run(store, prepared, role, npc):
        runtime = GameRuntime(store, prepared)
        try:
            peer = Peer(runtime)
            await peer.login(role)
            owner = runtime.roles[role['id']]
            await owner.io(runtime_storage.initialize_role_wallet, store, 1111, role['id'], owner.epoch,
                (1000, 0, 0, 0), 'explicit_migration')
            await owner.mailbox.call('settle', AssetChange('buyback-native-price-capture',
                grants=((40200, 1, 1), (40204, 1, 0), (32000, 2))))
            items = (await owner.io(owner.inventory.snapshot))['items']
            assert {(row['template_id'], row['quantity']) for row in items} == {(40200, 1), (40204, 1), (32000, 2)}
            npc_key = (npc.map_id << 32) | npc.placement_id
            menu = await peer.request(VISIT_NPC, struct.pack('>q', npc_key))
            assert any({2, 214} <= set(decode_visit_npc(body)[1]) for kind, body in menu if kind == S_VISIT_NPC)
            keys = tuple(row['id'] for row in items)
            request = struct.pack('>q', npc_key) + compact(len(keys)) + struct.pack('>' + 'i' * len(keys), *keys)
            messages = await peer.request(npc_shop_sales.SELL_ITEMS, request)
            body, = (body for kind, body in messages if kind == npc_shop_sales.REPURCHASE_ITEMS)
            assert (await owner.io(owner.inventory.snapshot))['items'] == []
            wallet = await owner.io(runtime_storage.wallet_snapshot, store, 1111, role['id'], owner.epoch)
            balances = {row.currency: row.balance for row in wallet}
            assert balances == {'cash': 8000, 'bound_silver': 400, 'yuanbao': 0, 'bound_yuanbao': 0}
            count, offset = read_compact(body, 12)
            assert count == 3
            records = []
            for index in range(count):
                start = offset + 48 * index
                template, flags, key, position = struct.unpack_from('>iiii', body, start)
                quantity, = struct.unpack_from('>i', body, start + 24)
                records.append(dict(template=template, flags=flags, key=key, position=position, quantity=quantity))
            offset += count * 48
            price_count, offset = read_compact(body, offset)
            assert price_count == count and len(body) == offset + price_count * 8
            prices = dict(struct.unpack_from('>ii', body, offset + index * 8) for index in range(price_count))
            expected_total = {40200: 250, 40204: 7000, 32000: 150}
            assert {row['template']: prices[row['key']] for row in records} == expected_total
            debits = []
            previous_cash = balances['cash']
            for row in records:
                repurchased = await peer.request(npc_shop_sales.REPURCHASE,
                    struct.pack('>qi', npc_key, row['key']))
                assert any(kind == npc_shop_sales.REPURCHASE_ITEMS for kind, _ in repurchased)
                current_wallet = await owner.io(runtime_storage.wallet_snapshot, store, 1111, role['id'], owner.epoch)
                current_cash = next(value.balance for value in current_wallet if value.currency == 'cash')
                charged = previous_cash - current_cash
                assert charged == expected_total[row['template']]
                debits.append(dict(template=row['template'], key=row['key'], quantity=row['quantity'], actual_cash_debit=charged))
                previous_cash = current_cash
            assert previous_cash == 600
            assert (await owner.io(owner.inventory.snapshot))['items'] == items
            return dict(npc_id=npc.npc_id, npc_key=npc_key, query_context_service_ids=[2, 214],
                source='Actual encrypted published SELL_ITEMS reply; original sale policy and transaction',
                protocol=hex(npc_shop_sales.REPURCHASE_ITEMS), body_hex=body.hex(),
                body_sha256=hashlib.sha256(body).hexdigest(), raw_item_records=records,
                raw_price_map=prices, actual_original_items=items,
                actual_wallet_after=balances, stock_or_price_packets_fabricated=False,
                actual_repurchase_debits=debits, final_cash_after_repurchase=previous_cash,
                exact_original_items_restored=True, quote_policy_changed=False)
        finally:
            await runtime.close()

    with tempfile.TemporaryDirectory(prefix='npc-buyback-price-frame-') as folder:
        store = AccountStore(Path(folder) / 'disposable.sqlite3')
        role = store.create_role(1111, '回购原价字段核对', 11, 1010109)
        prepared = runtime_storage.prepare(store)
        npc = next(p for rows in store.npc_resources[0].values() for p in rows if p.npc_id == 10011)
        store.save_position(1111, role['id'], (npc.map_id, npc.x, npc.y))
        result = asyncio.run(asyncio.wait_for(run(store, prepared, role, npc), 40))
    verify()
    origins = {}
    for name, module in tuple(sys.modules.items()):
        file = getattr(module, '__file__', None)
        if not file or name == '__main__':
            continue
        actual = Path(file).resolve()
        if actual.is_relative_to(ROOT):
            assert actual.parent in (source, harness), str(actual)
            origins[name] = str(actual)
    result.update(release=str(RELEASE), producer_sha256=sha(Path(__file__)),
        actual_project_module_origins=origins, source_inputs_preserved=len(published['sha256']),
        helper_inputs_preserved=len(context['harness_sha256']), config_inputs_preserved=len(context['workspace_sha256']),
        live_database_accessed=False, listener_started=False, service_or_GUI_changed=False,
        original_client_final_price_verified=False)
    (ROOT / 'evidence/npc-buyback-current-price-frame.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=lambda value: asdict(value)) + '\n', encoding='utf8')
    print('CAPTURED actual sale frame: three real cached instances, price-map250/7000/150; no policy edits')


if __name__ == '__main__':
    main()

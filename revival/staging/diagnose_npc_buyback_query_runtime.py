"""Actual merchant-tab query red, distinct from local configured purchase stock."""
import argparse
import asyncio
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--expect-missing', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((RELEASE / 'manifest.json').read_text(encoding='utf8'))
    candidate = json.loads((RELEASE / 'candidate.json').read_text(encoding='utf8'))
    source, harness = RELEASE / 'source', RELEASE / 'harness'

    def verify():
        for directory, entries in ((source, manifest['sha256']), (harness, candidate['harness_sha256']),
                (harness, candidate['harness_resource_sha256']),
                (harness / 'workspace', candidate['workspace_sha256'])):
            for name, digest in entries.items():
                assert sha(directory / name) == digest, name

    verify()
    sys.path[:0] = [str(harness), str(source)]
    import inspect_client
    inspect_client.ROOT, inspect_client.OUT = ROOT.parent, harness / 'workspace'
    from accounts import AccountStore
    from game_runtime import GameRuntime
    from inventory import QUERY_BAG
    from task_dialog_protocol import decode_visit_npc, S_VISIT_NPC
    from world_entity_protocol import VISIT_NPC
    from verify_runtime import Peer
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
            key = (npc.map_id << 32) | npc.placement_id
            menu = await peer.request(VISIT_NPC, struct.pack('>q', key))
            decoded = [decode_visit_npc(body) for kind, body in menu if kind == S_VISIT_NPC]
            assert any(2 in row[1] for row in decoded), decoded
            before = await owner.io(owner.inventory.snapshot)
            wallet = await owner.io(runtime_storage.wallet_snapshot, store, 1111, role['id'], owner.epoch)
            body = struct.pack('>iQ', 4, key)
            response = await peer.request(QUERY_BAG, body)
            assert await owner.io(owner.inventory.snapshot) == before
            assert await owner.io(runtime_storage.wallet_snapshot, store, 1111, role['id'], owner.epoch) == wallet
            return dict(npc_id=npc.npc_id, npc_key=key, menu_service_ids=[list(row[1]) for row in decoded],
                query_type=hex(QUERY_BAG), query_body=body.hex(),
                reply_types=[hex(kind) for kind, _ in response],
                native_buyback_listing_received=any(kind == npc_shop_sales.REPURCHASE_ITEMS for kind, _ in response),
                current_inventory_and_wallet_preserved=True,
                configured_purchase_stock=list(store.npc_gameplay.stock[npc.npc_id]),
                stock_is_separate_client_configuration_not_query4_instances=True,
                no_purchase_or_sale_executed=True)
        finally:
            await runtime.close()

    with tempfile.TemporaryDirectory(prefix='npc-buyback-query-red-') as folder:
        store = AccountStore(Path(folder) / 'disposable.sqlite3')
        role = store.create_role(1111, '商店回购查询反馈', 11, 1010109)
        prepared = runtime_storage.prepare(store)
        npc = next(p for rows in store.npc_resources[0].values() for p in rows if p.npc_id == 10004)
        assert store.npc_gameplay.stock[10004] == tuple(range(40103, 41004, 100))
        store.save_position(1111, role['id'], (npc.map_id, npc.x, npc.y))
        result = asyncio.run(asyncio.wait_for(run(store, prepared, role, npc), 30))
    verify()
    origins = {}
    for name, imported in tuple(sys.modules.items()):
        file = getattr(imported, '__file__', None)
        if not file or name == '__main__':
            continue
        actual = Path(file).resolve()
        if actual.is_relative_to(ROOT):
            assert actual.parent in (source, harness), str(actual)
            origins[name] = str(actual)
    result.update(release=str(RELEASE), probe_sha256=sha(Path(__file__)),
        source_inputs_preserved=len(manifest['sha256']), helper_inputs_preserved=len(candidate['harness_sha256']),
        config_inputs_preserved=len(candidate['workspace_sha256']), actual_project_module_origins=origins,
        source='Native tab classification awaiting its separate frozen research evidence',
        live_database_accessed=False, listener_started=False, service_or_GUI_changed=False,
        full_original_UI_or_complete_buyback_verified=False)
    (ROOT / 'evidence/npc-buyback-query-runtime-baseline.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('Merchant10004 query4/NPCkey listing received:', result['native_buyback_listing_received'])
    if args.expect_missing:
        assert not result['native_buyback_listing_received'], 'Gap no longer reproduces'
    else:
        assert result['native_buyback_listing_received'], 'Current NPC buyback tab query has no listing reply'


if __name__ == '__main__':
    main()

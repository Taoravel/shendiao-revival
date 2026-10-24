"""Actual published Owner receipts and original-column3 Peer acceptance.

An optional explicit one-module candidate replaces NPC repair only. Every other
gameplay/helper/config input remains in the approved immutable release.
"""
import argparse
import asyncio
from contextlib import closing
from dataclasses import asdict, is_dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'runtime/deployments/npc-repair-20261024T023920Z'
STABLE = 'npc-column-real-legacy-paid4'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def plain(value):
    if is_dataclass(value):
        return plain(asdict(value))
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def main():
    global ROOT, RELEASE
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=('legacy', 'candidate'), required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--npc-module', type=Path)
    parser.add_argument('--workspace-root', type=Path, default=ROOT)
    args = parser.parse_args()
    ROOT = args.workspace_root.resolve()
    RELEASE = ROOT / 'runtime/deployments/npc-repair-20261024T023920Z'
    assert not args.database.resolve().is_relative_to(ROOT / 'runtime')
    assert args.database.name == 'disposable.sqlite3' and args.database.resolve().is_relative_to(ROOT / 'evidence')
    assert not args.report.resolve().is_relative_to(RELEASE)
    manifest = json.loads((RELEASE / 'manifest.json').read_text(encoding='utf8'))
    candidate = json.loads((RELEASE / 'candidate.json').read_text(encoding='utf8'))
    source, harness = RELEASE / 'source', RELEASE / 'harness'
    override = args.npc_module.resolve() if args.npc_module else None
    override_sha = sha(override) if override else None

    def verify():
        for directory, entries in ((source, manifest['sha256']),
                (harness, candidate['harness_sha256']),
                (harness, candidate['harness_resource_sha256']),
                (harness / 'workspace', candidate['workspace_sha256'])):
            for name, digest in entries.items():
                assert sha(directory / name) == digest, name
        if override:
            assert sha(override) == override_sha

    verify()
    sys.path[:0] = [str(harness), str(source)]
    import inspect_client
    inspect_client.ROOT, inspect_client.OUT = ROOT.parent, harness / 'workspace'
    if override:
        assert args.phase == 'candidate' and override.name == 'npc_repairs.py'
        spec = importlib.util.spec_from_file_location('npc_repairs', override)
        module = importlib.util.module_from_spec(spec)
        sys.modules['npc_repairs'] = module
        spec.loader.exec_module(module)
    from accounts import AccountStore
    from game_runtime import GameRuntime
    from inventory import UNEQUIP_ITEM
    import runtime_storage
    from task_dialog_protocol import decode_visit_npc
    from world_entity_protocol import VISIT_NPC
    from verify_runtime import Peer
    import verify_npc_equipped_repair_runtime as fixture
    assert Path(fixture.__file__).resolve() == harness / 'verify_npc_equipped_repair_runtime.py'

    async def legacy(store, prepared, role, npc):
        original_peer = fixture.Peer
        seen = []

        class StableOwnerPeer(original_peer):
            async def request(self, kind, body):
                if kind != 0xc0413:
                    return await super().request(kind, body)
                assert struct.unpack('>iqii', body)[2] == 4
                owner = self.connection.rt.roles[role['id']]
                seen.append(dict(body=body.hex(), accepted_login_epoch=owner.epoch))
                # Historical command uses the existing public Owner Interface
                # to retain a real server retry ID; no receipt is fabricated.
                return await owner.mailbox.call('receive', kind, body, request_id=STABLE)

        fixture.Peer = StableOwnerPeer
        try:
            checked = await fixture.check(store, prepared, role, npc)
        finally:
            fixture.Peer = original_peer
        assert len(seen) == 1
        return dict(real_old_owner_receipt_created=True, stable_request_id=STABLE,
            actual_old_request_hex=seen[0]['body'], legacy_accepted_login_epoch=seen[0]['accepted_login_epoch'],
            role_id=role['id'], original_fixture=checked,
            historical_repair_entered_public_owner=True, encrypted_repair_claimed=False)

    async def check(store, prepared, role, npc):
        runtime = GameRuntime(store, prepared)
        try:
            peer = Peer(runtime)
            await peer.login(role)
            owner = runtime.roles[role['id']]
            key = (npc.map_id << 32) | npc.placement_id
            menu = await peer.request(VISIT_NPC, struct.pack('>q', key))
            assert 513 in decode_visit_npc(menu[-1][1])[1]

            async def state():
                return plain(dict(inventory=await owner.io(owner.inventory.snapshot),
                    wallet=await owner.io(runtime_storage.wallet_snapshot, store, 1111,
                        role['id'], owner.epoch)))

            original = await state()
            item = original['inventory']['items'][0]
            assert item['equipment_slot'] == 0
            item_key = item['id']
            body = lambda column: struct.pack('>iqii', 2, key, column, item_key)

            async def paid(column):
                before = await state()
                try:
                    messages = await owner.mailbox.call('receive', 0xc0413, body(column), request_id=STABLE)
                except ValueError as error:
                    raise AssertionError('Real legacy paid4 cannot replay original-column' + str(column)) from error
                assert messages and any(kind == 0xc32c8 for kind, _ in messages)
                assert await state() == before, 'Paid repair rewrote current assets'

            await paid(4)
            await paid(3)
            conflict_before = await state()
            try:
                await owner.mailbox.call('receive', 0xc0413,
                    struct.pack('>iqii', 2, key, 3, item_key + 1), request_id=STABLE)
            except ValueError as error:
                assert str(error) == 'NPC repair retry intent conflict', str(error)
            else:
                raise AssertionError('Paid legacy identity accepted a different item')
            assert await state() == conflict_before

            def later_wear(inventory, request, loss):
                with closing(inventory.accounts.connect()) as db, db:
                    db.execute('BEGIN IMMEDIATE')
                    current = inventory.equipment_condition(db, item_key)
                    inventory.wear_equipment(db, item_key, request, current.version, loss)

            await owner.io(later_wear, owner.inventory, 'npc-column-later-wear', 5)
            dirty = await state()
            condition = dirty['inventory']['items'][0]['condition']
            assert condition['maximum'] - condition['current'] >= 5
            # A fresh wire4 must not inherit the ability to read a real paid4.
            assert await peer.request(0xc0413, body(4)) == []
            assert await state() == dirty
            native = await peer.request(0xc0413, body(3))
            assert native, 'Native original-column3 equipped repair did not respond'
            fixture.attributes(native)
            changed = await state()
            repaired = changed['inventory']['items'][0]
            assert repaired['equipment_slot'] == 0
            assert repaired['condition']['version'] == condition['version'] + 1
            cash = lambda snapshot: next(row['balance'] for row in snapshot['wallet'] if row['currency'] == 'cash')
            # Original level1 repair table's known per-unit cost2, already
            # exercised as40 for20 loss in the published fixture.
            expected_fee = 2 * (condition['maximum'] - condition['current'])
            assert cash(dirty) - cash(changed) == expected_fee
            await paid(4)
            await paid(3)
            assert await state() == changed
            await peer.request(UNEQUIP_ITEM, struct.pack('>ii', item_key, -1))
            moved = await state()
            assert moved['inventory']['items'][0]['equipment_slot'] is None
            await owner.io(later_wear, owner.inventory, 'npc-column-carried-wear', 1)
            moved = await state()
            carried_condition = moved['inventory']['items'][0]['condition']
            assert carried_condition['maximum'] > carried_condition['current']
            await paid(4)
            await paid(3)
            assert await state() == moved
            assert await peer.request(0xc0413, body(3)) == []
            assert await state() == moved
            return dict(real_legacy_paid4_new_lease_current_only=True,
                current_login_epoch=owner.epoch, changed_paid_item_rejected=True,
                native3_matches_existing_paid4_identity=True,
                fresh4_rejected_before_payment=True, actual_encrypted_native3_fresh_repair_passed=True,
                fresh3_wrong_owned_location_rejected=True, actual_native3_fee=expected_fee,
                later_paid4_and3_keep_newer_condition_wallet_and_carried_location=True,
                final_public_state=moved, source_inventory_refresh_column_still_legacy4=True,
                complete_original_GUI_or_shop_query_fixed=False)
        finally:
            await runtime.close()

    store = AccountStore(args.database)
    if args.phase == 'legacy':
        assert not override
        assert not store.roles(1111), 'Historical seed must use a new disposable database'
        role = store.create_role(1111, '原修理已付回放', 11, 1010109)
        prepared = runtime_storage.prepare(store)
        npc = next(p for entries in store.npc_resources[0].values() for p in entries if p.npc_id == 10004)
        store.save_position(1111, role['id'], (npc.map_id, npc.x, npc.y))
        result = asyncio.run(asyncio.wait_for(legacy(store, prepared, role, npc), 40))
    else:
        prepared = runtime_storage.prepare(store)
        npc = next(p for entries in store.npc_resources[0].values() for p in entries if p.npc_id == 10004)
        role, = store.roles(1111)
        result = asyncio.run(asyncio.wait_for(check(store, prepared, role, npc), 40))
    verify()
    origins = {}
    for name, module in tuple(sys.modules.items()):
        file = getattr(module, '__file__', None)
        if not file or name == '__main__':
            continue
        actual = Path(file).resolve()
        if actual.is_relative_to(ROOT):
            assert actual.parent in (source, harness) or (name == 'npc_repairs' and actual == override), str(actual)
            origins[name] = str(actual)
    result.update(phase=args.phase, process_id=os.getpid(), release=str(RELEASE), explicit_npc_module_override=str(override) if override else None,
        override_sha256=override_sha, probe_sha256=sha(Path(__file__)), actual_project_module_origins=origins,
        production_inputs_preserved=len(manifest['sha256']), helper_inputs_preserved=len(candidate['harness_sha256']),
        config_inputs_preserved=len(candidate['workspace_sha256']),
        database='caller-provided disposable database only', live_database_accessed=False,
        listener_started=False, service_or_GUI_changed=False)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('PASS repair-column', args.phase, 'with actual published imports and preserved inputs')


if __name__ == '__main__':
    main()

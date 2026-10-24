"""Change only the repair request's column in the published encrypted Peer test.

Column3 provenance is a separate native research question. This controlled
comparison records current behavior, not a claim of complete original GUI use.
"""
import argparse
import asyncio
from dataclasses import asdict, is_dataclass
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


def plain(value):
    if is_dataclass(value):
        return plain(asdict(value))
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expect-missing', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((RELEASE / 'manifest.json').read_text(encoding='utf8'))
    candidate = json.loads((RELEASE / 'candidate.json').read_text(encoding='utf8'))
    source, harness = RELEASE / 'source', RELEASE / 'harness'

    def verify():
        groups = ((source, manifest['sha256']), (harness, candidate['harness_sha256']),
            (harness, candidate['harness_resource_sha256']),
            (harness / 'workspace', candidate['workspace_sha256']))
        for directory, entries in groups:
            for name, digest in entries.items():
                assert sha(directory / name) == digest, name

    verify()
    sys.path[:0] = [str(harness), str(source)]
    import inspect_client
    inspect_client.ROOT, inspect_client.OUT = ROOT.parent, harness / 'workspace'
    from accounts import AccountStore
    import runtime_storage
    import verify_npc_equipped_repair_runtime as fixture
    assert Path(fixture.__file__).resolve() == harness / 'verify_npc_equipped_repair_runtime.py'
    original_peer = fixture.Peer
    captures = []

    async def run(column, store, prepared, role, npc):
        events = []

        class ColumnPeer(original_peer):
            async def login(self, value):
                self.fixture_role_id = value['id']
                return await super().login(value)

            async def request(self, kind, body):
                if kind != 0xc0413:
                    return await super().request(kind, body)
                method, key, original_column, item = struct.unpack('>iqii', body)
                assert method == 2 and original_column == 4
                owner = self.connection.rt.roles[self.fixture_role_id]

                async def current():
                    inventory = await owner.io(owner.inventory.snapshot)
                    wallet = await owner.io(runtime_storage.wallet_snapshot, store, 1111,
                        self.fixture_role_id, owner.epoch)
                    return plain(dict(inventory=inventory, wallet=wallet))

                before = await current()
                queries = []
                for query_column, target in ((3, 0), (4, 0), (4, key)):
                    bag = await super().request(0xc03f2, struct.pack('>iQ', query_column, target))
                    queries.append(dict(column=query_column, target=target,
                        replies=[dict(type=hex(k), body=b.hex()) for k, b in bag]))
                assert queries[0]['replies'] == [] and queries[1]['replies']
                assert queries[2]['replies'] == []
                request = struct.pack('>iqii', method, key, column, item)
                reply = await super().request(kind, request)
                after = await current()
                events.append(dict(column=column, item_key=item, before=before, after=after,
                    public_bag_queries=queries, native_request_hex=request.hex(),
                    replies=[dict(type=hex(k), body=b.hex()) for k, b in reply]))
                return reply

        fixture.Peer = ColumnPeer
        error = None
        try:
            await fixture.check(store, prepared, role, npc)
        except AssertionError as failure:
            error = str(failure)
        finally:
            fixture.Peer = original_peer
        assert len(events) == 1, 'Fixture failed before exact repair input'
        event = events[0]
        if column == 4:
            assert error is None, error
            assert event['before'] != event['after']
        else:
            assert error == 'Expected exactly one final role attribute map', error
            assert event['before'] == event['after'], 'Rejected repair unexpectedly changed current assets'
            assert event['replies'] == []
        event['original_fixture_assertion'] = error
        captures.append(event)

    for column in (4, 3):
        with tempfile.TemporaryDirectory(prefix='npc-repair-column-') as folder:
            store = AccountStore(Path(folder) / 'disposable.sqlite3')
            role = store.create_role(1111, '修理栏位对照', 11, 1010109)
            prepared = runtime_storage.prepare(store)
            npc = next(p for entries in store.npc_resources[0].values() for p in entries if p.npc_id == 10004)
            store.save_position(1111, role['id'], (npc.map_id, npc.x, npc.y))
            asyncio.run(asyncio.wait_for(run(column, store, prepared, role, npc), 30))
    verify()
    origins = {}
    for name, module in tuple(sys.modules.items()):
        file = getattr(module, '__file__', None)
        if not file or name == '__main__':
            continue
        path = Path(file).resolve()
        if path.is_relative_to(ROOT):
            assert path.parent in (source, harness), str(path)
            origins[name] = str(path)
    report = dict(release=str(RELEASE), source_inputs_unchanged=len(manifest['sha256']),
        helper_inputs_unchanged=len(candidate['harness_sha256']),
        config_inputs_unchanged=len(candidate['workspace_sha256']),
        actual_project_module_origins=origins,
        fixture_sha256=sha(Path(fixture.__file__)), probe_sha256=sha(Path(__file__)),
        comparisons=captures, column4_control_passed=True, column3_rejected_without_asset_change=True,
        own_bag_column3_rejected=True, legacy_column4_returns_own_equipment=True,
        column4_npc_target_rejected=True,
        source='Exact published encrypted equip/repair fixture; only its test caller repair-column changes',
        native_column3_full_provenance_verified=False, replacement_dispatcher=False,
        live_database_accessed=False, live_service_changed=False, gui_verified=False,
        methods=['diagnosing-bugs: single wire field control versus rejection on actual encrypted Peer',
            'tdd: preserve native-compatible acceptance red before any NPC production edit'])
    (ROOT / 'evidence/npc-repair-column-runtime-baseline.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('column4: original runtime fixture passes; column3: no reply, assets unchanged')
    if not args.expect_missing:
        raise AssertionError('Original repair column3 is rejected; native provenance still separately pending')


if __name__ == '__main__':
    main()

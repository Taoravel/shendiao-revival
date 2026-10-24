"""Audit published special-service boundaries using disposable startup state.

This is a public map/service seam check, not an encrypted Peer or GUI check.
All gameplay imports and configuration remain in the exact published release.
"""
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
    record = json.loads((RELEASE / 'candidate.json').read_text(encoding='utf8'))
    manifest = json.loads((RELEASE / 'manifest.json').read_text(encoding='utf8'))
    source, harness = RELEASE / 'source', RELEASE / 'harness'

    def verify():
        groups = ((source, manifest['sha256']), (harness, record['harness_sha256']),
            (harness, record['harness_resource_sha256']), (harness / 'workspace', record['workspace_sha256']))
        for directory, entries in groups:
            for name, digest in entries.items():
                assert sha(directory / name) == digest, name

    verify()
    sys.path[:0] = [str(harness), str(source)]
    import inspect_client
    inspect_client.ROOT, inspect_client.OUT = ROOT.parent, harness / 'workspace'
    from accounts import AccountStore
    import runtime_storage
    import npc_repairs
    from world_npcs import NpcScene
    from world_owner import MapAddress, Location

    with tempfile.TemporaryDirectory(prefix='npc-special-boundary-') as folder:
        store = AccountStore(Path(folder) / 'disposable.sqlite3')
        prepared = runtime_storage.prepare(store)
        resources = store.npc_gameplay
        bindings = resources.services.bindings
        scoped = {sid: [asdict(b) for b in bindings.values() if b.service_id == sid]
            for sid in (93, 160, 513, 855)}
        assert not any(scoped[sid] for sid in (93, 160, 855))
        assert len(scoped[513]) == 12
        parents = {parent: list(children) for parent, children in resources.services.children.items()
            if any(sid in children for sid in (93, 160, 855))}
        assert 855 in parents[1774]
        assert all(1774 not in menu for menu in resources.services.menus.values())
        placements, definitions = store.npc_resources
        target = next(p for entries in placements.values() for p in entries
            if (p.npc_id, 513) in bindings and p.map_id in prepared[3]
            and 0 <= p.x < prepared[3][p.map_id]['width']
            and 0 <= p.y < prepared[3][p.map_id]['height'])
        address = MapAddress(target.map_id, target.map_id, 0)
        key = (target.map_id << 32) | target.placement_id
        scene = NpcScene(address, (target,), prepared[3], binding_capacity=64,
            interaction_rules=store.npc_interaction_rules)
        scene.spawn(((key, target.placement_id),), definitions, batch_size=64)
        current = Location(1, 'disposable-scope-only', address, 1, target.x, target.y)
        proof = scene.interact(struct.pack('>q', key), current, current,
            request_id='special-boundary', now_ms=1, deadline_ms=10)
        kwargs = dict(request_id=proof.source_id, now_ms=1, deadline_ms=10)
        assert resources.services.plan(struct.pack('>qi', key, 513), proof, current,
            **kwargs).handler == 'equipment.repair'
        rejected = {}
        for sid in (93, 160, 855):
            try:
                resources.services.plan(struct.pack('>qi', key, sid), proof, current, **kwargs)
            except ValueError as error:
                rejected[sid] = str(error)
            else:
                raise AssertionError('Unactivated special service granted command')
        assert all(error == 'NPC service is not authorized' for error in rejected.values())
        # The original repair request contains method/key/column/item, no service
        # identifier. The current ordinary plan explicitly authorizes513.
        ordinary = npc_repairs.plan(resources, struct.pack('>iqii', 2, key, 1, 91),
            proof, current, **kwargs)
        assert ordinary.service.service_id == 513
        assert ordinary.service.handler == 'equipment.repair'
        result = dict(release=str(RELEASE), bindings=scoped, original_parent_references=parents,
            unactivated_parent1774_hidden=True, public_scope_fixture=asdict(target),
            rejected_special_services=rejected, ordinary_method2_service=ordinary.service.service_id,
            conclusions=['Actual registry authorizes no93/160/855, despite original labels and parent855',
                'Method2 has no serviceID; future special dispatch needs explicit NPC/type authorization',
                'No special asset mutation, fee or success semantics tested'],
            source_inputs_verified=len(manifest['sha256']), harness_inputs_verified=len(record['harness_sha256']),
            configuration_inputs_verified=len(record['workspace_sha256']),
            database='new disposable startup only; no role created',
            encrypted_peer_verified=False, actual_map_owner_verified=False,
            live_database_accessed=False, listener_started=False, live_service_changed=False,
            native_gui_verified=False)
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
    result['actual_project_module_origins'] = origins
    result['probe_sha256'] = sha(Path(__file__))
    path = ROOT / 'evidence/npc-special-repair-published-activation-audit.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('PASS published special-repair boundary: 1442 inputs; no93/160/855 activation')


if __name__ == '__main__':
    main()

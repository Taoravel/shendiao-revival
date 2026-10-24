"""Offline public MapOwner mailbox tracer; never touches live service or DB."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def check():
    from game_runtime import MapOwner, Position
    from world_protocol import ENTER_SCENE, scene_entry

    # Original scene encoder checks its startup catalog: use a real template
    # and a known valid prologue point, with an explicit offline map fixture.
    catalog = {1006: dict(available=True, width=8192, height=8192, portals={})}
    owner = MapOwner(1006, catalog)
    try:
        original = Position(1, 'root-owned-offline-join', (1006, 360, 2264), 1, (22, 141))
        joined = await owner.mailbox.call('join', original)
        current = await owner.mailbox.call('location', 1, original.epoch)
        declaration = await owner.mailbox.call('declare_movement', 1, original.epoch,
            current, 1, 'root-owned-scene', ENTER_SCENE,
            scene_entry(current.position, reason=0), 'normal_scene')
        await owner.mailbox.call('movement_will_send', 1, original.epoch, declaration)
        repeated = await owner.mailbox.call('join', joined)
        after = await owner.mailbox.call('location', 1, original.epoch)
        if repeated != joined or after != current:
            raise AssertionError('Idempotent join changed current position')
        # A retry of the same successful join must not revoke this exact send.
        await owner.mailbox.call('movement_will_send', 1, original.epoch, declaration)
        return dict(idempotent_join_preserved_pending_movement=True,
                    position_unchanged=True)
    finally:
        await owner.mailbox.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    if not (source / 'game_runtime.py').is_file():
        raise ValueError('Exact runtime source required')
    before = {str(p.relative_to(source)): digest(p) for p in source.rglob('*') if p.is_file()}
    sys.path.insert(0, str(source))
    import inspect_client
    inspect_client.ROOT = Path(__file__).resolve().parents[2]
    inspect_client.OUT = source
    result = dict(source=str(source), source_file_count=len(before),
                  live_socket=False, live_database=False, service_changed=False,
                  seam='Actual MapOwner.mailbox join/declare_movement/movement_will_send/location')
    try:
        result.update(asyncio.run(check()))
        result['passed'] = True
    except Exception as error:
        result.update(passed=False, error_type=type(error).__name__, error=str(error))
    after = {str(p.relative_to(source)): digest(p) for p in source.rglob('*') if p.is_file()}
    result['source_sha_stable'] = before == after
    result['source_sha256'] = before
    origins = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename and Path(filename).resolve().is_relative_to(source):
            origins[name] = str(Path(filename).resolve())
    result['actual_source_imports'] = origins
    result['probe_sha256'] = digest(Path(__file__))
    if not result['source_sha_stable']:
        result['passed'] = False
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items()
        if k not in ('source_sha256', 'actual_source_imports')}, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

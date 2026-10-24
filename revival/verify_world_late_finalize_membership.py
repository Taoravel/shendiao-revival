"""A historical source finalize must not remove a later runtime membership.

Actual MapOwner/SerialOwner public commands, trusted transfer fixtures only;
no GameRuntime socket, persistence, client, deployment or production mutation.
"""
import argparse
import asyncio
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time

if __name__ == '__main__':
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument('--runtime-source', type=Path)
    selected, _ = bootstrap.parse_known_args()
    if selected.runtime_source is not None:
        import inspect_client
        source = selected.runtime_source.resolve(strict=True)
        inspect_client.OUT = source
        sys.path.insert(0, str(source))

from game_runtime import MapOwner, Position
from runtime_core import StaleEpoch
from world_catalog import maps


def sources():
    paths = {name: Path(importlib.import_module(name).__file__).resolve()
             for name in ('game_runtime', 'runtime_core', 'runtime_movement',
                          'world_owner', 'world_catalog')}
    paths['probe'] = Path(__file__).resolve()
    return {name: {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            for name, path in paths.items()}


async def check(result):
    catalog = maps()
    source, target = MapOwner(1006, catalog), MapOwner(1007, catalog)
    try:
        initial = Position(1, 'lease-before-transfer', (1006, 360, 2264), 1, (22, 141))
        await source.mailbox.call('join', initial)
        location = await source.mailbox.call('location', initial.role_id, initial.epoch)
        offer = await source.mailbox.call('authorized_transfer', initial.role_id, initial.epoch,
            location, (1007, 8480, 6976), int(time.monotonic()*1000)+10000)
        reservation = await target.mailbox.call('reserve', offer)
        frozen = await source.mailbox.call('freeze', reservation)
        receipt = await target.mailbox.call('activate', frozen)
        assert await source.mailbox.call('finalize', receipt) == receipt
        await target.mailbox.call('ready', receipt.location)
        # Idempotent duplicate on an empty old source is a legitimate control.
        assert await source.mailbox.call('finalize', receipt) == receipt
        assert source.domain.location(initial.role_id) is None
        assert initial.role_id not in source.positions
        result['empty_source_duplicate_safe'] = True
        # Actual membership release/rejoin, not host assignments into caches.
        await target.mailbox.call('leave', initial.role_id, initial.epoch)
        replacement = Position(1, 'lease-after-transfer', (1006, 360, 2264), 10, (22, 141))
        await source.mailbox.call('join', replacement)
        current = await source.mailbox.call('location', replacement.role_id, replacement.epoch)
        assert current.login_epoch == replacement.epoch
        result['new_membership_before'] = dict(epoch=current.login_epoch,
            position=current.position, version=current.version)
        try:
            await source.mailbox.call('finalize', receipt)
        except ValueError as error:
            result['late_finalize_rejection'] = str(error)
        after = source.domain.location(replacement.role_id)
        cached = source.positions.get(replacement.role_id)
        result['domain_membership_unchanged'] = after == current
        result['runtime_cache_unchanged'] = cached == replacement
        try:
            observed = await source.mailbox.call('location', replacement.role_id, replacement.epoch)
        except StaleEpoch as error:
            result['new_membership_public_error'] = str(error)
            result['new_membership_publicly_readable'] = False
        else:
            result['new_membership_publicly_readable'] = observed == current
        assert result['domain_membership_unchanged']
        assert result['runtime_cache_unchanged'], 'Late historical finalize erased replacement runtime membership'
        assert result['new_membership_publicly_readable']
    finally:
        await source.mailbox.close()
        await target.mailbox.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-source', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    before = sources()
    result = dict(all_passed=False, native_gui_verified=False, live_server_changed=False,
        scope='actual map mailboxes; authorized transfer fixture; old receipt after newer source lease')
    try:
        asyncio.run(asyncio.wait_for(check(result), 10))
        result['all_passed'] = True
    except Exception as error:
        result['error'] = repr(error)
        raise
    finally:
        result.update(source=before, inputs_stable=before == sources())
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    assert result['inputs_stable']
    print(json.dumps({'all_passed': True, 'inputs_stable': True}))


if __name__ == '__main__':
    main()

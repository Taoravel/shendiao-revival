"""Verify map decisions with native fixtures while filesystem access is denied."""
from dataclasses import FrozenInstanceError
import json
import struct
from unittest.mock import patch
from inspect_client import OUT
from world_catalog import maps
from world_movement import plan_movement, ROLE_STOP


def main():
    catalog = maps()  # startup, before network/owner hot paths
    fixtures = json.loads((OUT/'evidence/movement-native-fixtures.json').read_text(encoding='utf-8'))['fixtures']
    source = (1007, 8480, 6976)
    with patch('builtins.open', side_effect=AssertionError('Hot-path file access')), \
         patch('io.open', side_effect=AssertionError('Hot-path file access')):
        plans = [plan_movement(source, (530, 436), f['type'], bytes.fromhex(f['body_hex']), catalog)
                 for f in fixtures]
        assert plans[0].position == source and not plans[0].checkpoint
        assert all(p.position == (1007, 8496, 6992) for p in plans[1:])
        transfer = plan_movement(source, (530, 436), ROLE_STOP,
                                 b'\0'+struct.pack('>hhQ', 8592, 7104, 0), catalog)
        assert transfer.source == source and transfer.transfer_target == (1014, 896, 3776)
        assert source == (1007, 8480, 6976)
    try:
        transfer.position = source
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError('Mutable movement result')
    try:
        catalog[1007]['portals'][(1, 1)] = (1014, 1, 1)
    except TypeError:
        pass
    else:
        raise AssertionError('Mutable shared catalog')
    print('PASS native fixtures: pure decisions, immutable results/catalog, transfer proposal only')


if __name__ == '__main__': main()

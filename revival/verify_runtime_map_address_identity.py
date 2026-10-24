"""Public runtime factory/lookup identity; no role admission or private entry."""
import asyncio
from pathlib import Path
import tempfile
from accounts import AccountStore
from game_runtime import GameRuntime
from inspect_client import OUT,write_json
from world_owner import MapAddress
import runtime_storage


async def check(store,prepared):
    runtime=GameRuntime(store,prepared)
    try:
        first=MapAddress(1501,42,0)
        second=MapAddress(1007,42,0)
        partition=MapAddress(1501,42,1)
        assert runtime.registered_map(first) is None
        a=runtime.map(first);b=runtime.map(second);c=runtime.map(partition)
        assert a is not b and a is not c and b is not c
        for address,owner in ((first,a),(second,b),(partition,c)):
            assert runtime.registered_map(address) is owner
            assert runtime.map(address) is owner and owner.domain.address==address
        public=runtime.map(1501)
        assert public is runtime.map(MapAddress(1501,1501,0)) and public is not a
        invalid=(True,False,None,1501.0,0,-1,2**63,
            MapAddress(True,42,0),MapAddress(1501,True,0),MapAddress(1501,42,False),
            MapAddress(2**63,42,0),MapAddress(1501,0,0),MapAddress(1501,2**63,0),
            MapAddress(1501,42,-1),MapAddress(1501,42,2**63))
        for value in invalid:
            for operation in (runtime.map,runtime.registered_map):
                try:operation(value)
                except ValueError:pass
                else:raise AssertionError('Malformed runtime map identity was admitted: '+repr(value))
        assert runtime.registered_map(first) is a and runtime.registered_map(second) is b
        assert runtime.registered_map(MapAddress(1501,43,0)) is None
        return dict(passed=['same instance/partition in distinct templates retains distinct owners',
            'partition identity remains distinct and exact lookup reuses each full address',
            'legacy integer public map aliases only its full public address',
            'malformed and boolean addresses reject without replacing prior owners; lookup does not create'],
            role_admission_verified=False,story_capacity_or_lifecycle_verified=False,
            live_server_changed=False,native_gui_verified=False,battle_executed=False)
    finally:await runtime.close()


def main():
    with tempfile.TemporaryDirectory(prefix='runtime-map-identity-') as directory:
        store=AccountStore(Path(directory)/'state.sqlite3')
        result=asyncio.run(check(store,runtime_storage.prepare(store)))
    write_json(OUT/'evidence/runtime-map-address-identity-verification.json',result)
    print(result)


if __name__=='__main__':main()

"""Real social startup accepts both JSON and immutable policy containers."""
import json
from pathlib import Path
import tempfile
from types import MappingProxyType
from accounts import AccountStore
from social_owner import SQLiteSocialStore
from guild_training import rules
from inspect_client import OUT,write_json


def main():
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'state.db')
        social=SQLiteSocialStore(accounts.path)
        social.initialize()
        frozen=social.organization_policy
        assert type(frozen['guild_initial_open_practices']) is tuple
        raw=json.loads((OUT/'design/recovery-baseline.json').read_text('utf-8'))['organizations']
        assert rules(raw)==rules(frozen)
        for bad in ((360001,),[360001]):
            try:rules(MappingProxyType(dict(frozen,guild_initial_open_practices=bad)))
            except ValueError:pass
            else:raise AssertionError('Nonempty designed baseline accepted')
    report=dict(passed=['actual SQLiteSocialStore.initialize freezes configuration lists and prepares organization schemas',
        'JSON and immutable organization policies produce identical training rules',
        'nonempty initial-practice baseline remains rejected for both container types'],live_store_changed=False)
    write_json(OUT/'evidence/guild-training-policy-verification.json',report);print(json.dumps(report))


if __name__=='__main__':main()

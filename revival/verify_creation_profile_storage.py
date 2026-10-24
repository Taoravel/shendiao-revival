"""Creation provenance redemption through the real storage Seam, offline only."""
from contextlib import closing,nullcontext
from dataclasses import replace
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from accounts import AccountStore
from currency import load_currency_rules
from inspect_client import OUT,write_json
from progression import credit_experience
from role_attribute_storage import read_attribute_snapshot,update_role_vitals
from runtime_core import StaleEpoch
import runtime_storage


def load(store,prepared,role,epoch):
    runtime_storage.load_role(store,1111,role['id'],epoch,prepared[0])
    return runtime_storage.role_load_profile(store,1111,role['id'],epoch)


def main():
    checks=[]
    with tempfile.TemporaryDirectory(prefix='creation-profile-') as directory:
        store=AccountStore(Path(directory)/'creation.sqlite3')
        old=store.create_role(1111,'旧创建记录',11,1010109)
        legacy=store.create_role(1111,'无创建记录',11,1010109)
        # Migrate the actual previous three-column provenance schema.
        with closing(store.connect()) as db,db:
            db.execute('CREATE TABLE role_restoration_origins '
                       '(role_id INTEGER PRIMARY KEY,origin TEXT NOT NULL,wallet_policy TEXT NOT NULL)')
            db.execute('INSERT INTO role_restoration_origins VALUES(?,?,?)',
                       (old['id'],'new_restoration_role',load_currency_rules().revision))
        prepared=runtime_storage.prepare(store)
        for role in (old,legacy):
            epoch=store.acquire_lease(1111,role['id'])
            assert load(store,prepared,role,epoch).attributes is None
        checks.append('old three-column origin and absent origin never initialize a profile')
        role=store.create_role(1111,'全新成长',11,1010109)
        with closing(store.connect()) as db:
            creation,receipt=db.execute('SELECT creation_profile,creation_profile_receipt '
                'FROM role_restoration_origins WHERE role_id=?',(role['id'],)).fetchone()
            assert json.loads(creation)['provenance']=='designed' and receipt is None
            assert db.execute('SELECT 1 FROM role_growth WHERE role_id=?',(role['id'],)).fetchone() is None
        epoch=store.acquire_lease(1111,role['id'])
        initial=load(store,prepared,role,epoch)
        assert (initial.growth.level,initial.growth.experience,initial.growth.free_points)==(1,0,0)
        assert initial.attributes.attributes.five_stats==(10,10,10,10,10)
        assert (initial.attributes.vitals.hp,initial.attributes.vitals.mp)==(100,100)
        assert initial.refresh[0]==0xc32c8
        checks.append('creation saves immutable designed template; first lease atomically initializes L1/XP0/19-map')
        with closing(store.leased(1111,role['id'],epoch).connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            current=read_attribute_snapshot(db,1111,role['id'],epoch)
            update_role_vitals(db,1111,role['id'],epoch,current.vitals,
                replace(current.vitals,hp=70,mp=40,version=current.vitals.version+1))
            credit_experience(db,1111,role['id'],150,store.growth_rules,store.attribute_rules,epoch)
        new_epoch=store.acquire_lease(1111,role['id'])
        resumed=load(store,prepared,role,new_epoch)
        assert (resumed.growth.level,resumed.growth.experience,resumed.growth.free_points)==(2,61,5)
        assert (resumed.attributes.vitals.hp,resumed.attributes.vitals.mp)==(80,46)
        assert load(store,prepared,role,new_epoch)==resumed
        try:load(store,prepared,role,epoch)
        except StaleEpoch:pass
        else:raise AssertionError('Old lease redeemed a creation profile')
        checks.append('reconnect preserves later XP/potential/wounds; redemption is idempotent and old epoch is fenced')
        for mutation in ('experience','policy','encoding','partial'):
            case=AccountStore(Path(directory)/f'{mutation}.sqlite3')
            resources=runtime_storage.prepare(case)
            fresh=case.create_role(1111,'异常创建',11,1010109)
            lease=case.acquire_lease(1111,fresh['id'])
            if mutation=='experience':
                with closing(case.connect()) as db,db:
                    db.execute('INSERT INTO role_progress VALUES(?,1)',(fresh['id'],))
            elif mutation=='policy':
                case.attribute_rules=replace(case.attribute_rules,revision='unreviewed-policy')
            elif mutation=='partial':
                load(case,resources,fresh,lease)
                with closing(case.connect()) as db,db:
                    db.execute('DELETE FROM role_attribute_snapshots WHERE role_id=?',(fresh['id'],))
            try:
                with (patch.object(runtime_storage,'growth_refresh',side_effect=ValueError('controlled encoding refusal'))
                      if mutation=='encoding' else nullcontext()):
                    load(case,resources,fresh,lease)
            except ValueError:pass
            else:raise AssertionError(f'{mutation} silently initialized/reset a profile')
            if mutation!='partial':
                with closing(case.connect()) as db:
                    for table in ('role_growth','role_attribute_baselines','role_attribute_snapshots'):
                        assert db.execute(f'SELECT 1 FROM {table} WHERE role_id=?',(fresh['id'],)).fetchone() is None
                    assert db.execute('SELECT creation_profile_receipt FROM role_restoration_origins '
                                      'WHERE role_id=?',(fresh['id'],)).fetchone()==(None,)
        checks.append('pre-login XP drift, policy changes and damaged initialized profiles refuse automatic repair')
        checks.append('native refresh encoding failure rolls back growth, attributes and creation receipt together')
    report=dict(passed=checks,database='disposable',live_server_changed=False,battle_executed=False,native_gui_verified=False)
    write_json(OUT/'evidence/creation-profile-storage-verification.json',report)
    print(report)


if __name__=='__main__':main()

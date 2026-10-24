"""Production settings through real organization storage; temporary accounts."""
from dataclasses import FrozenInstanceError
from pathlib import Path
from contextlib import closing
from dataclasses import replace
import asyncio,json,struct,tempfile
from verify_faction_payments import Fixture
from faction_domain import OrganizationStore
from inspect_client import OUT,write_json
import family_products_protocol as p


def make(directory):
    fixture=Fixture(Path(directory)/'products.db')
    command=fixture.family();fixture.fund(command)
    identity=fixture.org.execute(command,fixture.now())['organization']
    return fixture,identity


def check_baseline(f,family):
    state=f.org.family_products_snapshot(family)
    assert state.family==family and state.drug_open is False and state.special_open is False
    assert state.drug_stock==state.special_stock==0 and state.revision==1
    assert state.origin.startswith('designed_new_family')
    try:state.drug_stock=100
    except FrozenInstanceError:pass
    else:raise AssertionError('Mutable production state escaped the owner')


def check_settings(f,family):
    cash=f.cash(1);funds=f.org.family_assets(family).funds
    opened=f.cmd(1,family,'set_family_products',(1,-1))
    first=f.org.execute(opened,f.now())
    state=f.org.family_products_snapshot(family)
    assert state.drug_open and not state.special_open and state.revision==2
    assert f.org.family_assets(family).funds==funds
    assert f.org.execute(opened,f.now())==first
    assert f.org.family_products_snapshot(family)==state
    closed=f.cmd(1,family,'set_family_products',(0,-1))
    f.org.execute(closed,f.now())
    state=f.org.family_products_snapshot(family)
    assert not state.drug_open and state.revision==3
    assert f.org.family_assets(family).funds==funds-50000
    f.org.execute(closed,f.now())
    unchanged=f.cmd(1,family,'set_family_products',(0,-1))
    f.org.execute(unchanged,f.now())
    assert f.org.family_products_snapshot(family)==state
    assert f.org.family_assets(family).funds==funds-50000 and f.cash(1)==cash
    f.reject(lambda:f.org.execute(replace(closed,args=(-1,0)),f.now()),'request_id_conflict')


def check_permissions_rollback(f,family):
    before=f.org.family_products_snapshot(family)
    for actor in (2,16):
        f.reject(lambda actor=actor:f.org.execute(f.cmd(actor,family,'set_family_products',(1,-1)),f.now()),'permission_denied')
    for choices in ((True,-1),(1,False),(1,1),(-1,-1),(2,-1),(1,),()):
        f.reject(lambda choices=choices:f.org.execute(f.cmd(1,family,'set_family_products',choices),f.now()),'invalid_family_product_choice')
    assert f.org.family_products_snapshot(family)==before
    f.org.execute(f.cmd(1,family,'set_family_products',(-1,1)),f.now())
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE family_assets SET funds=49999 WHERE family=?',(family,))
    before=f.org.family_products_snapshot(family)
    close=f.cmd(1,family,'set_family_products',(-1,0))
    f.reject(lambda:f.org.execute(close,f.now()),'insufficient_family_funds')
    assert f.org.family_products_snapshot(family)==before and f.org.family_assets(family).funds==49999
    with closing(f.accounts.connect()) as db,db:
        assert not db.execute('SELECT 1 FROM organization_receipts WHERE actor=1 AND request_id=?',(close.request_id,)).fetchone()
        db.execute('UPDATE family_assets SET funds=50000 WHERE family=?',(family,))
        db.execute("CREATE TRIGGER reject_product_ledger BEFORE INSERT ON organization_fund_ledger WHEN NEW.reason='set_family_products' BEGIN SELECT RAISE(ABORT,'controlled_failure'); END")
    f.reject(lambda:f.org.execute(close,f.now()),'organization_constraint')
    assert f.org.family_products_snapshot(family)==before and f.org.family_assets(family).funds==50000
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER reject_product_ledger')
    f.org.execute(close,f.now())
    assert f.org.family_assets(family).funds==0 and not f.org.family_products_snapshot(family).special_open


def check_panel(f,family):
    panel=f.org.family_products_panel(1,f.epochs[1],family)
    assert panel.state==f.org.family_products_snapshot(family)
    assert (panel.level,panel.drug_cost,panel.special_cost)==(1,10000,15000)
    f.reject(lambda:f.org.family_products_panel(2,f.epochs[2],family),'permission_denied')
    f.reject(lambda:f.org.family_products_panel(1,'invalid-epoch',family),'stale_epoch')
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE organizations SET level=5 WHERE id=?',(family,))
    panel=f.org.family_products_panel(1,f.epochs[1],family)
    assert (panel.level,panel.drug_cost,panel.special_cost)==(5,50000,35000)
    assert p.information(panel.state,panel.drug_cost,panel.special_cost)==struct.pack('>QiiQii',50000,0,0,35000,0,0)
    for body in (b'',bytes(7),bytes(9),struct.pack('>ii',2,-1),struct.pack('>ii',-1,-1),struct.pack('>ii',1,1)):
        f.reject(lambda body=body:p.decode_set(body),'invalid_family_product_')


def check_restart_unknown(f,family):
    state=f.org.family_products_snapshot(family)
    reloaded=OrganizationStore(f.accounts.path,f.policy)
    reloaded.initialize()
    assert reloaded.family_products_snapshot(family)==state
    old_epoch=f.epochs[1]
    f.epochs[1]=f.accounts.acquire_lease(1111,1)
    stale=replace(f.cmd(1,family,'set_family_products',(1,-1)),epoch=old_epoch)
    f.reject(lambda:reloaded.execute(stale,f.now()),'stale_epoch')
    assert reloaded.family_products_snapshot(family)==state
    # Simulated historical missing settings: startup is never a migration grant.
    funds=f.org.family_assets(family).funds
    with closing(f.accounts.connect()) as db,db:db.execute('DELETE FROM family_products WHERE family=?',(family,))
    reloaded.initialize()
    f.reject(lambda:reloaded.family_products_snapshot(family),'family_products_unknown')
    f.reject(lambda:reloaded.execute(f.cmd(1,family,'set_family_products',(1,-1)),f.now()),'family_products_unknown')
    assert reloaded.family_assets(family).funds==funds


async def check_runtime(f,family):
    from game_runtime import GameRuntime
    from faction_runtime import OrganizationOutcome
    import runtime_storage
    for choices in ((1,-1),(-1,1)):f.org.execute(f.cmd(1,family,'set_family_products',choices),f.now())
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE family_assets SET funds=50000 WHERE family=?',(family,))
    cash=f.cash(1)
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    try:
        commands=[f.cmd(1,family,'set_family_products',choice) for choice in ((0,-1),(-1,0))]
        results=await asyncio.gather(*(runtime.social_runtime.organizations.command(c,f.now()) for c in commands),return_exceptions=True)
        assert sum(isinstance(value,OrganizationOutcome) for value in results)==1
        errors=[value for value in results if isinstance(value,Exception)]
        assert len(errors)==1 and str(errors[0])=='insufficient_family_funds'
        state=f.org.family_products_snapshot(family)
        assert sum((state.drug_open,state.special_open))==1
        assert f.org.family_assets(family).funds==0 and f.cash(1)==cash
        successful=commands[0] if isinstance(results[0],OrganizationOutcome) else commands[1]
        await runtime.social_runtime.organizations.command(successful,f.now())
        assert f.org.family_products_snapshot(family)==state
    finally:await runtime.close()


if __name__=='__main__':
    with tempfile.TemporaryDirectory() as directory:
        f,family=make(directory)
        check_baseline(f,family)
        check_settings(f,family)
        check_permissions_rollback(f,family)
        check_panel(f,family)
        check_restart_unknown(f,family)
    with tempfile.TemporaryDirectory() as directory:
        f,family=make(directory)
        asyncio.run(check_runtime(f,family))
    result=dict(passed=['explicit new family frozen production baseline; startup preserves historical unknown',
        'original independent open/close; closing charges family funds once; current-state no-op free',
        'nonleader/outsider/malformed input rejected; request-id intent fenced',
        'insufficient funds and late ledger fault roll back flags/revisions/fee/receipt',
        'leader/lease-gated current panel uses original per-level maintenance quote and native format',
        'restart preserves settings; replacement epoch rejects stale owner',
        'actual bounded organization runtime competes for final close fee with one whole success'],
        live_server_changed=False,native_gui_verified=False,npc_route_integrated=False,
        hourly_production_verified_here=False,whole_family_development_complete=False)
    write_json(OUT/'evidence/family-products-verification.json',result);print(json.dumps(result))

"""Family history through the same authorized organization projection."""
from pathlib import Path
from contextlib import closing
import tempfile,json,sqlite3
from verify_faction_payments import Fixture
from inspect_client import OUT,write_json

STAMP=1792800000000  # 2026-10-24 00:00:00 UTC, 08:00:00 Asia/Shanghai


def setup(directory):
    f=Fixture(Path(directory)/'history.db');f.now=lambda:STAMP
    command=f.family();f.fund(command)
    family=f.org.execute(command,f.now())['organization']
    return f,family,command


def view(f,family,role=1):
    generation=dict(f.org.family_audience(family).members)[role]
    return f.org.family_projection(role,f.epochs[role],family,generation,tuple(f.epochs.items())).view


def check_creation(directory):
    f,family,command=setup(directory)
    history=view(f,family).history
    assert [(c.template_id,c.parameters) for c in history]==[(1,('2026-10-24 08:00:00',))]
    f.org.execute(command,f.now());f.org.initialize()
    assert view(f,family).history==history


def check_leadership(directory):
    f,family,_=setup(directory)
    appoint=f.cmd(1,family,'appoint',(2,'deputy'));f.org.execute(appoint,f.now())
    assert len(view(f,family).history)==1
    transfer=f.cmd(1,family,'appoint',(2,'leader'));f.org.execute(transfer,f.now())
    assert [(c.template_id,c.parameters[-1]) for c in view(f,family).history]==[(1,'2026-10-24 08:00:00'),(4,'费用角色2')]
    f.org.execute(transfer,f.now()+1)
    f.org.execute(f.cmd(2,family,'appoint',(1,'deputy')),f.now())
    abdicate=f.cmd(2,family,'appoint',(2,'member'));f.org.execute(abdicate,f.now())
    assert [c.parameters[-1] for c in view(f,family).history[1:]]==['费用角色2','费用角色1']
    f.org.execute(abdicate,f.now()+1);assert len(view(f,family).history)==3


def check_levels(directory):
    from inventory import Inventory,AssetChange
    from family_donation import pay
    from verify_family_donation import encode
    from verify_family_maintenance import tick
    f,family,_=setup(directory)
    f.accounts.inventory_config=Inventory.prepare(f.accounts)
    inv=Inventory(f.accounts,1111,1,epoch=f.epochs[1],currency_rules=f.rules)
    f.tx(1,lambda db:inv.apply_settlement(db,AssetChange('history-boxes',grants=((36076,20,1),))))
    key=inv.immutable_snapshot().items[0].id
    reserve=f.cmd(1,family,'reserve_family_donation',(20,((key,20),)))
    f.org.execute(reserve,f.now())
    f.tx(1,lambda db:pay(db,1111,1,f.epochs[1],family,reserve.request_id,f.now(),f.org.donation_rules,inv,precommit=encode))
    resolve=f.cmd(1,family,'resolve_family_donation',(reserve.request_id,))
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER history_donation_failure BEFORE INSERT ON family_donation_receipts BEGIN SELECT RAISE(ABORT,'history_donation_failure'); END")
    f.reject(lambda:f.org.execute(resolve,f.now()),'organization_constraint')
    assert len(view(f,family).history)==1 and f.org.family_assets(family).funds==3000000
    assert inv.immutable_snapshot().items==()
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER history_donation_failure')
    f.org.execute(resolve,f.now())
    assert [(r.template_id,r.parameters[-1]) for r in view(f,family).history]==[(1,'2026-10-24 08:00:00'),(2,'2')]
    f.org.execute(resolve,f.now()+1)
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE family_assets SET funds=0 WHERE family=?',(family,))
    before=view(f,family);clock=f.org.family_maintenance_snapshot(family)
    with closing(f.accounts.connect()) as db,db:
        db.execute("CREATE TRIGGER history_hour_failure BEFORE INSERT ON family_maintenance_receipts BEGIN SELECT RAISE(ABORT,'history_hour_failure'); END")
    try:tick(f,family)
    except sqlite3.IntegrityError:pass
    else:raise AssertionError('Controlled hourly receipt failure did not fire')
    assert view(f,family)==before and f.org.family_maintenance_snapshot(family)==clock
    with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER history_hour_failure')
    command,result=tick(f,family)
    assert result.level_after==1
    assert [(r.template_id,r.parameters) for r in view(f,family).history[1:]]==[
        (2,('2026-10-24 08:00:00','2')),(3,('2026-10-24 09:00:00','1'))]
    f.org.maintain_family(command,command.due_ms+1);assert len(view(f,family).history)==3


def check_rollback(directory):
    f,family,_=setup(directory)
    f.org.execute(f.cmd(1,family,'appoint',(2,'deputy')),f.now())
    before=view(f,family);command=f.cmd(1,family,'appoint',(2,'leader'))
    for table in ('family_history','organization_receipts'):
        with closing(f.accounts.connect()) as db,db:
            db.execute(f"CREATE TRIGGER history_late_failure BEFORE INSERT ON {table} BEGIN SELECT RAISE(ABORT,'history_failure'); END")
        try:f.org.execute(command,f.now())
        except (sqlite3.IntegrityError,ValueError) as error:assert str(error) in ('history_failure','organization_constraint')
        else:raise AssertionError('Controlled history/receipt failure did not fire')
        assert view(f,family)==before and f.org.snapshot(family)[0]['leader']==1
        with closing(f.accounts.connect()) as db,db:db.execute('DROP TRIGGER history_late_failure')
    f.org.execute(command,f.now());assert len(view(f,family).history)==2


def check_legacy_and_scope(directory):
    f,family,_=setup(directory)
    with closing(f.accounts.connect()) as db,db:db.execute('DELETE FROM family_history WHERE family=?',(family,))
    f.org.initialize();assert view(f,family).history==()
    generation=dict(f.org.family_audience(family).members)[2]
    f.org.execute(f.cmd(2,family,'leave'),f.now())
    f.reject(lambda:f.org.family_projection(2,f.epochs[2],family,generation,()),'stale_family_membership')
    f.reject(lambda:f.org.family_projection(16,f.epochs[16],family,generation,()),'stale_family_membership')
    f.org.execute(f.cmd(1,family,'appoint',(3,'deputy')),f.now())
    f.org.execute(f.cmd(1,family,'appoint',(3,'leader')),f.now())
    assert [r.template_id for r in view(f,family).history]==[4]


def check_budget(directory):
    f,family,_=setup(directory);leader=1
    for _ in range(105):
        target=3-leader
        f.org.execute(f.cmd(leader,family,'appoint',(target,'deputy')),f.now())
        f.org.execute(f.cmd(leader,family,'appoint',(target,'leader')),f.now())
        leader=target
    history=view(f,family).history
    assert len(history)==100 and all(row.template_id==4 for row in history)
    assert history[0].parameters[-1]=='费用角色1' and history[-1].parameters[-1]=='费用角色2'
    f.org.initialize();assert view(f,family).history==history


if __name__=='__main__':
    with tempfile.TemporaryDirectory() as directory:check_creation(directory)
    with tempfile.TemporaryDirectory() as directory:check_leadership(directory)
    with tempfile.TemporaryDirectory() as directory:check_levels(directory)
    for check in (check_rollback,check_legacy_and_scope,check_budget):
        with tempfile.TemporaryDirectory() as directory:check(directory)
    result=dict(passed=['successful family creation records one original course and replay/startup never duplicates it',
        'direct transfer and native self-abdication record the actual new leader; ordinary appointment does not',
        'silver-box upgrade and hourly downgrade histories/levels roll back on late receipt failure and settle once on retry',
        'history insertion and final command-receipt failures roll leadership and history back together',
        'unknown legacy history stays empty; departed and unrelated roles cannot query the family projection',
        '105 real leadership transfers retain an ordered bounded panel of the latest 100 across startup'],
        native_gui_verified=False,live_server_changed=False)
    write_json(OUT/'evidence/family-history-verification.json',result);print(json.dumps(result))

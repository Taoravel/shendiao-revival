"""Organization funds are distinct from role cash; disposable account fixture."""
import json
import hashlib
import sqlite3
import asyncio
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import tempfile
from verify_faction_payments import Fixture
from inspect_client import OUT,write_json
from currency import CurrencyChange,apply_currency
from faction_domain import OrganizationStore


def legacy_cash_intent(f,command,*,committed=False):
    """Historical pre-correction state, using the real old cash transaction.

    This is explicit migration test data. Production has no legacy mint/debit
    entry and the current payment Interface refuses to create this intent.
    """
    fp=OrganizationStore.fingerprint(command)
    key=hashlib.sha256(json.dumps([command.actor,command.request_id],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    debit,refund='organization:debit:'+key,'organization:refund:'+key
    def write(db):
        amount=f.policy['family_aim_fee']
        apply_currency(db,1111,command.actor,command.epoch,
            CurrencyChange(debit,'family_aim_update','organization-intent:'+fp,(('cash',-amount),)),f.rules)
        f.org.record_funding(db,command,amount)
        db.execute('INSERT INTO organization_payments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (command.actor,command.request_id,fp,command.organization,command.operation,json.dumps(command.args,ensure_ascii=False),
             amount,'family_aim_update',f.rules.revision,debit,refund,'funded',f.now(),f.now()))
        if committed:
            db.execute('UPDATE organization_funding SET consumed=1 WHERE actor=? AND request_id=?',(command.actor,command.request_id))
            revision=db.execute('SELECT revision FROM organizations WHERE id=?',(command.organization,)).fetchone()[0]
            result=dict(organization=command.organization,revision=revision+1)
            db.execute('UPDATE organizations SET aim=?,revision=revision+1 WHERE id=?',(command.args[0],command.organization))
            db.execute('INSERT INTO organization_receipts VALUES(?,?,?,?)',(command.actor,command.request_id,fp,json.dumps(result)))
    f.tx(command.actor,write)


async def runtime_spend(f,identity):
    from game_runtime import GameRuntime
    from faction_runtime import OrganizationOutcome
    import runtime_storage
    runtime=GameRuntime(f.accounts,runtime_storage.prepare(f.accounts))
    try:
        before=f.cash(2)
        results=await asyncio.gather(*(runtime.social_runtime.organizations.command(
            f.cmd(2,identity,'change_aim',(aim,)),f.now()) for aim in ('并发宗旨甲','并发宗旨乙')),return_exceptions=True)
        assert sum(isinstance(r,OrganizationOutcome) for r in results)==1
        rejected=[r for r in results if isinstance(r,Exception)]
        assert len(rejected)==1 and str(rejected[0])=='insufficient_family_funds'
        assert f.org.family_assets(identity).funds==0 and f.cash(2)==before
        assert not runtime.social_runtime.organizations.owners
    finally:await runtime.close()


def guild_check(directory,checks):
    f=Fixture(Path(directory)/'guild.db')
    create=f.family();f.fund(create);family=f.org.execute(create,f.now())['organization']
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE organizations SET level=3 WHERE id=?',(family,))
    create_guild=f.cmd(1,family,'create_guild',('资金帮派','同心协力',create.args[2]));f.fund(create_guild)
    guild=f.org.execute(create_guild,f.now())['organization']
    initial=f.org.guild_assets(guild)
    assert initial.funds==f.policy['guild_initial_funds']==0 and initial.origin.startswith('designed_')
    cash=f.cash(1);family_funds=f.org.family_assets(family).funds
    aim=f.cmd(1,guild,'change_aim',('帮派新宗旨',))
    f.reject(lambda:f.fund(aim),'guild_aim_uses_organization_funds')
    f.reject(lambda:f.org.execute(aim,f.now()),'insufficient_guild_funds')
    assert f.cash(1)==cash and f.org.family_assets(family).funds==family_funds
    # Explicit funded-guild test state, not a implemented contribution reward.
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE guild_assets SET funds=600000 WHERE guild=?',(guild,))
    f.org.execute(aim,f.now());assert f.org.guild_assets(guild).funds==300000
    f.org.execute(aim,f.now());assert f.org.guild_assets(guild).funds==300000
    assert f.cash(1)==cash and f.org.family_assets(family).funds==family_funds
    with closing(f.accounts.connect()) as db,db:
        db.execute("INSERT INTO organizations(id,kind,name,aim,leader) VALUES(9992,'guild','旧档帮派','原来宗旨',1)")
    f.org.initialize()
    f.reject(lambda:f.org.guild_assets(9992),'guild_assets_unknown')
    checks.append('guild aim charges native-message 300000 guild funds once; never family funds/cash; new baseline explicitly designed, old unknown funds untouched')


def main():
    checks=[]
    with tempfile.TemporaryDirectory() as directory:
        f=Fixture(Path(directory)/'state.db')
        create=f.family();f.fund(create)
        identity=f.org.execute(create,f.now())['organization']
        aim=f.cmd(1,identity,'change_aim',('组织新宗旨',))
        cash=f.cash(1)
        try:f.fund(aim)
        except ValueError as error:assert str(error)=='family_aim_uses_organization_funds'
        else:raise AssertionError('Family aim still debits role cash instead of organization funds')
        assert f.cash(1)==cash
        initial=f.org.family_assets(identity)
        assert initial.funds==3_000_000 and initial.popularity==1000 and initial.founder_name=='费用角色1'
        checks.append('new family receives explicit guide-supported organization funds/popularity and founder identity')
        made=f.org.execute(aim,f.now())
        expected=initial.funds-f.policy['family_aim_fee']
        assert f.org.family_assets(identity).funds==expected and f.cash(1)==cash
        assert f.org.execute(aim,f.now())==made and f.org.family_assets(identity).funds==expected
        assert f.org.execute(create,f.now())['organization']==identity and f.org.family_assets(identity).funds==expected
        checks.append('new aim uses organization funds once, never role cash; replay does not regrant initial funds')
        f.reject(lambda:f.org.execute(f.cmd(2,identity,'change_aim',('越权新宗旨',)),f.now()),'permission_denied')
        assert f.org.family_assets(identity).funds==expected
        rollback=f.cmd(1,identity,'change_aim',('原子新宗旨',),'funds-rollback')
        before=f.org.snapshot(identity)
        with closing(f.accounts.connect()) as db,db:
            db.execute("CREATE TRIGGER fixture_receipt_failure BEFORE INSERT ON organization_receipts WHEN NEW.request_id='funds-rollback' BEGIN SELECT RAISE(ABORT,'fixture_failure'); END")
        try:f.org.execute(rollback,f.now())
        except sqlite3.IntegrityError:pass
        else:raise AssertionError('Expected receipt failure')
        assert f.org.snapshot(identity)==before and f.org.family_assets(identity).funds==expected
        with closing(f.accounts.connect()) as db,db:
            assert not db.execute('SELECT 1 FROM organization_fund_ledger WHERE request_id=?',(rollback.request_id,)).fetchone()
            db.execute('DROP TRIGGER fixture_receipt_failure')
        checks.append('permissions and receipt-write failure preserve funds, aim, revision and ledger atomically')
        # Prior cash intents remain recoverable but cannot also debit family funds.
        legacy=f.cmd(1,identity,'change_aim',('旧款新宗旨',));legacy_cash_intent(f,legacy)
        assert f.cash(1)==cash-f.policy['family_aim_fee'] and f.fund(legacy).status=='funded'
        f.reject(lambda:f.org.execute(legacy,f.now()),'legacy_cash_aim_requires_revoke')
        assert f.org.family_assets(identity).funds==expected
        assert f.org.revoke_funding(legacy,f.now()).status=='revoked'
        assert f.resolve(legacy).status=='refunded' and f.cash(1)==cash
        assert f.fund(legacy).status=='refunded' and f.cash(1)==cash
        new_intent=replace(legacy,request_id='correct-family-funds')
        f.org.execute(new_intent,f.now());expected-=f.policy['family_aim_fee']
        assert f.org.family_assets(identity).funds==expected and f.cash(1)==cash
        checks.append('old pending cash aim is cancelled/refunded once before a fresh family-funded intent; no double pool charge')
        committed=f.cmd(1,identity,'change_aim',('已成旧宗旨',));legacy_cash_intent(f,committed,committed=True)
        assert f.org.revoke_funding(committed,f.now()).status=='committed'
        assert f.fund(committed).status==f.resolve(committed).status=='committed'
        before=f.org.family_assets(identity)
        f.org.execute(committed,f.now())
        assert f.org.family_assets(identity)==before and f.cash(1)==cash-f.policy['family_aim_fee']
        checks.append('already committed historical cash receipts replay without a second family debit or refund')
        f.reject(lambda:f.org.execute(f.cmd(1,identity,'appoint',(2,'leader')),f.now()),'deputy_required_for_leadership')
        f.reject(lambda:f.org.execute(f.cmd(1,identity,'appoint',(1,'member')),f.now()),'deputy_required')
        f.org.execute(f.cmd(1,identity,'appoint',(2,'deputy')),f.now())
        f.org.execute(f.cmd(1,identity,'appoint',(1,'deputy')),f.now())
        assert f.org.snapshot(identity)[0]['leader']==2
        # A self-demotion moves the former deputy to leader and leaves exactly
        # one new deputy; the next native self-demotion can select member.
        f.org.execute(f.cmd(2,identity,'appoint',(2,'member')),f.now())
        assert f.org.snapshot(identity)[0]['leader']==1
        f.org.execute(f.cmd(1,identity,'appoint',(2,'deputy')),f.now())
        f.org.execute(f.cmd(1,identity,'appoint',(2,'leader')),f.now())
        checks.append('native abdication to existing deputy supports self-member/self-deputy; ordinary member cannot skip deputy to leader')
        assert f.org.family_assets(identity).founder_name==initial.founder_name
        with closing(f.accounts.connect()) as db,db:
            db.execute('INSERT INTO organizations(id,kind,name,aim,leader) VALUES(999,\'family\',\'旧档家族\',\'原来宗旨\',16)')
        f.org.initialize()
        f.reject(lambda:f.org.family_assets(999),'family_assets_unknown')
        f.reject(lambda:f.org.execute(f.cmd(16,999,'change_aim',('不补初始款',)),f.now()),'family_assets_unknown')
        assert f.org.family_assets(identity)==before
        checks.append('founder survives transfer; startup migration neither resets known balances nor grants unknown old families')
        with closing(f.accounts.connect()) as db,db:
            db.execute('UPDATE family_assets SET funds=? WHERE family=?',(f.policy['family_aim_fee'],identity))
        asyncio.run(runtime_spend(f,identity))
        checks.append('actual per-family runtime owner serializes two spends against one-fee balance: one succeeds, one rejects, role cash unchanged')
        # Controlled low-balance fixture tests exact rejection without issuing
        # dozens of unrelated paid changes; all assertions use public outcomes.
        with closing(f.accounts.connect()) as db,db:
            db.execute('UPDATE family_assets SET funds=? WHERE family=?',(f.policy['family_aim_fee']-1,identity))
        low=f.org.family_assets(identity);old=f.org.snapshot(identity)
        f.reject(lambda:f.org.execute(f.cmd(2,identity,'change_aim',('余额不足宗旨',)),f.now()),'insufficient_family_funds')
        assert f.org.family_assets(identity)==low and f.org.snapshot(identity)==old
        checks.append('insufficient organization funds leave all state unchanged')
        with closing(f.accounts.connect()) as db,db:
            original=tuple(db.execute('SELECT * FROM organization_fund_ledger WHERE organization=? ORDER BY request_id',(identity,)))
            db.execute('''CREATE TABLE family_fund_ledger AS SELECT organization AS family,actor,request_id,reason,delta,balance,created_ms
                FROM organization_fund_ledger WHERE organization=?''',(identity,))
            db.execute('DELETE FROM organization_fund_ledger WHERE organization=?',(identity,))
        f.org.initialize()
        with closing(f.accounts.connect()) as db,db:
            assert tuple(db.execute('SELECT * FROM organization_fund_ledger WHERE organization=? ORDER BY request_id',(identity,)))==original
            db.execute("UPDATE family_fund_ledger SET balance=balance+1 WHERE reason='new_family'")
        f.reject(f.org.initialize,'organization_fund_ledger_conflict')
        with closing(f.accounts.connect()) as db,db:
            assert tuple(db.execute('SELECT * FROM organization_fund_ledger WHERE organization=? ORDER BY request_id',(identity,)))==original
            db.execute("UPDATE family_fund_ledger SET balance=balance-1 WHERE reason='new_family'")
        checks.append('earlier family-only ledger migrates without lost records; conflicting copied history fails without overwriting')
        guild_check(directory,checks)
    report=dict(passed=checks,native_gui_verified=False,live_store_changed=False,
                provenance='family initial funds/popularity from PC guide; family/guild aim amounts and fund pools from native messages; new guild funds zero explicitly designed pending original baseline')
    write_json(OUT/'evidence/faction-family-funds-verification.json',report)
    print(json.dumps(report))


if __name__=='__main__':main()

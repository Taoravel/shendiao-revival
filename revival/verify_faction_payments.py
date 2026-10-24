"""Actual wallet debit, organization commit/revoke and recovery in disposable DBs."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import threading
import time
import uuid
from unittest.mock import patch
from accounts import AccountStore,FencedConnection
from currency import load_currency_rules,prepare_wallet_storage,initialize_wallet,read_wallet,WalletNotInitialized
from faction_domain import OrganizationStore,OrganizationCommand
from faction_payments import OrganizationPayments,prepare_payment_storage
from runtime_core import BlockingIO,SerialOwner,StaleEpoch
from inspect_client import OUT,write_json


class Fixture:
    def __init__(self,path):
        self.accounts=AccountStore(path)
        self.rules=load_currency_rules()
        self.policy=json.loads((OUT/'design/recovery-baseline.json').read_text(encoding='utf-8'))['organizations']
        with closing(self.accounts.connect()) as db,db:
            for rid in range(1,19):
                db.execute('INSERT INTO roles(id,account_id,name,school,shape,level) VALUES(?,1111,?,12,1010101,40)',(rid,f'费用角色{rid}'))
            prepare_wallet_storage(db)
            prepare_payment_storage(db)
        self.epochs={rid:self.accounts.acquire_lease(1111,rid) for rid in range(1,19)}
        self.org=OrganizationStore(path,self.policy);self.org.initialize()
        self.payments=OrganizationPayments(self.policy,self.rules)
        # Explicit test baselines; no live wallet migration or production grants.
        for rid,cash in ((1,20_000_000),(2,100),(16,1_000_000)):
            self.tx(rid,lambda db,rid=rid,cash=cash:initialize_wallet(db,1111,rid,self.epochs[rid],
                (cash,99_000_000,0,0),'explicit_migration',self.rules))

    def tx(self,rid,operation):
        with closing(FencedConnection(self.accounts.connect(),rid,self.epochs[rid])) as db,db:
            db.execute('BEGIN IMMEDIATE')
            return operation(db)

    def now(self):return int(time.time()*1000)

    def cmd(self,rid,org,op,args=(),key=None):
        return OrganizationCommand(rid,self.epochs[rid],key or uuid.uuid4().hex,self.now()+60_000,org,op,args)

    def family(self,rid=1,name='现金家族'):
        ids=range(1,16) if rid==1 else (16,17,18)
        return self.cmd(rid,0,'create_family',(name,'同心协力',tuple((i,self.epochs[i]) for i in ids)))

    def fund(self,c,payments=None):
        return self.tx(c.actor,lambda db:(payments or self.payments).fund(db,1111,c.actor,self.epochs[c.actor],c,self.now()))

    def resolve(self,c):
        return self.tx(c.actor,lambda db:self.payments.resolve(db,1111,c.actor,self.epochs[c.actor],c.request_id,self.now()))

    def wallet(self,rid):return self.tx(rid,lambda db:read_wallet(db,1111,rid,self.epochs[rid],self.rules))

    def cash(self,rid):return next(b.balance for b in self.wallet(rid) if b.currency=='cash')

    def reject(self,operation,contains):
        try:operation()
        except (ValueError,RuntimeError) as error:assert contains in str(error),(str(error),contains)
        else:raise AssertionError('Expected rejection: '+contains)


def check(f,passed):
    original=f.wallet(1)
    create=f.family()
    funded=f.fund(create)
    fee=f.policy['family_create_fee']
    assert funded.status=='funded' and f.cash(1)==20_000_000-fee
    assert next(b for b in f.wallet(1) if b.currency=='bound_silver')==original[1]
    assert f.fund(create).status=='funded' and f.cash(1)==20_000_000-fee
    made=f.org.execute(create,f.now());family=made['organization']
    assert f.org.execute(create,f.now())==made
    assert f.resolve(create).status==f.fund(create).status=='committed'
    assert len(f.org.snapshot(family)[1])==15
    passed.append('real cash debit, immutable grant and recovery record commit atomically; retry creates/charges only once')
    f.reject(lambda:f.fund(replace(create,args=('不同名称',*create.args[1:]))),'payment_intent_conflict')
    low=f.family(2)
    f.reject(lambda:f.fund(low),'Insufficient')
    assert f.cash(2)==100 and f.wallet(2)[1].balance==99_000_000
    missing=f.cmd(3,0,'create_family',create.args)
    try:f.fund(missing)
    except WalletNotInitialized:pass
    else:raise AssertionError('Missing wallet was silently initialized')
    with closing(f.accounts.connect()) as db:
        assert not db.execute('SELECT 1 FROM role_wallet_profiles WHERE role_id=3').fetchone()
        assert not db.execute('SELECT 1 FROM organization_payments WHERE actor IN (2,3)').fetchone()
    passed.append('large bound-silver balance cannot fund insufficient cash; missing profiles stay uninitialized')
    rollback=f.family(name='回滚家族')
    before=f.wallet(1)
    def fail(db):
        f.payments.fund(db,1111,1,f.epochs[1],rollback,f.now())
        db.execute('UPDATE roles SET level=41 WHERE id=1')
        raise RuntimeError('controlled_outer_failure')
    f.reject(lambda:f.tx(1,fail),'controlled_outer_failure')
    assert f.wallet(1)==before
    with closing(f.accounts.connect()) as db:
        assert db.execute('SELECT level FROM roles WHERE id=1').fetchone()[0]==40
        assert not db.execute('SELECT 1 FROM organization_funding WHERE actor=1 AND request_id=?',(rollback.request_id,)).fetchone()
        assert not db.execute('SELECT 1 FROM organization_payments WHERE actor=1 AND request_id=?',(rollback.request_id,)).fetchone()
    passed.append('outer failure rolls back cash, currency receipt, grant, payment intent and other role writes together')
    # Fee is consumed before the duplicate-name INSERT; that whole organization
    # tx rolls back, leaving an available grant but still-debited role wallet.
    failed=f.family(16,name='现金家族')
    cash=f.cash(16);f.fund(failed)
    f.reject(lambda:f.org.execute(failed,f.now()),'organization_constraint')
    assert f.resolve(failed).status=='funded' and f.cash(16)==cash-fee
    assert f.org.revoke_funding(failed,f.now()).status=='revoked'
    assert f.resolve(failed).status==f.fund(failed).status=='refunded' and f.cash(16)==cash
    assert f.resolve(failed).status=='refunded' and f.cash(16)==cash
    cancelled=f.family(16,name='撤销家族');f.fund(cancelled)
    f.org.revoke_funding(cancelled,f.now());f.resolve(cancelled)
    f.reject(lambda:f.org.execute(cancelled,f.now()),'funding_required')
    assert f.cash(16)==cash
    passed.append('post-consumption organization failure preserves debit until explicit revoke; refund once; late valid creation cannot commit after refund')
    # Persisted pending work survives the store object and a login replacement.
    pending=f.family(16,name='重登家族');f.fund(pending)
    old_epoch=f.epochs[16]
    f.epochs[16]=f.accounts.acquire_lease(1111,16)
    f.payments=OrganizationPayments(f.policy,f.rules)
    records=f.tx(16,lambda db:f.payments.pending(db,1111,16,f.epochs[16]))
    assert len(records)==1 and records[0].request_id==pending.request_id and type(records[0].args[-1]) is tuple
    f.reject(lambda:f.fund(pending),'epoch_mismatch')
    f.reject(lambda:f.org.revoke_funding(pending,f.now()),'stale_epoch')
    rebound=replace(pending,epoch=f.epochs[16],deadline_ms=f.now()+60_000)
    f.org.revoke_funding(rebound,f.now());assert f.resolve(rebound).status=='refunded'
    def old_callback():
        with closing(FencedConnection(f.accounts.connect(),16,old_epoch)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            return f.payments.resolve(db,1111,16,old_epoch,pending.request_id,f.now())
    try:old_callback()
    except StaleEpoch:pass
    else:raise AssertionError('Old role callback changed wallet')
    assert f.cash(16)==cash
    passed.append('restart/relogin enumerates old intent under new lease; stale funding/revoke/refund callbacks rejected')
    # Lost success reply must never be interpreted as a failed organization op.
    newer=f.family(name='后续意图');f.fund(newer)
    assert f.org.revoke_funding(create,f.now()).status=='committed'
    assert f.resolve(create).status=='committed'
    current=f.cash(1)
    assert next(x.balance for x in f.resolve(create).balances if x.currency=='cash')==current
    f.org.revoke_funding(newer,f.now());f.resolve(newer)
    passed.append('lost success reply resolves committed without refund; returned balances reflect newer debits')
    proof=f.family(16,name='凭据家族');start=f.cash(16);f.fund(proof)
    f.org.revoke_funding(proof,f.now())
    # Persistence fault injection, observed only through public resolve/wallet.
    # An organization cancellation alone is insufficient proof of a cash debit.
    with closing(f.accounts.connect()) as db,db:
        debit=db.execute('SELECT debit_id FROM organization_payments WHERE actor=? AND request_id=?',(16,proof.request_id)).fetchone()[0]
        original_debit=db.execute('SELECT * FROM role_wallet_receipts WHERE role_id=? AND settlement_id=?',(16,debit)).fetchone()
        db.execute('DELETE FROM role_wallet_receipts WHERE role_id=? AND settlement_id=?',(16,debit))
    f.reject(lambda:f.resolve(proof),'payment_debit_missing')
    assert f.cash(16)==start-fee
    with closing(f.accounts.connect()) as db,db:db.execute('INSERT INTO role_wallet_receipts VALUES(?,?,?,?)',original_debit)
    assert f.resolve(proof).status=='refunded' and f.cash(16)==start
    passed.append('missing original wallet debit proof refuses refund; restoring the authoritative receipt permits one recovery')
    limited=OrganizationPayments(dict(f.policy,payment_pending_limit=1),f.rules)
    first=f.family(16,name='限额家族');f.fund(first,limited)
    f.reject(lambda:f.fund(f.family(16,name='另一家族'),limited),'payment_pending_full')
    f.org.revoke_funding(first,f.now());f.resolve(first)
    passed.append('bounded pending-payment capacity rejects before another cash debit')
    uncertain=f.family(16,name='待核家族');f.fund(uncertain)
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE organization_funding SET consumed=1 WHERE actor=? AND request_id=?',(16,uncertain.request_id))
    before=f.cash(16)
    f.reject(lambda:f.resolve(uncertain),'payment_outcome_unknown')
    f.reject(lambda:f.org.revoke_funding(uncertain,f.now()),'funding_outcome_unknown')
    assert f.cash(16)==before
    # Restore only this deliberately corrupted fixture for cleanup.
    with closing(f.accounts.connect()) as db,db:
        db.execute('UPDATE organization_funding SET consumed=0 WHERE actor=? AND request_id=?',(16,uncertain.request_id))
    f.org.revoke_funding(uncertain,f.now());f.resolve(uncertain)
    passed.append('inconsistent consumed grant without success receipt remains pending for reconciliation, never auto-refunded')
    # Different workers race late commit against cancellation. SQLite's local
    # transactional grant is the final guard even before an owner sees a reply.
    for i in range(8):
        race=Fixture(Path(f.accounts.path).parent/f'race-{i}.db')
        command=race.family();start=race.cash(1);race.fund(command)
        barrier=threading.Barrier(2)
        def commit():
            barrier.wait(timeout=2)
            try:race.org.execute(command,race.now());return 'committed'
            except ValueError as error:assert str(error)=='funding_required';return 'revoked'
        def revoke():
            barrier.wait(timeout=2);return race.org.revoke_funding(command,race.now()).status
        with ThreadPoolExecutor(max_workers=2) as pool:
            a,b=pool.submit(commit),pool.submit(revoke)
            result,decision=a.result(),b.result()
        assert result==decision
        outcome=race.resolve(command)
        assert outcome.status==('committed' if result=='committed' else 'refunded')
        assert race.cash(1)==start-(race.policy['family_create_fee'] if result=='committed' else 0)
    passed.append('eight actual commit/revoke races yield either one paid operation or one refund, never both')
    # Guild level remains a progression fixture; the 3M debit is real ledger code.
    with closing(f.accounts.connect()) as db,db:db.execute('UPDATE organizations SET level=3 WHERE id=?',(family,))
    guild=f.cmd(1,family,'create_guild',('现金帮派','同心协力',create.args[2]))
    cash=f.cash(1);f.fund(guild)
    made=f.org.execute(guild,f.now());assert f.resolve(guild).status=='committed'
    assert f.cash(1)==cash-f.policy['guild_create_fee'] and f.org.snapshot(made['organization'])[0]['kind']=='guild'
    passed.append('family and guild creation use configured cash purposes; family notice is excluded from new cash funding')
    return family


async def owner_check(f,family,passed):
    io=BlockingIO();release=threading.Event();entered=threading.Event()
    payment=f.family(name='所有者家族')
    def blocked_fund():
        entered.set()
        if not release.wait(3):raise AssertionError('Missing fixture release')
        return f.fund(payment)
    async def handle_one(c):return await io.run(('role',1),blocked_fund)
    async def handle_other(c):return await io.run(('role',2),f.wallet,2)
    first,other=SerialOwner(('role',1),handle_one),SerialOwner(('role',2),handle_other)
    try:
        before_other=await io.run(('role',2),f.wallet,2)
        pending=asyncio.create_task(first.call('fund'))
        assert await asyncio.to_thread(entered.wait,1)
        assert await asyncio.wait_for(other.call('wallet'),.7)==before_other
        assert await asyncio.wait_for(io.run(('organization',family),f.org.snapshot,family),.7)
        assert not pending.done()
        release.set();assert (await pending).status=='funded'
        await io.run(OrganizationStore.owner_key(payment),f.org.revoke_funding,payment,f.now())
        assert (await io.run(('role',1),f.resolve,payment)).status=='refunded'
    finally:
        release.set();await first.close();await other.close();await io.close()
    passed.append('role-key bounded I/O and mailboxes: another role wallet and organization read progress during controlled funding pause')


async def runtime_owner_check(f,family,passed):
    from game_runtime import GameRuntime
    import runtime_storage
    for cancel_first in (False,True):
        fresh=Fixture(Path(f.accounts.path).parent/f'runtime-order-{cancel_first}.db')
        runtime=GameRuntime(fresh.accounts,runtime_storage.prepare(fresh.accounts))
        org=runtime.social_runtime.organizations
        release=threading.Event();entered=threading.Event()
        try:
            payment=fresh.family();before=fresh.cash(1);fresh.fund(payment)
            if cancel_first:
                assert (await org.command(payment,fresh.now(),revoke=True)).status=='revoked'
                try:await org.command(payment,fresh.now())
                except ValueError as error:assert str(error)=='funding_required'
                else:raise AssertionError('Late paid commit consumed a revoked grant')
                assert fresh.resolve(payment).status=='refunded' and fresh.cash(1)==before
            else:
                original=org.store.execute
                def slow(command,stamp):
                    entered.set()
                    if not release.wait(3):raise AssertionError('Missing organization release')
                    return original(command,stamp)
                with patch.object(org.store,'execute',slow):
                    abandoned=asyncio.create_task(org.command(payment,fresh.now()))
                    assert await asyncio.to_thread(entered.wait,1)
                    owner=org.owners[OrganizationStore.owner_key(payment)]['owner']
                    abandoned.cancel()
                    try:await abandoned
                    except asyncio.CancelledError:pass
                    revoke=asyncio.create_task(org.command(payment,fresh.now(),revoke=True))
                    for _ in range(3):await asyncio.sleep(0)
                    assert not revoke.done() and org.owners[OrganizationStore.owner_key(payment)]['owner'] is owner
                    release.set();assert (await revoke).status=='committed'
                assert fresh.resolve(payment).status=='committed' and fresh.cash(1)==before-fresh.policy['family_create_fee']
            assert not org.owners and not org.inflight
        finally:release.set();await runtime.close()
    passed.append('actual organization runtime serializes cancelled-wait commit before revoke; terminal revoke blocks late commit and permits one role cash refund')


def main():
    passed=[]
    with tempfile.TemporaryDirectory() as directory:
        fixture=Fixture(Path(directory)/'state.db')
        family=check(fixture,passed)
        asyncio.run(owner_check(fixture,family,passed))
        asyncio.run(runtime_owner_check(fixture,family,passed))
    result=dict(passed=passed,wallet_baselines='explicit disposable test fixtures only',family_level='level-3 fixture only',
        shared_native_runtime_integrated=False,native_gui_verified=False,live_store_changed=False,
        deployment='single-database SQLite Adapter; cross-database saga not implemented')
    write_json(OUT/'evidence/faction-payment-verification.json',result)
    print(json.dumps(result))


if __name__=='__main__':main()

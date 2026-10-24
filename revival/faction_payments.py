"""Role-owned organization payments joining the caller's fenced transaction.

No connection, commit, wallet initialization, network send or cross-role wallet
access. Organization owners exclusively consume/revoke grants; role owners
exclusively debit/refund cash and update their payment recovery records.
"""
from dataclasses import dataclass
import hashlib
import json
from types import MappingProxyType
from currency import CurrencyChange,apply_currency,read_wallet
from faction_domain import OrganizationStore,OrganizationCommand


@dataclass(frozen=True)
class PaymentReceipt:
    actor: int
    request_id: str
    fingerprint: str
    amount: int
    status: str
    # Always freshly read absolute balances, not historical debit/refund values.
    balances: tuple


@dataclass(frozen=True)
class PendingPayment:
    actor: int
    request_id: str
    fingerprint: str
    organization: int
    operation: str
    args: tuple
    amount: int


def immutable(value):
    if type(value) is tuple:return all(immutable(x) for x in value)
    return type(value) in (str,int)


def tuples(value):
    return tuple(tuples(x) for x in value) if isinstance(value,list) else value


def one(db,sql,args):
    # Join ordinary AccountStore transactions without changing their row factory.
    cursor=db.execute(sql,args)
    row=cursor.fetchone()
    return dict(zip((c[0] for c in cursor.description),row)) if row is not None else None


def prepare_payment_storage(db):
    """Startup migration, after OrganizationStore and currency schemas."""
    db.executescript('''CREATE TABLE IF NOT EXISTS organization_payments (
        actor INTEGER NOT NULL REFERENCES roles(id), request_id TEXT NOT NULL,
        fingerprint TEXT NOT NULL, organization INTEGER NOT NULL, operation TEXT NOT NULL,
        args TEXT NOT NULL, amount INTEGER NOT NULL CHECK(amount>0), purpose TEXT NOT NULL,
        currency_policy TEXT NOT NULL, debit_id TEXT NOT NULL, refund_id TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('funded','committed','refunded')),
        created_ms INTEGER NOT NULL, updated_ms INTEGER NOT NULL,
        PRIMARY KEY(actor,request_id));
        CREATE INDEX IF NOT EXISTS organization_payment_pending ON organization_payments(actor,status,created_ms);''')


class OrganizationPayments:
    def __init__(self,policy,currency_rules):
        self.policy,self.rules=MappingProxyType(dict(policy)),currency_rules

    def _identity(self,command,role_id,epoch):
        if not isinstance(command,OrganizationCommand) or command.actor!=role_id or str(command.epoch)!=str(epoch):
            raise ValueError('payment_actor_or_epoch_mismatch')
        if type(command.request_id) is not str or not 1<=len(command.request_id)<=160 or not immutable(command.args):
            raise ValueError('invalid_payment_intent')

    def _quote(self,db,command):
        if command.operation=='create_family' and command.organization==0:
            field,purpose='family_create_fee','family_create'
        elif command.operation=='create_guild' and command.organization>0:
            field,purpose='guild_create_fee','guild_create'
        elif command.operation=='change_aim':
            row=one(db,'SELECT kind FROM organizations WHERE id=?',(command.organization,))
            if not row:raise ValueError('organization_missing')
            raise ValueError(row['kind']+'_aim_uses_organization_funds')
        else:raise ValueError('operation_has_no_organization_fee')
        amount=self.policy[field]
        if type(amount) is not int or not 0<amount<2**63:raise ValueError('invalid_organization_fee')
        return amount,purpose

    def _receipt(self,db,account_id,role_id,epoch,row):
        return PaymentReceipt(role_id,row['request_id'],row['fingerprint'],row['amount'],row['status'],
                              read_wallet(db,account_id,role_id,epoch,self.rules))

    def fund(self,db,account_id,role_id,epoch,command,now_ms):
        """Debit cash + immutable grant + recovery intent in one owner tx.

        The caller already began its current role lease transaction and must
        roll it back on any error. Retrying a cancelled intent cannot recharge.
        No wire-provided amount or wallet type is accepted.
        """
        self._identity(command,role_id,epoch)
        read_wallet(db,account_id,role_id,epoch,self.rules)
        if now_ms>command.deadline_ms:raise ValueError('payment_deadline')
        fingerprint=OrganizationStore.fingerprint(command)
        old=one(db,'SELECT * FROM organization_payments WHERE actor=? AND request_id=?',(role_id,command.request_id))
        if old and command.operation=='change_aim':
            # Recover prior code's cash debit without permitting any new one.
            # resolve still verifies the original wallet debit/grant/receipt.
            if (old['fingerprint'],old['purpose'],old['currency_policy'])!=(fingerprint,'family_aim_update',self.rules.revision):
                raise ValueError('payment_intent_conflict')
            return self.resolve(db,account_id,role_id,epoch,command.request_id,now_ms)
        amount,purpose=self._quote(db,command)
        if old:
            if (old['fingerprint'],old['amount'],old['purpose'],old['currency_policy'])!=(fingerprint,amount,purpose,self.rules.revision):
                raise ValueError('payment_intent_conflict')
            return self.resolve(db,account_id,role_id,epoch,command.request_id,now_ms)
        # Legacy fixture grants are not proof a real wallet was debited.
        if db.execute('SELECT 1 FROM organization_funding WHERE actor=? AND request_id=?',(role_id,command.request_id)).fetchone():
            raise ValueError('existing_grant_has_no_wallet_intent')
        if db.execute('SELECT COUNT(*) FROM organization_payments WHERE actor=? AND status=?',(role_id,'funded')).fetchone()[0]>=self.policy['payment_pending_limit']:
            raise ValueError('payment_pending_full')
        key=hashlib.sha256(json.dumps([role_id,command.request_id],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        debit,refund='organization:debit:'+key,'organization:refund:'+key
        apply_currency(db,account_id,role_id,epoch,CurrencyChange(debit,purpose,'organization-intent:'+fingerprint,(('cash',-amount),)),self.rules)
        OrganizationStore.record_funding(db,command,amount)
        db.execute('INSERT INTO organization_payments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (role_id,command.request_id,fingerprint,command.organization,command.operation,json.dumps(command.args,ensure_ascii=False),
             amount,purpose,self.rules.revision,debit,refund,'funded',now_ms,now_ms))
        row=one(db,'SELECT * FROM organization_payments WHERE actor=? AND request_id=?',(role_id,command.request_id))
        return self._receipt(db,account_id,role_id,epoch,row)

    def resolve(self,db,account_id,role_id,epoch,request_id,now_ms):
        """Recover committed creation or refund an organization-revoked grant.

        A lost reply, exception or timeout alone never authorizes a refund.
        The role reads the durable organization decision in its transaction.
        A replacement login may resolve its own old payment under the new lease.
        """
        read_wallet(db,account_id,role_id,epoch,self.rules)
        row=one(db,'SELECT * FROM organization_payments WHERE actor=? AND request_id=?',(role_id,request_id))
        if not row:raise ValueError('payment_missing')
        if row['currency_policy']!=self.rules.revision:raise ValueError('payment_currency_migration_required')
        if not db.execute('SELECT 1 FROM role_wallet_receipts WHERE role_id=? AND settlement_id=?',
                          (role_id,row['debit_id'])).fetchone():raise ValueError('payment_debit_missing')
        grant=one(db,'SELECT fingerprint,amount,consumed FROM organization_funding WHERE actor=? AND request_id=?',(role_id,request_id))
        if not grant or (grant['fingerprint'],grant['amount'])!=(row['fingerprint'],row['amount']):raise ValueError('payment_grant_inconsistent')
        receipt=db.execute('SELECT fingerprint FROM organization_receipts WHERE actor=? AND request_id=?',(role_id,request_id)).fetchone()
        if receipt:
            if receipt[0]!=row['fingerprint'] or grant['consumed']!=1 or row['status']=='refunded':raise ValueError('payment_receipt_inconsistent')
            status='committed'
        elif grant['consumed']==-1:
            if row['status']=='committed':raise ValueError('committed_payment_revoked')
            if row['status']!='refunded':
                apply_currency(db,account_id,role_id,epoch,
                    CurrencyChange(row['refund_id'],'organization_refund','organization-intent:'+row['fingerprint'],(('cash',row['amount']),)),self.rules)
            status='refunded'
        elif grant['consumed']==0 and row['status']=='funded':
            status='funded'  # No outcome yet; keep pending, never invent a refund.
        else:raise ValueError('payment_outcome_unknown')
        db.execute('UPDATE organization_payments SET status=?,updated_ms=? WHERE actor=? AND request_id=?',
                   (status,now_ms,role_id,request_id))
        current=one(db,'SELECT * FROM organization_payments WHERE actor=? AND request_id=?',(role_id,request_id))
        return self._receipt(db,account_id,role_id,epoch,current)

    def pending(self,db,account_id,role_id,epoch,limit=64):
        read_wallet(db,account_id,role_id,epoch,self.rules)
        if type(limit) is not int or not 1<=limit<=128:raise ValueError('payment_recovery_batch_limit')
        return tuple(PendingPayment(r[0],r[1],r[2],r[3],r[4],tuples(json.loads(r[5])),r[6])
          for r in db.execute('SELECT actor,request_id,fingerprint,organization,operation,args,amount FROM organization_payments WHERE actor=? AND status=? ORDER BY created_ms,request_id LIMIT ?',
                              (role_id,'funded',limit)))

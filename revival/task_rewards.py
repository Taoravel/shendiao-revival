"""Pure reward plans and a transaction-joining, per-channel settlement Adapter.

Unknown channels stay pending while verified channels settle once. Dependencies
join the same role transaction; no network sends, connection creation or commits.
"""
from dataclasses import dataclass
import hashlib
import json
from inventory import AssetChange
from progression import credit_experience, read_experience
from currency import task_currency_channels,apply_currency,read_wallet,CurrencyChange,WalletNotInitialized
from task_pet_experience import prepare_task_pet_experience_storage, settle_pet_experience
from task_growth_resources import synchronize_task_inventory_source


@dataclass(frozen=True)
class TaskRewardPlan:
    role_id: int
    task_id: int
    fingerprint: str
    experience: int
    grants: tuple
    pending: tuple
    item_fingerprint: str = ''


@dataclass(frozen=True)
class TaskRewardReceipt:
    role_id: int
    task_id: int
    experience_awarded: int
    items_awarded: tuple
    pending: tuple
    rewards_complete: bool
    experience_balance: int
    level: int
    currency_awarded: tuple = ()  # (original field, canonical currency, original amount)
    wallet: tuple | None = None   # current balances; historical receipt is not a cache snapshot
    pet_experience: object = None


def prepare_reward_storage(db):
    """Startup-only schema migration; caller owns the connection."""
    db.executescript('''CREATE TABLE IF NOT EXISTS task_reward_channels (
        role_id INTEGER NOT NULL REFERENCES roles(id), task_id INTEGER NOT NULL,
        channel TEXT NOT NULL, fingerprint TEXT NOT NULL, receipt TEXT NOT NULL,
        PRIMARY KEY(role_id,task_id,channel));''')
    prepare_task_pet_experience_storage(db)


def update_reward_delivery(effect):
    """Recompute mixed reward/continuation outbox status without losing raw data."""
    fields = effect.get('continuation_fields', {})
    resolved=set(effect.get('continuation_resolved_fields',()))
    other_pending = (bool(effect.get('next_ids')) and not effect.get('chain_resolved',False)) or any(
        bool(value) if isinstance(value, (list, tuple)) else str(value) not in ('0', '', 'None')
        for key,value in fields.items() if key not in resolved)
    effect['followups_pending'] = other_pending
    return effect.get('reward_status') == 'settled' and not other_pending


def plan_task_reward(role_id, task_id, effect, resources, item_catalog):
    """Pure planning against immutable startup configs; no design reward override.

    Existing explicit zero rewards stay zero. Confirmed 0/1 binding flags are
    forwarded to Inventory's per-instance binding interface. Missing or unknown
    flags keep the item channel pending rather than changing its meaning.
    """
    definition = resources.definitions.get(task_id)
    if definition is None or effect.get('task_id') != task_id:
        raise ValueError('Task reward definition mismatch')
    rewards = effect.get('display_rewards')
    items = effect.get('display_items')
    expected_items = [dict(x) for x in definition['display_items']]
    if rewards != dict(definition['display_rewards']) or items != expected_items:
        raise ValueError('Task reward differs from source configuration')
    if any(type(v) is not int or v < 0 for v in rewards.values()):
        raise ValueError('Invalid task reward amount')
    canonical = json.dumps([task_id, rewards, items], sort_keys=True, separators=(',', ':'))
    fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
    pending = [(key, value, 'recipient_or_currency_mapping_unconfirmed')
               for key, value in sorted(rewards.items()) if key != 'ExpReward' and value]
    grants, item_problem = [], False
    raw_selectors=tuple(int(x) for x in definition.get('lists',{}).get('RewardItemShapeIDList',()))
    selected_indices=tuple(range(len(items)))
    selector_problem=None
    role_config=effect.get('reward_role_config_id')
    if raw_selectors:
        frozen=effect.get('reward_item_selectors')
        if frozen is None:
            selector_problem='explicit_role_reward_reconciliation'
        elif tuple(frozen)!=raw_selectors:
            raise ValueError('Task item selector differs from source configuration')
        elif type(role_config) is not int or not 1<=role_config<=10:
            selector_problem='role_reward_selector_not_resolved'
        else:
            # Original17c5950: missing/<=0/>10 selectors are unconditional,
            # including the common item after ten character-specific rows.
            selected_indices=tuple(i for i in range(len(items)) if i>=len(raw_selectors)
                or not 1<=raw_selectors[i]<=10 or raw_selectors[i]==role_config)
    item_fingerprint=fingerprint
    if raw_selectors:
        item_fingerprint=hashlib.sha256(json.dumps([fingerprint,'native_character_reward_v1',
            raw_selectors,role_config,selected_indices],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    for index in selected_indices:
        item=items[index]
        ident, count, bind = item['id'], item['count'], item['bind']
        if (type(ident) is not int or ident not in item_catalog or type(count) is not int or count <= 0
                or type(bind) is not int or bind not in (0, 1)):
            item_problem = True
        else:
            grants.append((ident, count, bind))
    if item_problem:
        pending.append(('items', len(items), 'item_id_quantity_or_binding_not_supported'))
        grants = []
    if selector_problem:
        pending.append(('items',len(items),selector_problem))
        grants = []
    return TaskRewardPlan(role_id, task_id, fingerprint, rewards['ExpReward'], tuple(grants), tuple(pending),item_fingerprint)


def settle_task_reward(db, account_id, role_id, login_epoch, task_id, resources, inventory, growth_rules=None, attribute_rules=None, currency_rules=None, pet_experience_rules=None,*,resource_rules=None,equipment_rules=None):
    """Join one owner transaction for EXP, inventory, channel receipts and effect.

    Any exception requires caller rollback. The lease is checked inside this
    transaction; caller schedules via bounded role/persistence resources. Retry
    checks durable per-channel receipts even if unresolved channels remain.
    """
    if not db.in_transaction:
        raise ValueError('Task reward requires an owner transaction')
    if inventory.account_id != account_id or inventory.role_id != role_id:
        raise ValueError('Task inventory owner mismatch')
    if not db.execute('SELECT 1 FROM roles WHERE id=? AND account_id=?', (role_id, account_id)).fetchone():
        raise ValueError('Task reward role ownership mismatch')
    lease = db.execute('SELECT 1 FROM role_leases WHERE role_id=? AND epoch=? AND active=1',
                       (role_id, login_epoch)).fetchone()
    if not lease:
        raise ValueError('Stale task reward lease')
    if not db.execute("SELECT 1 FROM task_journal WHERE role_id=? AND task_id=? AND state='completed'",
                      (role_id, task_id)).fetchone():
        raise ValueError('Task is not completed')
    row = db.execute('SELECT payload,delivered FROM task_effects WHERE role_id=? AND task_id=?', (role_id, task_id)).fetchone()
    if row is None:
        raise ValueError('Task reward effect missing')
    effect = json.loads(row[0])
    plan = plan_task_reward(role_id, task_id, effect, resources, inventory.items)

    def channel(name, apply, fingerprint=None):
        fingerprint=plan.fingerprint if fingerprint is None else fingerprint
        old = db.execute('SELECT fingerprint,receipt FROM task_reward_channels WHERE role_id=? AND task_id=? AND channel=?',
                         (role_id, task_id, name)).fetchone()
        if old:
            if old[0] != fingerprint:
                raise ValueError('Task reward source changed after settlement')
            return json.loads(old[1])
        result = apply()
        db.execute('INSERT INTO task_reward_channels VALUES(?,?,?,?,?)',
                   (role_id, task_id, name, fingerprint, json.dumps(result)))
        return result

    wallet=None
    if currency_rules is not None:
        if any(field not in ('MoneyReward','SMoney') for field in currency_rules.task_fields):
            raise ValueError('Unsupported task currency mapping')
        schema=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='role_wallet_profiles'").fetchone()
        if schema:
            try: wallet=read_wallet(db,account_id,role_id,login_epoch,currency_rules)
            except WalletNotInitialized: pass

    # A delivered legacy effect without our receipt may already have been paid
    # elsewhere. Fail closed rather than credit it a second time.
    known = db.execute('SELECT 1 FROM task_reward_channels WHERE role_id=? AND task_id=?', (role_id, task_id)).fetchone()
    if row[1] and not known:
        raise ValueError('Legacy delivery requires reconciliation')
    # Recipient was captured by the workflow before character EXP. An old
    # completed task without a decision stays pending; never select here.
    pet = settle_pet_experience(db,account_id,role_id,login_epoch,task_id,
        effect['display_rewards']['PetExpReward'],plan.fingerprint,inventory,pet_experience_rules)
    # This runs even if character_exp is already paid: a newly eligible pending
    # pet channel can still have advanced the inventory revision this time.
    resource_context=synchronize_task_inventory_source(db,account_id,role_id,login_epoch,task_id,inventory,
        resource_rules,equipment_rules,phase='before-exp')
    def exp():
        balance = credit_experience(db, account_id, role_id, plan.experience, growth_rules,attribute_rules,login_epoch,
                                    resource_context=resource_context)
        return {'awarded': plan.experience, 'balance_after': balance.experience}
    exp_receipt = channel('character_exp', exp)
    items = ()
    if not any(entry[0] == 'items' for entry in plan.pending):
        def grant_items():
            inventory.apply_settlement(db, AssetChange(f'task:{role_id}:{task_id}:items', plan.grants))
            return {'grants': plan.grants}
        item_receipt = channel('items', grant_items, plan.item_fingerprint)
        items = tuple(tuple(x) for x in item_receipt['grants'])

    synchronize_task_inventory_source(db,account_id,role_id,login_epoch,task_id,inventory,
        resource_rules,equipment_rules,phase='after-items')

    paid_currency=[]
    currency_rows=task_currency_channels(effect['display_rewards'],currency_rules) if currency_rules is not None else ()
    mapped={field:(name,amount) for field,name,amount in currency_rows}
    for field in ('MoneyReward','SMoney'):
        amount=effect['display_rewards'].get(field,0)
        if not amount: continue
        old=db.execute('SELECT fingerprint,receipt FROM task_reward_channels WHERE role_id=? AND task_id=? AND channel=?',
                       (role_id,task_id,'currency:'+field)).fetchone()
        if old:
            if old[0]!=plan.fingerprint: raise ValueError('Task reward source changed after settlement')
            receipt=json.loads(old[1])
            if receipt.get('field')!=field or receipt.get('amount')!=amount:
                raise ValueError('Invalid historical task currency receipt')
            if currency_rules is not None and (field not in mapped or receipt.get('policy')!=currency_rules.revision
                    or receipt.get('currency')!=mapped[field][0]):
                raise ValueError('Task currency receipt migration required')
            paid_currency.append((field,receipt['currency'],amount))
        elif wallet is not None and field in mapped:
            name,amount=mapped[field]
            def pay(field=field,name=name,amount=amount):
                change=CurrencyChange(f'task:{role_id}:{task_id}:currency:{field}',
                    'task_reward',f'task:{task_id}:{field}',((name,amount),))
                apply_currency(db,account_id,role_id,login_epoch,change,currency_rules)
                return {'field':field,'currency':name,'amount':amount,'policy':currency_rules.revision,
                        'source_ref':change.source_ref,'settlement_id':change.settlement_id}
            receipt=channel('currency:'+field,pay)
            paid_currency.append((field,receipt['currency'],amount))
    paid_fields={field for field,_,_ in paid_currency}
    pending=tuple(entry for entry in plan.pending if entry[0] not in paid_fields)
    pending=tuple((field,amount,pet.reason) if field=='PetExpReward' else (field,amount,reason)
                  for field,amount,reason in pending if field!='PetExpReward' or pet.status=='pending')
    if currency_rules is not None and wallet is None:
        pending=tuple((field,amount,'wallet_not_initialized') if field in mapped else (field,amount,reason)
                      for field,amount,reason in pending)
    if wallet is not None:
        wallet=read_wallet(db,account_id,role_id,login_epoch,currency_rules)
    complete = not pending
    effect['reward_status'] = 'settled' if complete else 'partially_settled'
    effect['reward_pending'] = pending
    # The older outbox also carries successor/scene/dialogue instructions. Reward
    # success alone must not hide those instructions from its consumer.
    delivered = update_reward_delivery(effect)
    db.execute('UPDATE task_effects SET payload=?,delivered=? WHERE role_id=? AND task_id=?',
               (json.dumps(effect, ensure_ascii=False), int(delivered), role_id, task_id))
    balance = read_experience(db, account_id, role_id)
    return TaskRewardReceipt(role_id, task_id, exp_receipt['awarded'], items, pending, complete,
                             balance.experience,balance.level,tuple(paid_currency),wallet,pet)

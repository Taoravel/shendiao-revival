"""Original role-conditional task rewards must not grant every variant."""
import json
from inspect_client import OUT
from tasks import TaskResources,_freeze,_plain
from task_rewards import plan_task_reward
from contextlib import closing
from pathlib import Path
import tempfile
from accounts import AccountStore
from inventory import Inventory
from tasks import prepare_task_store
from task_rewards import prepare_reward_storage,settle_task_reward


def main():
    doc=json.loads((OUT/'catalogs/tasks.json').read_text(encoding='utf-8'))
    definitions={x['id']:x for x in doc['missions']}
    resources=TaskResources(_freeze(definitions),_freeze({}))
    catalog={int(x['attributes']['id']):x['attributes'] for x in json.loads(
        (OUT/'catalogs/knight.gsp.item.citemattr.json').read_text(encoding='utf-8'))}
    definition=definitions[220902]
    effect={'task_id':220902,'display_rewards':definition['display_rewards'],
            'display_items':definition['display_items']}
    plan=plan_task_reward(1,220902,effect,resources,catalog)
    assert (any(x[0]=='items' for x in plan.pending) or len(plan.grants)<len(definition['display_items'])), \
        f'Conditional rewards ignored: all {len(plan.grants)} configured rows granted without a role selector'
    examples={(220902,1):((36671,1,1),(32029,1,1)),(220902,10):((36670,1,1),(32029,1,1)),
              (221002,1):((36735,1,1),(31253,1,1)),(221002,10):((36739,1,1),(31253,1,1))}
    for (task_id,role_config),expected in examples.items():
        task=definitions[task_id]
        effect=dict(task_id=task_id,display_rewards=task['display_rewards'],display_items=task['display_items'],
            reward_item_selectors=list(map(int,task['lists']['RewardItemShapeIDList'])),reward_role_config_id=role_config)
        selected=plan_task_reward(1,task_id,effect,resources,catalog)
        assert selected.grants==expected
    with tempfile.TemporaryDirectory() as directory:
        accounts=AccountStore(Path(directory)/'variants.sqlite3')
        prepared=prepare_task_store(accounts)
        inv_config=Inventory.prepare(accounts)
        role=accounts.create_role(1111,'奖励形象固定',11,1010109)
        epoch=accounts.acquire_lease(1111,role['id'])
        inv=Inventory(accounts,1111,role['id'],inv_config)
        with closing(accounts.connect()) as db:
            prepare_reward_storage(db)
        task=definitions[221002]
        effect=dict(task_id=221002,display_rewards=task['display_rewards'],display_items=task['display_items'],
            reward_item_selectors=list(map(int,task['lists']['RewardItemShapeIDList'])),reward_role_config_id=1)
        with closing(accounts.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute("INSERT INTO task_journal VALUES(?,221002,'completed')",(role['id'],))
            db.execute('INSERT INTO task_effects(role_id,task_id,payload) VALUES(?,221002,?)',(role['id'],json.dumps(effect)))
            first=settle_task_reward(db,1111,role['id'],epoch,221002,prepared,inv)
            assert first.items_awarded==examples[(221002,1)]  # current shape9 must not replace frozen1
            again=settle_task_reward(db,1111,role['id'],epoch,221002,prepared,inv)
            assert again.items_awarded==first.items_awarded
            actual=tuple(db.execute('SELECT template_id,quantity,binding FROM inventory_items WHERE role_id=? ORDER BY slot',(role['id'],)))
            assert actual==first.items_awarded
    report=dict(passed=['original220902/221002 select correct role1/10 variant plus common tail',
        'legacy selector-less completed reward remains reconciliation, never grants all variants',
        'frozen role1 selection survives current shape9; bound items awarded once and replay returns same rows'],
        source='client_verified filter; freezing time is designed',live_client_tested=False)
    (OUT/'evidence/task-reward-variants-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    main()

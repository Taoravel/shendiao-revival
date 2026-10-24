# 任务奖励接入唯一人物资源

2026-10-23。按ARCHITECTURE、DESIGN_AUTHORITY、ROLE_RESOURCE_STORAGE_INTEGRATION、ROLE_RESOURCE_EQUIPMENT_SEAM_AUDIT以及本窗口 [TASK_GROWTH_RESOURCE_SEAM_AUDIT.md](TASK_GROWTH_RESOURCE_SEAM_AUDIT.md)实施。根窗口已实际提供GrowthResourceContext与裸身-only成长写；本窗口仅修改所属progression/task_rewards/task_workflow及独立任务Adapter，没有改root属性/装备/资源/role_growth/role_growth_actions或共享入口，没有自动迁移角色。

## 当前Interface

`progression.credit_experience(..., *, resource_context=None)`显式透传根窗口 `GrowthResourceContext(inventory_snapshot,equipment_rules,resource_rules)`到auto_credit_profile。已有角色已经迁移而调用方漏传时，原migrated围栏继续拒绝，不能捕获异常后退回经验银行。

下列任务入口新增keyword `resource_rules=None,equipment_rules=None`，两者须同时提供；Inventory仍用已有实际参数：

- `task_workflow.complete_task_transaction`、`replay_completed_task_transaction`、`replay_item_completion_transaction`。
- `task_rewards.settle_task_reward`。
- `task_item_transactions.submit_item_task_transaction`、`task_quiz.answer_task_quiz_transaction`、`task_cart_transfer.complete_cart_transfer_transaction`。
- `task_region.complete_region_transaction`、`acknowledge_region_transaction`。
- `task_newbie_chapter.finish_newbie_chapter`、`task_master_card.choose_master_card`、`reconcile_master_equipment`。

规则启动时由所属初始化加载冻结`load_resource_rules()`及现有EquipmentAttributeRules，调用方在同一角色租约事务注入：

```python
completion = complete_task_transaction(
    db, actor, plan, request_id, resources, inventory,
    growth_rules, attribute_rules, currency_rules, pet_experience_rules,
    resource_rules=prepared_resource_rules,
    equipment_rules=prepared_equipment_rules)
```

未迁移角色保持原合约；提供新规则也不初始化metadata或治疗。缺少schema、已知资源/装备来源、政策不匹配或当前source错误时明确失败，不能用登录/读取来补迁移。共享Adapter还需同步采用根窗口当前resource profile读取，避免重新用旧read_attribute_snapshot覆盖本结果。

## 同一事务的实际顺序

`task_growth_resources.py`只组合公开资源Interface，不复制SQL或公式：

1. TaskWorkflow在apply_task_plan、交物或宠奖励之前，通过 `current_task_resource_profile`验证已迁移角色的当前完整来源。旧profile返回None后走现有旧合约；仅ResourceNotInitialized被视为未转交，其他异常不能吞掉。
2. 保留原固定任务宠接收者、任务完成、objective_items扣物和settle_pet_experience顺序。宠XP通过实际Inventory.change_pet_growth也推进inventory revision；不能只考虑交物。
3. 在character_exp渠道前无条件调用 `synchronize_task_inventory_source(...,phase='before-exp')`：读唯一资源before、当前真实库存→current_equipment_totals→resource_caps_from_projection；确有来源差异才以inventory_change计划/CAS落盘。此原因严格保持数值caps、成长与其他政策不变，只更新携带资产来源，HP/MP及resource version不变。即使人物EXP渠道已付、仅此次补发宠XP，此同步仍执行。
4. 以刚取得的当前InventorySnapshot构造GrowthResourceContext，只在未付EXP渠道调用credit_experience；根窗口在同一库存revision内写裸身/ordinary_growth资源过渡。没有拿任务入口旧库存快照贯穿这一步。
5. 原items渠道发物/宠之后，再执行phase='after-items'的source-only同步。货币不变成资产revision；所有渠道及资源凭据仍在外层同一事务。
6. TaskWorkflow从当前真实库存和唯一资源读取current_resource_profile，并在内层growth_refresh直接编码一份最终装备/资源快照；不再先对已迁移角色尝试裸身+总资源混合编码。TaskCompletion.attributes可直接为根窗口EquipmentRoleSnapshot。

source-only收据身份由taskID、阶段和实际前后inventory revision组成。来源已精确当前时仅读返回，不按后来HP生成一份新transition复用旧键。已付任务重试继续读当前成长/资源/资产，不重做ordinary_growth、不治疗、不重置后继；只有真实仍pending的奖励渠道实际新写资产时才同步新来源。

所有原生结果仍须提交前编码，任一步失败整笔回滚；成功后才发布缓存和发送。任务源ID/receipt不替代世界、战斗或连接所有者事实。会改变装备caps的操作须先由所属穿脱/耐久/修理原因结算，不能借本source-only阶段抹平成普通成长。

## 开场、选择卡与装备任务的精确接线

开场`finish_newbie_chapter`的鲜完成和已付确认都透传同一对规则。创建唯一carrier/basis、显式迁移profile及新建开关仍由主集成统一控制，此函数不创建资源来源。

`choose_master_card(..., *, generation, now_ms, growth_rules=None, attribute_rules=None, currency_rules=None, pet_experience_rules=None, resource_rules=None, equipment_rules=None)`先严格读当前来源，原获准选择发一件绑定武器后，按`phase='master-card'`同步inventory_change，再进入TaskWorkflow。已付卡凭据分支仅核对当前来源、读背包/任务显示，不调用source同步，不再发物。即使后来已装备、升级或受损，也不回放旧资源。

穿装备的主集成按下列顺序加入**同一调用方事务**：

1. 读当前唯一资源before，调用公开`Inventory.equip_transaction(db,item_key,slot,epoch,request_id)`取得实际EquipmentEvent。
2. 用实际新InventorySnapshot计算`current_equipment_totals`和`resource_caps_from_projection`，按`plan_resource_caps(before,caps,'equip',resource_rules)`并`apply_resource_transition`落盘。资源键由装备命令所有者管理；已付装备重试按其持久凭据只读当前状态。
3. 调用独立`reconcile_master_equipment(db,account_id,role_id,epoch,resources,master_card_rules,inventory,*,event=None,growth_rules=None,attribute_rules=None,currency_rules=None,pet_experience_rules=None,resource_rules=None,equipment_rules=None)`。该函数严格读当前profile、验证实际所领实例slot0、完成type59并接车夫；不穿装备、不补equipment/source transition。可信重登恢复可以省略event，仍要求当前来源已收敛。
4. 装备/任务消息及最终完整属性编码成功后提交，提交后才发送。

`equip_master_transaction(..., **reward_rules)`保留为旧资源合约的组合包装。已迁移profile显式带新规则调用时在穿装备之前拒绝；新集成使用上面可独立reconcile的Interface，避免隐式二次equipment transition。

## 实际检查与当前依赖状态

[task-resource-jiaxing-chain-check.json](task-resource-jiaxing-chain-check.json)当前通过：明确已知70/40夹具在intro前显式转交资源合约→原intro→师父卡发物/source-only→公开equip/显式equip资源过渡/独立type59 reconcile→车夫/公开世界同事务→嘉兴，实际激活原后继，无测试offer或XP注入目标。原120XP经TaskWorkflow自然得到L2/31/free5、80/110HP、46/106MP/version1与49/38/8；内层唯一完整map/RoleDetail一致，重试资源不变且不重复60001/state1，已付卡在装备/升级后只读不写。新增卡片晚期背包编码失败、装备资源/type59后提交前失败均全库回滚，相同身份随后重试成功；旧equip包装及未先结算equip资源的独立reconcile在写入前拒绝。该检查覆盖任务领域消费者的全前置链；NPC位置是可信领域夹具，非自然导航/连续连接/GUI验收。

`verify_task_resource_growth.py`当前复查已通过原102108交50056、实际宠5000XP、人物10000XP及三件原绑定50057同事务，source前/后两阶段和HP70/MP40保持、晚期背包失败全库回滚、旧/半注入规则及旧epoch拒绝、后来60/30不被重放覆盖。新增原102313“人物EXP/items已付、本次补发pending宠7000XP”也已通过：原宠接收者固定，人物累计20500XP不重付、无重复成长，source再次收敛且不治疗。当前完整结果见 [task-resource-growth-check.json](task-resource-growth-check.json)。

此前血脉迁移期间，按diagnosing-bugs缩至**无任务逻辑的最小公开零EXP调用**，定位Inventory/change_pet/load_pet漏传已知blood规则，见 [task-pet-growth-contract-check.json](task-pet-growth-contract-check.json)的历史红记录。库存所属窗口已补齐真实公开Interface，本窗口重新运行原复合检查全部通过，当前无此依赖阻塞；未补血脉默认值、删除已知来源或修改其源码。

必要旧路径兼容已通过普通TaskWorkflow、固定Quiz、交物、158静态区域、10车夫路线、43开场路线和86师父武器选择。新增资源接线的全前置领域链和复合宠XP检查如上；当前源状态与最终结果以相应report为准。

## 接入限制与后续消费者

2026-10-24补充：`task_battle.settle_task_battle_transaction`与`acknowledge_task_battle_transaction`已新增成对`resource_rules/equipment_rules`并透传共同完成/恢复；不会结算战斗自身HP/MP，也不改变默认关闭的正式PVE能力。梦醒第一族在显式已知唯一资源profile下，经人工Participant/BattleFinished契约的真实admit/settle及125/0返回路径通过；旧战斗绑定六组契约检查回归通过。实际AI与敌方数值未执行；当前精确梦醒候选见`task-dream-return-settlement-delivery.json`。主集成仍须将参数注入共享消费者，按上述独立装备阶段组合；新profile从创建一路覆盖消费者的开关由主集成统一启用，不由本窗口自动激活。领域链通过不能当作共享Runtime、自然导航或客户端已验收。

research/codebase-design先沿真实目标扣物、宠XP、人物XP、items顺序审计，使用根公开Module隐藏来源/CAS/成长算法，并把独立type59 reconcile保留在已完成equipment资源过渡后的Seam；diagnosing-bugs以现有复合反馈缩成零EXP公开调用，区分依赖接线和任务逻辑，并在所属窗口修复后重跑原反馈；writing-for-agents将真实签名、阶段、检查与未完成消费者共置。产物为所属共同消费者、task_growth_resources、任务Adapter参数透传、复合检查/全前置嘉兴领域链与本文。17个本批源码AST解析及交接本地链接检查通过。未做全面回归、部署、GUI/真人角色、实际战斗或商业并发验收。

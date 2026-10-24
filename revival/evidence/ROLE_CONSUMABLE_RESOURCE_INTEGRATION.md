# 人物药品接入唯一资源记录

2026-10-23，资产窗口。新资源药品消费者已离线实现并验证，尚未在共享运行时启用新profile或做GUI验收。接迁移后的CUseItem、任务事务内用药或药品构造参数时读本文；权威资源规则、迁移与完整before CAS分别见ROLE_RESOURCE_TRANSITION_DECISION、ROLE_RESOURCE_STORAGE_INTEGRATION。当前六槽开放范围由根维护，本批沿原10师承武器白名单。

## 调用与完成条件

启动由根加载冻结resource_rules和equipment_attribute_rules，显式选择以下一种接入方式。Inventory不从accounts自动激活新资源规则、不在药品热路径加载配置、不创建或迁移角色profile。

构造注入，之后原Owner用药路由参数保持不变：

```python
inventory = Inventory(leased_accounts, account_id, role_id, inventory_config,
    resource_rules=resource_rules,
    equipment_attribute_rules=equipment_attribute_rules)
replies = await owner.io(inventory.receive_role_consumable,
    body, epoch, command.request_id)
```

或保留原Inventory构造，在专用原生Adapter末尾位置传入两份启动规则，适配Owner.io只接*args：

```python
replies = await owner.io(inventory.receive_role_consumable,
    body, epoch, command.request_id, resource_rules, equipment_attribute_rules)
```

Adapter仍接受原16字节BE32物品实例key、BE32目标种类0、BE64当前角色ID；角色Owner继续检查joined、非战斗/传送和受理命令身份。同一次受理请求ID保持稳定，新的相同点击是新命令。完成条件是角色已有可信显式迁移，且药品和所有其他消费者、load均已采用新contract后，根再启用迁移开关。调用本Adapter不完成这项开关或全链路验收。

外层已有角色事务可调用：

```python
receipt = inventory.use_role_consumable(db, item_key, epoch, request_id,
    resource_rules=resource_rules, equipment_rules=equipment_attribute_rules)
# 在同一事务取得当前资产，编码最终profile及自己的common receipt。
assets = inventory.immutable_snapshot_transaction(db, epoch=epoch)
profile = current_resource_profile(db, account_id, role_id, epoch, assets,
    resource_rules=resource_rules, equipment_rules=equipment_attribute_rules)
```

构造参数名equipment_attribute_rules和use方法参数名equipment_rules有意区分Inventory已有普通装备原表equipment_rules字段。两份新规则成对提供；单份或错误类型拒绝。调用方已有事务负责统一回滚异常、写共同凭据并提交，本方法不另开连接/提交/发送。

## 原子性与重试语义

已显式迁移时：read_role_resources读取唯一已知before → 用真实携带物品/实例品质计算效果并扣1 → 同事务资产快照 → current_equipment_totals → resource_caps_from_projection → plan_resource_values(before,...,'medicine',current_caps=当前caps) → apply_resource_transition → 原有inventory_role_consumables领域凭据。扣物品触发现有资产revision触发器，资源source因此跟随真实当前资产，不把旧裸身上限改标签冒充最终caps。药品允许来源revision前进，不能把上限/成长变更混进药品。

唯一当前HP/MP仍是role_attribute_snapshots.vitals；本模块未加第二份当前值或改根资源存储。既有药品凭据中的vitals是历史审计。新profile下匹配领域已付凭据时，直接返回当前资源的RoleConsumableReceipt.vitals，不再次扣除、不按当前before重建旧transition。旧profile下保留旧ack行为；原生Adapter两种模式都重新读当前权威资源刷新。迁移前已经消耗的旧凭据，迁移后同ID也只确认原消耗并显示当前伤势。

无迁移profile时，即使注入两份规则仍沿原read_attribute_snapshot/update_role_vitals路径；这不静默创建新metadata。已有迁移profile而未注入规则时，根旧混合读取围栏明确拒绝；未知policy、缺载体等错误不回退成旧资源或训练值。缺钱包、当前值/物品原生编码失败和任意后续异常均应回滚资源、物品、source、两份凭据和版本。

receive_role_consumable在同一事务预编码普通世界c32c8的当前60/70 HP/MP及带真实cash的携带栏c03f3，返回list逻辑消息；提交后由目标连接发送。药品不改变caps，故本Adapter无需另发推测上限；需全量人物快照的外层使用同次current_resource_profile和根既有编码Interface。

## 本批方法与证据

codebase-design把两种实际资源contract放在同一药品Interface，时间和世界资格继续归角色Owner；依赖成对显式注入。tdd沿既有角色事务/不可变资产/原生receive Seam：缺构造注入的实际失败后补分支，真实70/40、已穿49009和物品扣除转绿，再补同事务source、重放和失败验证。writing-for-agents按构造/位置传参/调用方事务分别给出完成条件。本批未改root数值模块或共享入口。

verify_role_consumable_resources通过：70/40使用真实药品变100/40；品质MP药变100/100；扣物来源revision更新，最终武器外攻45保持；后来10/20或死亡0的已付请求仅刷新当前，不重新治疗。真实载体/资源回执/领域回执保存触发中断、外层失败、无钱包、携带数量超signed32的真实晚期bag编码失败均完整回滚，原失败键后续只生效一次。full/dead拒绝、部分规则拒绝、旧profile兼容、迁移前旧凭据、真实opaque LeasedAccounts换租约和重开通过。结构化证据为role-consumable-resources-verification.json。

必要回归：旧verify_role_consumables、原Owner RC4/MPPC用药切片verify_role_consumable_runtime、role_resource_storage、inventory事务/现金/租约、pet_skill_expiry、task_pet_experience及装备修理共享投影hook均通过。临时数据库，无在线服务/真实角色/GUI/实际战斗；新profile shared路由/创建激活、其他消费者与六槽仍由根统一集成，完整目标active。

# 背包与宠物变更的同事务资源来源接线

2026-10-23，资产窗口。主集成接通用Inventory消息、秘籍或这些方法的独立事务时读本文。原角色资源规则见ROLE_RESOURCE_STORAGE_INTEGRATION；本批只提供可信precommit接缝，来源同步算法使用根的synchronize_inventory_resource_source，不复制计算，不启用新profile或修改shared。

已付通用命令现有独立公开只读Interface：current_mutation_messages_transaction(db,kind,body,epoch,now_ms=None)，具体顺序/支持集合和当前宠物选择/旧宠放生处理见INVENTORY_CURRENT_MUTATION_MESSAGES。根先校验共同凭据及replayed=True严格source，再调用此方法；已付分支不再调用receive。

## 原生Adapter接法

新增可位置传递的末尾参数：

```python
Inventory.receive(kind, body, precommit=None)
Inventory.receive_pet_skill_book(body, epoch, request_id, draws, now_ms=None, precommit=None)
```

trusted precommit的形状为`precommit(db, inventory, current_snapshot, *, replayed: bool)`。它在实际变更后、原生回复编码与同一个事务提交前同步执行，snapshot由同一个db、当前epoch读取，包含未提交资产。不另开连接，不访问Session/writer，不返回协程。异常会回滚资产、来源和全部该事务内凭据。

根可用仅捕获不可变命令字段/冻结规则的闭包：

```python
def source_precommit(db, inventory, snapshot, *, replayed):
    return synchronize_inventory_resource_source(
        db, account_id, role_id, epoch, snapshot, request_id,
        resource_rules=resource_rules,
        equipment_rules=equipment_attribute_rules,
        replayed=replayed)

# Owner.io仅收*args，故接缝参数可位置传入。
replies = await owner.io(inventory.receive, kind, body, source_precommit)
book_replies = await owner.io(inventory.receive_pet_skill_book,
    body, epoch, request_id, fixed_draws, now_ms, source_precommit)
```

account_id、role_id、epoch、request_id为本次已受理命令的可信字段，不取自客户端重试标记；规则启动注入。根仍负责场景/战斗/传送门禁、同一命令身份和提交后连接投递。源同步返回值仅供回调使用；Inventory回给网络的仍是自身逻辑消息列表。source-only不改变数值资源/属性，无需为了来源版本另发推测人物属性包。

完成条件：每个启用新profile的实际变更路由传入可信hook，回调调用根helper且原生消息在同事务预编码；未具备这项条件的变更继续拒绝。根helper未迁移精确返回None；fresh只做inventory_change同caps来源CAS；领域已付replay只严格读取当前profile，pending来源拒绝而不补写。

## 已覆盖的事务与历史判定

通用receive的MOVE_ITEM、ARRANGE_BAG、宠物USE_ITEM、ADD_PET_POINT、RENAME_PET、FIGHT_PET、REST_PET、FREE_PET均在其实际写事务内调用hook。移动/整理已由“先提交再另开连接查询回复”改为同事务核心→hook→真实cash/背包编码→提交；这也修复了晚期回复失败仍保留移动的风险。改名/选择/休息/放生也在同一事务编码回复。

上述旧协议和独立操作没有自己的外部稳定请求凭据，执行了一次真实操作后明确传False；不把相同线包或相同目标位置伪装成已付历史。原生协议没有请求ID，新点击是新命令。稳定Owner命令重试和共同凭据仍归根，不能仅依赖此bool去重客户端点击。

秘籍Adapter在同事务先检查是否存在该领域凭据，再调用现有learn_pet_skill做完整身份、fingerprint/规则/版本校验。只有校验成功的既有凭据传True；新学习传False。冲突会在hook前拒绝。当前Pet/真实cash/拓格进度及绑定完整栏仍在hook之后、提交之前编码；当前时钟规则保持PET_SKILL_EXPIRY_DECISION。

公开独立事务方法`move_item`、`arrange_bag`、`rename_pet`、`fight_pet`、`free_pet`新增keyword-only precommit=None；原返回语义保持。这些方法复用相同事务核心，hook看到真实结果。调用方自己持有db的apply_settlement、equip_transaction、unequip_transaction等接口仍由其外层在全部变更后调用统一helper；没有在奖励/成长中间提前同步来源。

通用legacy EQUIP_ITEM/UNEQUIP_ITEM也有接缝，但资源上限变化应走根现有专用穿脱原因事务。source-only helper会拒绝上限变化，不能将它当作穿脱、磨损、修理或成长结算替代。人物药品自身的新资源接线不变，见ROLE_CONSUMABLE_RESOURCE_INTEGRATION。

## 本批实际方法与验证

tdd沿既定原生receive/角色事务/冻结快照Seam：实际MOVE_ITEM传入hook因旧签名拒绝而红→同事务核心和位置参数实现后绿。随后验证真实source-only CAS、领域历史与失败。codebase-design将可变事务核心留在Inventory，可信回调只负责根资源接缝；保留两个旧公开Adapter及只读查询行为。writing-for-agents按通用消息、秘籍和外层事务列出接法及严格完成条件。

verify_inventory_resource_hook.py通过：实际已穿49009、已知70/40资源，移动/整理/改名/加点/宠物药品/真实参战选择/休息/放生均同步当前来源且人物资源version始终0。秘籍首次False、校验过的历史True；原客户端学习/背包codec消费当前回复。不同draw复用请求ID在hook前拒绝；后来无同步资产导致的pending状态，旧秘籍replay严格拒绝且不修补。真实source receipt保存abort、source CAS之后回调失败和实际数量超signed32导致的晚期bag编码失败均回滚资产/来源/凭据；同失败键后来能提交。async回调拒绝，实际opaque LeasedAccounts换租约及旧回调拒绝通过。

结构化证据inventory-resource-hook-verification.json。既有移动/整理、cash/租约、宠物原生命令/成长/显示/药品/技能/到期、人物药品新资源、卸装与任务宠物经验回归通过。血脉基线新增字段使独立原serializer期望增加已知白色上限1139，原序列化全字节对比已重新通过；未放宽原生比对。没有修改根数值/shared、启动服务、操作真实角色/GUI或实际战斗。

# 本批NPC资源接缝签名

2026-10-23，NPC窗口给唯一shared集成方的最小契约。完成状态、必要shared门控解除及实际检查见[NPC_ASSET_RESOURCE_INTEGRATION.md](NPC_ASSET_RESOURCE_INTEGRATION.md)。未部署/自动激活profile。

- `npc_gameplay.purchase(accounts,inventory,intent,precommit=None)`。
- `npc_shop_sales.settle(accounts,inventory,intent,precommit=None)`：sell/buyback同一入口。
- `npc_gameplay.depot_operation(accounts,inventory,service,kind,body,precommit=None)`：只对真实MOVE_ITEM及其领域已付重试调用hook；open/query/cash不改变inventory版本，不调用此资产hook，不能借纯读取修补来源。
- 上述hook统一为`precommit(db,inventory,current_inventory_snapshot,*,replayed: bool)->tuple[(type:int,body:bytes),...]`，keyword-only replayed来自已验证领域指纹/公共receipt的真实bool。fresh=False，领域receipt存在且意图相同=True。捕获实际受理request_id的可信闭包调用root synchronize_inventory_resource_source，再按需要current_resource_profile/growth_refresh编码。返回None或可变消息会拒绝并回滚。
- `npc_repairs.repair(accounts,inventory,intent,precommit=None,*,draw_source=...,resource_rules=None,equipment_rules=None)`：保留原三参数precommit(db,inventory,snapshot)，无需main猜replayed。注入新资源规则后，fresh内部捕获唯一before→真实耐久/收费→实际after_caps→equipment_repair计划/CAS；old只严格读当前profile。然后再调用shared纯final precommit。两规则必须成对。
- `npc_recovery.settle(...,*,resource_rules=None,equipment_rules=None)`保持上一批签名；kind1内部治疗事务已接唯一资源，pet kind2/3/4本批补用统一source-only helper，重试传真实old标记，不重建HP过渡。

规则启动加载后显式注入，无root字段名猜测、热路径配置解析或隐式迁移。precommit=None保留旧未迁移调用；main负责在新profile真实mutation缺hook/规则时预先拒绝。NPC窗口不改shared/root数值。所有同步必须在各NPC自开外层db事务中完成，不能等返回后再在shared补写source。

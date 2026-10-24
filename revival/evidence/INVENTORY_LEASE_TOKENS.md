# 装备事务和快照的租约身份

2026-10-23。Inventory.equip_transaction、immutable_snapshot_transaction与use_role_consumable现接受原样opaque字符串（1..128字符），并兼容严格int的正63位旧租约（0<epoch<2^63）。bool、空/超长字符串、其他类型、超限整数在查库前拒绝。字符串不转数字；例如00007与字符串7/整数7分别判定。没有修改accounts或共享租约生成器。

每次均在调用方已有事务内检查实际roles归属与role_leases的当前active身份；只接受类型不等于拥有资格。Inventory可从LeasedAccounts接收可信epoch，普通AccountStore调用方显式提供；不从客户端字段或查库猜身份。EquipmentEvent.login_epoch为int|str，JSON保存原类型和内容。重登后当前新租约可以确认已提交历史，但replayed=True、事件原epoch不变；旧租约连历史确认也拒绝。

同事务快照仍返回原冻结InventorySnapshot，包含未提交的当前版本、物品/条件/详情、宠物/成长/养护；无新连接/提交/写入。equipment_bag_messages沿实际钱包检查，不补假现金。公共签名未改变，已有整数调用保持兼容。

验证：verify_inventory_lease_tokens.py使用实际LeasedAccounts/FencedConnection与临时库，验证Unicode token原样保存、同事务穿戴/快照/现金回复、人物用药重试只扣一次、新旧租约隔离、00007区别及超限整数拒绝。最初字符串在快照入口失败；新增2^63反例实际产生OverflowError，修正后均通过。

verify_master_inventory_lease.py使用真实任务和背包公开Interface，完成受控intro前置→师父对白授权→原卡选择→绑定实例/condition/detail→实际精确实例slot0→type59完成/车夫激活。全部使用opaque字符串；后续处理失败使装备、事件、type59、车夫同时回滚，同键重试只确认历史。这里只验证独立调用方事务，未改共享路由、未发卡给现场角色、未验证真实GUI，也不重复宣称其他窗口的intro运行时工作归本模块。

任务窗口的43路线/86选择整数验证仍是既有证据；本批新增字符串实际链路切片，清除了其文档列出的Inventory字符串依赖。共享运行服接线与最终原生连续连接验收仍由集成方执行。

方法：diagnosing-bugs用公开Interface的确定性失败区分类型校验、SQL身份比较和历史回执；tdd在原Seam补超限整数红→绿；codebase-design复用角色事务和冻结事件，不增加全局锁/路由层；writing-for-agents集中列出身份形状、来源和提交条件。生产改动仅inventory.py，未改共享入口或现场租约。

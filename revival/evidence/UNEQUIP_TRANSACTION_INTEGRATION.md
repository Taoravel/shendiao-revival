# 卸装公开事务Interface

2026-10-23，集成方要求卸装与最终人物属性投影同事务，本模块已补：

`Inventory.unequip_transaction(db, key, target_slot, epoch, request_id) -> UnequipEvent`

调用方持有当前角色租约事务，key为当前穿戴的自有实例；target_slot=-1表示受理时选择首个空携带格，或显式0≤slot<容量。只读配置在启动注入。本方法不建连接、不提交、不编码/发送；同一request_id与equip共享意图账本，区分操作名/实例/目标。提交后重放只返回`replayed=True`历史事件，不卸下后来重新穿戴的装备；新有效租约能确认旧历史，事件保留原login_epoch。

`UnequipEvent`为冻结独立类型，字段role_id、login_epoch、request_id、item_key、template_id、previous_equipment_slot、target_slot、inventory_revision、replayed。previous_equipment_slot是卸下前的装备槽，target_slot是当次实际携带格。它不是EquipmentEvent，不能作为type59穿戴完成事实；现有EquipmentEvent/equip_transaction/immutable_snapshot_transaction/equipment_bag_messages签名与语义保持不变。

共享接入步骤：验证原生卸装包和角色命令上下文→调用上述Interface→在同一db事务用immutable_snapshot_transaction取得当前资产→按current_equipment_projection重算当前绝对人物属性并预编码20项→同事务调用equipment_bag_messages预编码当前双栏→公共回执与变更一起提交→提交后经目标连接发送。投影/钱包/编码错误让外层回滚，不直接用历史event当当前资产。

已通过`verify_unequip_transaction.py`：公开Interface无嵌套连接；冻结快照版本/实际cash/目标格与卸装匹配；重试、同键目标/操作冲突、重新穿戴后旧请求不卸新状态；真实凭据写入abort、外层失败、缺钱包整体回滚；无效格/非穿戴/他人/缺事务/过期租约拒绝；实际LeasedAccounts的opaque中文token、新租约读旧历史、重开保留。独立类型避免误触穿戴任务。

本验证未启动服务/客户端，尚未接共享人物投影路径；人物最终20项与任务师承实际集成由原始集成窗口统一处理。装备私有_unequip保留给旧兼容路径，新增shared使用公开方法。

方法：沿用codebase-design的小Interface与调用方事务Seam；tdd先以公开方法缺失复现，再验证资产当前状态/幂等；diagnosing-bugs用真实receipt触发器验证部分写入失败；writing-for-agents集中字段与接入完成条件。产物为Inventory局部新增、verify_unequip_transaction.py及unequip-transaction-verification.json；没有改共享入口或当前发布。

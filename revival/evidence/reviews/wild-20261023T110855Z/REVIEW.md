## Standards

# Standards

结论：固定候选当前硬违反0项；有实际后果的判断性smell 0项。保留两项前轮缺陷记录：关闭吞操作/遗留Owner，以及五数快照遗漏完整resource source；本次均已修复，不能将前轮0项理解为这些缺陷从未存在。

固定比较：master-ready-exit-20261023T110056Z/source → wild-20261023T110855Z/source；非Git，无提交列表。scope.json的8个候选及6个既有基准哈希全部匹配。准确范围为wild_runtime_storage.py、wild_rewards.py、verify_wild_runtime.py、role_resource_plan.py、role_resource_storage.py、design/role-resources-v1.json、verify_role_resource_combat.py、game_runtime.py。另核对基准中其余1417个非缓存文件逐字节保留，原任务/退出修复未被覆盖。

资源来源修复：wild_runtime_storage.py:105–110按format2冻结完整RoleResources；:181–199在consume之前以asdict完整比较，包含caps.source/policy，拒绝仅库存来源改变、carrier有无改变；旧未结算且已迁移行缺少source时明确拒绝核对。已settled仍先走当前只读刷新，不重造终局或扣血。符合ROLE_RESOURCE_COMBAT_INTEGRATION“完整before/source必须拒绝，不把终局重贴新来源”及ARCHITECTURE版本化快照规则。

关闭修复继承：game_runtime.py:321–356以finally释放Battle/Map；:857–873重试非终局后继续原close。最新世界初始化保留load_exit_ui_message、构造期只读加载及spawn前发送；相对master基准该文件仅关闭修复两处。runtime_storage/battle_owner/wild_battle与前轮已审候选哈希相同，沿用实际入口的Owner、工作线程I/O、持久checkpoint、提交后消息与新租约恢复审查。

方法：沿用已读code-review的十二项Fowler判断性baseline、codebase-design的所有权/Interface/Seam；AGENTS、ARCHITECTURE、DESIGN_AUTHORITY及wild授权/接入和resource combat规范优先。没有为无实际后果的风格差异制造发现。

验证与限制：本轴仅静态文件、diff及哈希，未运行DB/战斗/服务/GUI。父任务报告来源红绿回归和11项Owner检查通过，本轴不声称独立执行。当前尚未发布；不证明现场、容量或完整原版平衡。


## Spec

# Spec最终复核（仅静态）

结论：0项未解决问题，原断线P2已关闭。

沿用code-review与codebase-design，按需求1–7复核实际移动、快照、独立战斗、终局事务、重试及跨lease恢复。8文件前后hash全匹配；基准为master-ready-exit-20261023T110056Z，无Git提交。重基context已核：四个任务/退出文件逐字相同；game_runtime相对该基准仅继承已审close两处修复，世界初始化及退出路由保留。

wild_runtime_storage.py:109冻结format2完整RoleResources；187先比较全部source/版本/数值，再消费终局。旧已付重放先返回当前值；旧未付迁移记录缺source在192拒绝显式核对。新增来源回归检查同五数、不同source拒绝且回滚后仍可结算。未发现新guard造成遗漏或越界。

game_runtime.py:341–353继承finally清理战斗/地图，870继续真正close；继承入口与资源Module范围保持分别审核。

本次只读取/hash核对，未执行测试、DB、服务或GUI；11项执行结果属集成方证据。候选未发布，现场版本与客户端验收不在本结论内。


Standards 0项未解决、无最高问题；Spec 0项未解决、无最高问题。前轮断线及完整来源缺陷的原报告和真实红绿反馈均保留，不代表从未发现问题。

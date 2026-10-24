# Standards

结论：当前硬规范违反0项；有实际后果的判断性smell 0项。原ENTRY_STANDARDS的P2关闭缺陷已修复。

固定候选：`runtime/deployments/wild-20261023T105951Z/source`，基准为`npc-20261023T102110Z/source`，准确差异见本目录scope.json/changes.diff。8个候选、6个既有基准SHA256匹配；非Git，无提交列表。

范围：wild_runtime_storage.py、wild_rewards.py、verify_wild_runtime.py、role_resource_plan.py、role_resource_storage.py、design/role-resources-v1.json、verify_role_resource_combat.py、game_runtime.py。实际入口沿前轮entry-scope/entry-changes补审：runtime_storage.py、battle_owner.py、wild_battle.py及完整wild_runtime_storage.py在新候选中哈希未变，继承该静态审查；game_runtime.py重新核对close、battle_step及调用上下文。

关闭修复：game_runtime.py:854–870先重试已缓存非终局checkpoint，再执行原close，避免吞掉关闭；:321–356的嵌套finally即便持久化持续失败，也移除rt.battles、关闭Battle邮箱并离开地图。最新租约仍只恢复已持久copy/outbox，不把未落盘状态声称已成功。新增两项验证分别覆盖短暂checkpoint故障后的精确伤害与邮箱释放、持续故障后的释放及新租约零奖恢复，符合ARCHITECTURE的局部故障恢复要求。

方法：沿用已读code-review的双轴分离及十二项Fowler判断性baseline、codebase-design的状态所有权/Interface/Seam，项目规则优先。规范仍为AGENTS、ARCHITECTURE、DESIGN_AUTHORITY、WILD_RUNTIME_INTEGRATION、WILD_RUNTIME_DIRECT_AUTHORIZATION、ROLE_RESOURCE_COMBAT_INTEGRATION。旧资源拒绝自动迁移、唯一carrier、宠物后成长快照、提交后返回消息等结论未因修复改变。

验证：本轴仅静态文件/diff/哈希；未运行DB、战斗、服务、GUI或回归脚本。父任务报告两项原生临时数据库回归及既有流程已绿，本报告不将其冒充本轴执行。尚未部署；未来master-ready重基后的内容不在本次固定候选结论内。

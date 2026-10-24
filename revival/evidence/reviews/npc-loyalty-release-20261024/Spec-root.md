# Spec 独立审查

缺失1（发布接线），额外行为0，报价实现错误0。

**已迁移角色在真实BASE被共享入口提前拒绝。** `NPC_PET_LOYALTY_INTEGRATION.md:7`称“生产增量只有…两文件”，L15称“单一source同步契约沿用”，L22所述Owner验收包含“当前单一人物资源10/20”。但准确BASE的 `source/runtime_storage.py:697–703` 对全部kind!=1先调用 `_require_unmigrated_operation`；L743–747遇已初始化resource即抛错。真实两个恢复入口 `source/game_runtime.py:584/628` 均经过此处。因此合法L21、power9、缺忠诚20的迁移角色不会进入候选 `npc_recovery.py:231`，新kind3/4不能恢复/收1260，已有paid也到不了L251–258凭据分支。两输入领域实现正确不足以支持交单中的Owner范围。应另冻并复核必要共享接线，或将发布能力明确限定为未迁移角色；不能据工作区Owner结果认定该两输入组合可用。此为实际BASE集成缺口，不归为报价公式回归。

其余核对：政策L10–18的逐宠当前power/合法care、缺失blood明确45来源及免费门槛，对应候选L130–170；present/orphan拒绝，kind2/inn不走新价。政策L23–25的单事务/旧paid兼容对应L245–305：保留npc.1指纹，旧receipt先于新报价，source同步及最终编码仍在原事务。

方法：沿用完整code-review/codebase-design，按ARCHITECTURE角色事务和DESIGN_AUTHORITY来源分级，追踪公开Interface到准确BASE调用方；未读Standards。非Git，以冻结SHA固定范围：候选 `e9a450596b38c8434139deb186f27f32ac1eb6cb916248a13ef79a9a43c17bab`、`09cc5d0572dc56b439b1ab16d132b70fb4e36390ca8642db5d67821d5af7ea29`，基线 `8e036f288d251b27ecb847e3d0a0771ed98d77ddac60456ad0b7f9bc031f9390` 全匹配scope；新政策base为空。

仅静态审查2输入/189diff行及必要消费者；未运行测试、DB、服务、GUI、真人或战斗，未将他方测试作为本轴执行证据。

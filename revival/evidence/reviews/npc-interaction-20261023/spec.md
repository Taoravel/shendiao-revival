# Spec

需求缺失：0项。额外范围：0项。错误实现：0项。

按已读code-review Spec、codebase-design及项目约束审查，依据同目录NPC_INTERACTION_DISTANCE_DECISION.md和npc-interaction-v1.json；八个base/current真实字节SHA均匹配manifest。

仅精确1006/13/10498使用包含边界的48，其余32。启动严格核唯一原摆放1668/970及definition.id，拒绝未知/重复/bool/非整数配方。Scene/Lifecycle均用同一冻结规则、当前NPC位置及当前角色位置复核；保留地址、租约、位置版本、active与generation围栏。新生命周期spawn分配新placement，不继承已移除原13例外。旧显式半径兼容；注入rules时要求default匹配。热路无配置读取，原资源tuple未改。

独立优先导入冻结current：8组距离检查、旧Scene及Lifecycle必要回归均通过，覆盖48/49及斜线、当前位置变化、跨实例、旧generation、移除和新spawn、启动冻结及无热读。

产物：本报告。仅领域/纯验证；共享自然链待主集成，不由这8组推定intro血手印、固定发布或GUI成功。未改生产、shared、政策、真实库或服务。

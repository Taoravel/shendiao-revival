# Spec 静态审查

结论：0 项确证问题。未发现本次差异造成的需求缺失/部分实现、越界行为或表面实现但实际错误；这不是运行或发布验收。

固定范围：以 `npc-20261023T102110Z/source` 为基准，审查 `wild-20261023T104109Z/source`；非 Git，无提交列表。使用本目录 `changes.diff` 和 `scope.json`，7 个变更文件的前后 SHA256 全部匹配：wild_runtime_storage.py、wild_rewards.py、verify_wild_runtime.py、role_resource_plan.py、role_resource_storage.py、design/role-resources-v1.json、verify_role_resource_combat.py。保留入口仅作调用背景读取，不把既有代码问题归为本次新增。

依据：`WILD_RUNTIME_INTEGRATION.md`「要求与已接代码」1–7，以及 `WILD_RUNTIME_DIRECT_AUTHORIZATION.md` 的本窗口接入授权。按 code-review 的 Spec 轴逐条追踪，按 codebase-design 沿角色、战斗、持久化 Interface 检查真实调用与事务归属。

核对结果：移动受理、独立 BattleOwner 与启动配置已有实际入口；新差异让未迁移旧档只在原 vitals 与投影完全一致时入场，并在同事务写回原 carrier（wild_runtime_storage.py:64、180、198）。迁移档保留显式 carrier；宠物结算后的资产快照先同步 source，再供人物升级使用（wild_rewards.py:281），终局/outbox、当前 lease 恢复与最终状态编码仍在角色事务路径。资源四文件另有 Module 专属双轴审查；此结论不替代它。

验证仅为读取和 hash 核对；未运行测试、数据库、战斗、服务或 GUI。临时 fixture 报告仅作测试覆盖资料，未当作现场客户端证据；生产默认 5 秒/20%/10 秒与活动范围未被本次差异扩大。现场部署、真实 GUI、容量和故障注入结果均未由本审查验证。

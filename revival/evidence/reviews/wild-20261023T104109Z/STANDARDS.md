# Standards

结论：硬违反 0 项；有实际后果的判断性 smell 0 项。

固定比较：`runtime/deployments/npc-20261023T102110Z/source` → `runtime/deployments/wild-20261023T104109Z/source`；非 Git 项目，无提交列表，依据本目录已捕获的 `changes.diff`、`scope.json`。7 个候选文件及 5 个既有基准文件 SHA256 全部匹配，未把工作区后续写入视为候选。

准确范围：`wild_runtime_storage.py`、`wild_rewards.py`、`verify_wild_runtime.py`、`role_resource_plan.py`、`role_resource_storage.py`、`design/role-resources-v1.json`、`verify_role_resource_combat.py`。

规范依据：根 `AGENTS.md`；`revival/ARCHITECTURE.md` 的状态所有权、阻塞 I/O、同事务结算与接入标准；`DESIGN_AUTHORITY.md` 的来源与禁止自动迁移规则；`evidence/WILD_RUNTIME_INTEGRATION.md`、`WILD_RUNTIME_DIRECT_AUTHORIZATION.md`、`ROLE_RESOURCE_COMBAT_INTEGRATION.md`。未找到额外 CODING_STANDARDS/CONTRIBUTING。

方法与决定：读取 code-review、codebase-design；将 Fowler 十二项 baseline 作为判断性启发，项目明确规则优先。按深 Module 的 Interface/Seam、Locality 核对资源归属：新增旧档分支仅对精确当前 vitals CAS 后消耗，不再借入场迁移；已有 resource carrier 继续由资源 Module 复算终局；宠物变更后在同事务刷新资源 source 和成长快照。未新增提交、网络发送或 DDL 热路径，未发现值得报告的重复转发/越权状态持有。

静态上下文：读取固定候选 `game_runtime.py` 的 load、wild_move、battle_step、finish_battle、关闭路径，`runtime_storage.py` 启动及成长上下文，`battle_owner.py` engine factory，以及直接使用的存储 Interface，检查实际调用后果。主策划四文件审查未被外推为整体 wild 通过。

验证：只做文件读取、diff 与哈希核对；未运行游戏、数据库、战斗、服务、GUI 或验证脚本。没有证明运行时正确性、现场部署、容量或原版数值平衡；Spec 由独立轴报告。

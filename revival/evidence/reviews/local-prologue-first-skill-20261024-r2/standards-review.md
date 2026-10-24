# Standards — r2 增量

硬违反：0。沿用 r1 的根 AGENTS、ARCHITECTURE“状态所有权／同事务资产与凭据／配置启动冻结”、DESIGN_AUTHORITY“来源及实测状态分离”标准。`role_skills.py` 只将已加载币种映射冻结为 tuple；`task_first_skill.py` 调用既有公开 `plan_task_reward` 核原字段和指纹，新增各前缀经验、空物品、原零宠奖决策及应付货币凭据的只读审计。没有调用奖励 writer、另开事务、重写其他所有者或扩大迁移来源；原 COMMIT 资格再核、账本 CAS、同事务授技／奖励／后继／回执及已付纯读路径未改变。空 catalog 仅用于明确无物品的原前缀规划核验，不作为物品授予依据。新增 missing/null 负例仍在临时库保存点内回滚，未隐藏真人／资源 outbox 未验范围。

判断建议：本增量新增 0；继承 r1 非阻断 possible Feature Envy 1 项：资格审计直接了解角色／钱包回执表结构，后续可收敛到其所属 Module 的只读证据 Interface，本批不要求扩大重构。完整十二类均重新判断：Mysterious Name、Duplicated Code、Feature Envy、Data Clumps、Primitive Obsession、Repeated Switches、Shotgun Surgery、Divergent Change、Speculative Generality、Message Chains、Middle Man、Refused Bequest。各奖励渠道的不同指纹与凭据形状有真实差异，不为消除相似判断引入泛化框架；其余无新增值得报告项。

方法与核验：code-review Standards＋codebase-design 的 Locality／Seam 判断。核 6 文件精确 r1 基线、两端 SHA、19 输入、原政策 SHA、112 行规范化重建 diff、AST 解析及自然验证记录 12 项候选源码绑定；missing/null 拒绝结果只读取冻结记录。未运行模块、DB 或测试，不独立重证红绿；真实角色、资源/outbox、共享接线和 GUI 范围保持 r1 限制。本报告不评 Spec。

# Standards

硬违反：0。标准来源为根 `AGENTS.md` 的所属模块分工、`revival/ARCHITECTURE.md` 的角色所有权／同事务资产与凭据／启动配置加载、`revival/DESIGN_AUTHORITY.md` 的来源和运行状态分离。`role_skills.py:309` 在调用方事务内插入独立 designed 来源和唯一迁移凭据，不冒充 VerifiedOtherSkillBaseline；已有账本与已付迁移返回当前值并保留原 epoch。`task_first_skill.py:282` 对 UNKNOWN 只读冻结资格；`:302` 提交重核真实创建资料、完整原路线收据、前驱胜利和私有地图凭据，然后同事务迁移、max 授技、原奖励、后继、教学回执及完整消息编码。加载政策只在显式启动路径；无共享入口或 Domain 改写，无将缺行直接当已知空技能的通用兜底。冻结设计政策明确区分兼容起点与历史事实，验证记录保留真实角色和资源/outbox 尚未验的限制。

判断建议：1（非阻断）。possible Feature Envy：`task_first_skill.py:246` 的 `for table in ('role_settlements','role_wallet_receipts')` 使 Task 资格审计了解角色、钱包回执表结构；后续可由所属 Module 提供同事务只读证据 Interface，Task 继续拥有 cohort 判定。本批无跨所有者写入，不作为硬违反。其余完整 baseline：Mysterious Name、Duplicated Code、Data Clumps、Primitive Obsession、Repeated Switches、Shotgun Surgery、Divergent Change、Speculative Generality、Message Chains、Middle Man、Refused Bequest 均无值得报告项；既有参数束和政策绑定字段符合仓库接口，未强推包装层。

方法与核验：code-review Standards＋codebase-design 的 Seam／Locality 判断。静态解析 6 文件 AST，核精确 r3 基线／新增空基线、两端 SHA、19 输入、政策 SHA、750 行重建 diff，以及自然教学记录的 12 项候选源码绑定。Domain 字节不变。只读取原八组及新隔离验证证据，未执行源码、DB、测试、真人存档或 GUI；资源/outbox、共享接线与真人资格仍需 main/root 验收。本报告不评 Spec。

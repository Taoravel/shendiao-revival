# 本地旧序章教学：固定双轴


## Standards（r1）

# Standards

硬违反：0。标准来源为根 `AGENTS.md` 的所属模块分工、`revival/ARCHITECTURE.md` 的角色所有权／同事务资产与凭据／启动配置加载、`revival/DESIGN_AUTHORITY.md` 的来源和运行状态分离。`role_skills.py:309` 在调用方事务内插入独立 designed 来源和唯一迁移凭据，不冒充 VerifiedOtherSkillBaseline；已有账本与已付迁移返回当前值并保留原 epoch。`task_first_skill.py:282` 对 UNKNOWN 只读冻结资格；`:302` 提交重核真实创建资料、完整原路线收据、前驱胜利和私有地图凭据，然后同事务迁移、max 授技、原奖励、后继、教学回执及完整消息编码。加载政策只在显式启动路径；无共享入口或 Domain 改写，无将缺行直接当已知空技能的通用兜底。冻结设计政策明确区分兼容起点与历史事实，验证记录保留真实角色和资源/outbox 尚未验的限制。

判断建议：1（非阻断）。possible Feature Envy：`task_first_skill.py:246` 的 `for table in ('role_settlements','role_wallet_receipts')` 使 Task 资格审计了解角色、钱包回执表结构；后续可由所属 Module 提供同事务只读证据 Interface，Task 继续拥有 cohort 判定。本批无跨所有者写入，不作为硬违反。其余完整 baseline：Mysterious Name、Duplicated Code、Data Clumps、Primitive Obsession、Repeated Switches、Shotgun Surgery、Divergent Change、Speculative Generality、Message Chains、Middle Man、Refused Bequest 均无值得报告项；既有参数束和政策绑定字段符合仓库接口，未强推包装层。

方法与核验：code-review Standards＋codebase-design 的 Seam／Locality 判断。静态解析 6 文件 AST，核精确 r3 基线／新增空基线、两端 SHA、19 输入、政策 SHA、750 行重建 diff，以及自然教学记录的 12 项候选源码绑定。Domain 字节不变。只读取原八组及新隔离验证证据，未执行源码、DB、测试、真人存档或 GUI；资源/outbox、共享接线与真人资格仍需 main/root 验收。本报告不评 Spec。


## Spec（r1）

# Spec

遗漏1项；扩域0项；其他实现错误0项。独立Spec轴，不合并Standards。

**[P2] 完整奖励来源审计尚未闭合。** 独立政策 `chapter_evidence` 要求“complete journal/command/reward/teaching receipt audit”，`unknown_stored_ledger`要求“broken source/creation records … refuse”。`task_first_skill.py:_local_baseline_basis` 对command/effects校验了完整前缀集合，但奖励通道只遍历现有行，检查非下游、指纹格式及JSON可解码；asset receipts也只遍历现有ID。若前缀100105的`character_exp`通道已缺失，或其receipt为合法JSON `null`，不会因奖励审计拒绝，仍可重新开菜单并在COMMIT形成匹配basis。由此来源断裂的UNKNOWN角色也能获得designed空起点。应以只读审计核必要原通道/奖励凭据存在及其task/channel/原奖励与指纹对应，并增缺失/合法JSON错误内容负例；不应补发历史奖励。当前自然9/11正例不受此问题阻断。

其余所读增量符合窄范围：UNKNOWN opener仅冻结basis/None revision，无写空；COMMIT重核creation/profile、本人章/路线、前缀journal/commands/effects、真前驱proof、私有checkpoint、当前task及时间票据。独立designed origin/permit/唯一receipt未冒充Verified基线；技能/120XP/原后继/receipt/native编码在同TX。known map保留，ledger同/新lease receipt-first返回后来值；teaching paid在已有receipt分支不重跑cohort。

方法/验证：code-review Spec静态核r3基线、750行归一化文本patch、6source/19inputs及独立policy SHA，均一致；Domain不变。读取真实专用engine自然教学、lateSQL回滚和8组known回归报告，未重跑DB/测试。资源/outbox/shared、真人资格及GUI仍未证明；不将通用cohort正例等同当前真人角色已获准。


## Standards（r2）

# Standards — r2 增量

硬违反：0。沿用 r1 的根 AGENTS、ARCHITECTURE“状态所有权／同事务资产与凭据／配置启动冻结”、DESIGN_AUTHORITY“来源及实测状态分离”标准。`role_skills.py` 只将已加载币种映射冻结为 tuple；`task_first_skill.py` 调用既有公开 `plan_task_reward` 核原字段和指纹，新增各前缀经验、空物品、原零宠奖决策及应付货币凭据的只读审计。没有调用奖励 writer、另开事务、重写其他所有者或扩大迁移来源；原 COMMIT 资格再核、账本 CAS、同事务授技／奖励／后继／回执及已付纯读路径未改变。空 catalog 仅用于明确无物品的原前缀规划核验，不作为物品授予依据。新增 missing/null 负例仍在临时库保存点内回滚，未隐藏真人／资源 outbox 未验范围。

判断建议：本增量新增 0；继承 r1 非阻断 possible Feature Envy 1 项：资格审计直接了解角色／钱包回执表结构，后续可收敛到其所属 Module 的只读证据 Interface，本批不要求扩大重构。完整十二类均重新判断：Mysterious Name、Duplicated Code、Feature Envy、Data Clumps、Primitive Obsession、Repeated Switches、Shotgun Surgery、Divergent Change、Speculative Generality、Message Chains、Middle Man、Refused Bequest。各奖励渠道的不同指纹与凭据形状有真实差异，不为消除相似判断引入泛化框架；其余无新增值得报告项。

方法与核验：code-review Standards＋codebase-design 的 Locality／Seam 判断。核 6 文件精确 r1 基线、两端 SHA、19 输入、原政策 SHA、112 行规范化重建 diff、AST 解析及自然验证记录 12 项候选源码绑定；missing/null 拒绝结果只读取冻结记录。未运行模块、DB 或测试，不独立重证红绿；真实角色、资源/outbox、共享接线和 GUI 范围保持 r1 限制。本报告不评 Spec。


## Spec（r2）

# Spec

新增遗漏/扩域/实现错误均0项；r1的P2已闭合，原历史报告保留。独立Spec轴，不合并Standards。

依据政策“complete journal/command/reward/teaching receipt audit”及“broken source/creation records … refuse”，本次对每个原前缀强制完整奖励通道集合，使用既有纯 `plan_task_reward` 核原奖励内容及源指纹；XP需正确原金额/整数历史余额，items需原指纹/空grants，零宠奖需原冻结decision及匹配hash/receipt，币奖需冻结映射、field/currency/amount/policy/source/settlementID完整一致。因此缺100105的XP通道或JSON null均不再通过审计，不会为修来源而重发奖励。

新增 `currency_fields` 只冻结已有政策映射；空item catalog只用于当前无物品前缀的只读规划，不新增grant能力或扩充cohort。原政策字节不变。opener、COMMIT/paid、scope/world函数AST不变，仍只在首次合法教学事务迁移，保留known完整map及receipt-first后来状态；无新增当前角色阻断条件超出已接受的完整审计要求。

验证器在自然真前驱胜利、UNKNOWN且教学前分别删除100105 XP通道和置null，独立savepoint回滚；冻结报告记两例拒绝，并保留真实engine教学、lateSQL回滚和paid当前值结果。修前实际红由执行方提供，本审查未重跑。

方法/验证：code-review Spec静态核r1精确基线、112行patch、6source/19inputs及独立policy SHA，报告candidate SHA均一致。未运行DB/测试、改实现或碰真人；8组known回归及ledger同/新lease结果沿用冻结报告。真实资源/outbox/shared、真人资格与GUI仍未证明。


当前Standards硬0/非阻断建议1；Spec未解决0，r1 P2经两个真实缺损反馈及r2复审闭合。shared/真人资格/发布与GUI另验。

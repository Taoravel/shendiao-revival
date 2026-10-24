# Spec

新增遗漏/扩域/实现错误均0项；r1的P2已闭合，原历史报告保留。独立Spec轴，不合并Standards。

依据政策“complete journal/command/reward/teaching receipt audit”及“broken source/creation records … refuse”，本次对每个原前缀强制完整奖励通道集合，使用既有纯 `plan_task_reward` 核原奖励内容及源指纹；XP需正确原金额/整数历史余额，items需原指纹/空grants，零宠奖需原冻结decision及匹配hash/receipt，币奖需冻结映射、field/currency/amount/policy/source/settlementID完整一致。因此缺100105的XP通道或JSON null均不再通过审计，不会为修来源而重发奖励。

新增 `currency_fields` 只冻结已有政策映射；空item catalog只用于当前无物品前缀的只读规划，不新增grant能力或扩充cohort。原政策字节不变。opener、COMMIT/paid、scope/world函数AST不变，仍只在首次合法教学事务迁移，保留known完整map及receipt-first后来状态；无新增当前角色阻断条件超出已接受的完整审计要求。

验证器在自然真前驱胜利、UNKNOWN且教学前分别删除100105 XP通道和置null，独立savepoint回滚；冻结报告记两例拒绝，并保留真实engine教学、lateSQL回滚和paid当前值结果。修前实际红由执行方提供，本审查未重跑。

方法/验证：code-review Spec静态核r1精确基线、112行patch、6source/19inputs及独立policy SHA，报告candidate SHA均一致。未运行DB/测试、改实现或碰真人；8组known回归及ledger同/新lease结果沿用冻结报告。真实资源/outbox/shared、真人资格与GUI仍未证明。

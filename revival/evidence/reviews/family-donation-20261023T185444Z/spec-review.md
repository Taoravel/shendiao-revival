# Spec review

结论：1 个可行动发现，P1=1，P0/P2/P3=0；以下问题修复前不能判为 Spec 通过。

## 发现

**[P1] 已付款后丢失当前成员档案会被误判为离开，并永久跳过声望。** `source/family_donation.py:253–256` 将“查询不到精确档案”统一转成 `prestige=None`，随后261–270提交资金、建设、ledger和终态凭据。规格 `FAMILY_DONATION_NUMERIC_HANDOFF.md:19` 明确要求：“家族原资金/建设/成员声望基线未知则拒绝”；`FAMILY_DONATION_RUNTIME.md:21` 允许跳过的是“已删除的旧关系”及重入新代次，并不授权把当前缺档当退出。

独立临时库复现：公开 Interface reserve→pay；删除该角色的 `family_member_state`，保留其仍属于原家族的 `family_members`；公开 resolve 返回 committed、funds_after=3100000、prestige_after=None。之后重试只返回既有终态，修复档案也无法兑现本次声望。应区分无当前关系/明确新代次与当前关系仍在但档案缺失；后者保持unknown、拒绝家族阶段并保留付款证明。增补此故障恢复纵切，同时保留离开重入不伤新代次的现有行为。

## 范围与验证

基于已审 guild-dissolution 固定源，通过 since-guild-dissolution.diff 审7个增量文件；无Git历史，使用candidate.json固定快照。沿用已完整读取的 code-review、codebase-design、writing-for-agents，核对两份具体规格及ARCHITECTURE、DESIGN_AUTHORITY、FAMILY_DEVELOPMENT_RESEARCH。检查两个写者职责、原子共同付款、孤儿child、当前背包重试、维护先结算/取消、历史小时不结新贡献、分区容量/恢复与来源口径；除此发现外，未见其他可行动偏差或范围夹带。

独立核验7个候选和592个源码依赖哈希未变；固定源15项脚本结果已齐，均exit0，但上述缺档情形不在现有检查内。复现只写临时数据库，未改生产、候选或共享入口，未启动游戏/在线服。

限制：数值仍 pending_root_review_not_activation_authorization；原296请求decoder、NPC实例准入、正式precommit、完整激活闭包、真实GUI/生产容量/跨库事务及全量玩法不在本批完成声明内。
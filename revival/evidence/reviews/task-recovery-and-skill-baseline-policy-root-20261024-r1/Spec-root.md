# Spec 独立静态审查

Missing/partial：0；Extra：0；Wrong：0。仅审四份新政策，不表示恢复或迁移已实现。

- TASK_BATTLE_INTEGRATION:39 原先仅允许新租约确认已有consumer回执；固定Task源码:337、355也拒绝旧epoch普通settle。新TASK_TERMINAL_RECOVERY_DECISION:3、5–13明确增加受限新Interface：公开读取可信producer原件，保留原admission/event/epoch，当前独占租约重核全量来源CAS，资源/Task/outbox settled同事务；漂移留pending，已有consumer回执只读当前。没有把bool或重写epoch当授权。冻结Task:206–234的胜利证明查询允许当前读租约读取历史receipt，原后继凭据可继续衔接。
- NEWBIE_FIRST_SKILL_DECISION:11 禁止未知历史推空。新baseline policy:4、10–24和decision:3–9明确独立designed例外：本地creation/chapter/route及完整凭据审计、正式前驱真胜、首技active、ledger缺失且无已付/下游矛盾共同准入；完整账本保留，部分/外来/断源拒绝，不使用VerifiedOtherSkillBaseline。缺行本身不是授权。
- 新baseline:22–25明确唯一迁移intent/回执与首次教学同事务，迟错全回滚；已有receipt在教学后或新租约下读当前，不再重核“首技尚未完成”来阻断合法重放，也不重置空map/补历史XP。实际r3 role_skills:126–129尚不接受新origin；policy:26已明确这是待实现的新Interface，不声称旧代码现可消费。

方法：沿用code-review逐项需求追踪、codebase-design所有权/事务Seam检查，重读domain-modeling，以“producer耐久≠consumer结算”“设计起点≠已验证历史”检验崩溃、资格转换及重试场景。非Git，使用固定字节/SHA；未读Standards。

16登记输入及diff审前后全匹配。scope SHA256：9be830b6b171b5e43bc440278bbba43fef2706b2e075444be2f14e0f585a6a38；diff：8ccc470e4d0c9192f4839721c73977691dc373724875c627ce47e6a65ec02151。

未验：未执行代码、测试、DB、socket或服务；未查真人资格、完整技能历史、实际恢复/迁移、shared、发布或GUI。未批准runtime/deploy。

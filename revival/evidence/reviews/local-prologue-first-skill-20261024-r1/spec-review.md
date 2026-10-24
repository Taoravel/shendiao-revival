# Spec

遗漏1项；扩域0项；其他实现错误0项。独立Spec轴，不合并Standards。

**[P2] 完整奖励来源审计尚未闭合。** 独立政策 `chapter_evidence` 要求“complete journal/command/reward/teaching receipt audit”，`unknown_stored_ledger`要求“broken source/creation records … refuse”。`task_first_skill.py:_local_baseline_basis` 对command/effects校验了完整前缀集合，但奖励通道只遍历现有行，检查非下游、指纹格式及JSON可解码；asset receipts也只遍历现有ID。若前缀100105的`character_exp`通道已缺失，或其receipt为合法JSON `null`，不会因奖励审计拒绝，仍可重新开菜单并在COMMIT形成匹配basis。由此来源断裂的UNKNOWN角色也能获得designed空起点。应以只读审计核必要原通道/奖励凭据存在及其task/channel/原奖励与指纹对应，并增缺失/合法JSON错误内容负例；不应补发历史奖励。当前自然9/11正例不受此问题阻断。

其余所读增量符合窄范围：UNKNOWN opener仅冻结basis/None revision，无写空；COMMIT重核creation/profile、本人章/路线、前缀journal/commands/effects、真前驱proof、私有checkpoint、当前task及时间票据。独立designed origin/permit/唯一receipt未冒充Verified基线；技能/120XP/原后继/receipt/native编码在同TX。known map保留，ledger同/新lease receipt-first返回后来值；teaching paid在已有receipt分支不重跑cohort。

方法/验证：code-review Spec静态核r3基线、750行归一化文本patch、6source/19inputs及独立policy SHA，均一致；Domain不变。读取真实专用engine自然教学、lateSQL回滚和8组known回归报告，未重跑DB/测试。资源/outbox/shared、真人资格及GUI仍未证明；不将通用cohort正例等同当前真人角色已获准。

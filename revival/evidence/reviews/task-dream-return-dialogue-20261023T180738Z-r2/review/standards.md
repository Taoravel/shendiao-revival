# Standards — r2增量

**0处硬性标准违反，0处需单列的判断性建议。** 继承前固定快照`task-dream-return-dialogue-20261023T180738Z/review/standards.md`的模块与12类smell审查，本轮只复核r2 delta及完整目标哈希；不替代Spec轴。

已核manifest所有目标/上下文SHA，并逐文件比较新旧source：仅`verify_task_prologue_return_dialogue.py:111、116`两个字符串改变，其他源文件逐字节相同。重新生成的两处差异与correction.diff精确一致；将两字符串归一后AST完全相同，验证行为没有变化。沿用空基线适配，无Git提交历史。

硬规则核对：`:111`将单一前驱拒绝断言缩为combined inactive/missing-predecessor context；`:116`明确有效post-AI8002场景及独立combat-predecessor负例尚未验证。两处更准确地分开已验证行为与未验范围，符合冻结`DESIGN_AUTHORITY.md`“交付分开报告”和`ARCHITECTURE.md:57`的验收表述要求；没有新增功能、授权、传送/结算或共享入口变更。

判断性建议：此次纯报告文字delta未引入可报告的baseline代码气味。未重跑verifier，不以父任务提供的“五组绿”替代独立运行记录；本轴实际验证仅静态差异、全部哈希和AST归一比较。未运行DB、服务、客户端或线上操作；唯一新增本审查文档，未改源码/政策/shared。

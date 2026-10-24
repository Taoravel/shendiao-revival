# Standards

硬违反：0。依据根 `AGENTS.md` 的模块分工、`revival/ARCHITECTURE.md` 的“状态所有权／交易、奖励与跨区／必要验收”、`revival/DESIGN_AUTHORITY.md` 的来源与实测分离要求审查全部 hunk。`source/task_battle.py:355` 保留普通结算当前租约围栏；`:372` 统一核原 admission、Participant、AI、定义与终态身份；`:476` 在当前角色事务中使用明确版本的内部 witness，并保留原事件 epoch。可信 producer 与完整来源 CAS 明示为 main caller 契约，不把 DTO 自身当授权。`:431`、`:456` 的已付分支只查询当前经验、钱包和属性，不调用 reward/chain writer。新增 harness 明示 Participant、terminal、producer/consumer 为契约夹具，未越权声称真实引擎或上线完成。

判断建议：0。完整 Fowler baseline 逐项判断：Mysterious Name、Duplicated Code、Feature Envy、Data Clumps、Primitive Obsession、Repeated Switches、Shotgun Surgery、Divergent Change、Speculative Generality、Message Chains、Middle Man、Refused Bequest 均未见本增量值得报告的问题。原结算校验和 writer 被复用；新增纯读接口承载真实的已付恢复差异，非空转发层。沿用角色事务参数与原始指纹字段符合仓库契约，不据此强推新的包装类型。

方法与核验：采用 code-review Standards 与 codebase-design 的 Seam／Locality 判断。静态 AST 解析两文件；核实已审 dream-r4 固定点精确字节、新 verifier 空基线、两端 SHA、21 项输入 SHA，以及规范化重建的 405 行 diff。普通 settle/ack 参数保持，原 ack 及其内部实现 AST 不变；六组恢复验证记录绑定候选 source SHA，另六组 ordinary binding 记录仅作为冻结输入读取。

未执行生产模块、DB、测试或 GUI；真实 producer/source CAS、共享恢复接线、真实引擎与现场客户端留给所属集成验收。本报告不评 Spec。

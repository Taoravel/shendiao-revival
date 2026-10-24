# Task terminal recovery 固定双轴记录


## Standards（r1）

# Standards

硬违反：0。依据根 `AGENTS.md` 的模块分工、`revival/ARCHITECTURE.md` 的“状态所有权／交易、奖励与跨区／必要验收”、`revival/DESIGN_AUTHORITY.md` 的来源与实测分离要求审查全部 hunk。`source/task_battle.py:355` 保留普通结算当前租约围栏；`:372` 统一核原 admission、Participant、AI、定义与终态身份；`:476` 在当前角色事务中使用明确版本的内部 witness，并保留原事件 epoch。可信 producer 与完整来源 CAS 明示为 main caller 契约，不把 DTO 自身当授权。`:431`、`:456` 的已付分支只查询当前经验、钱包和属性，不调用 reward/chain writer。新增 harness 明示 Participant、terminal、producer/consumer 为契约夹具，未越权声称真实引擎或上线完成。

判断建议：0。完整 Fowler baseline 逐项判断：Mysterious Name、Duplicated Code、Feature Envy、Data Clumps、Primitive Obsession、Repeated Switches、Shotgun Surgery、Divergent Change、Speculative Generality、Message Chains、Middle Man、Refused Bequest 均未见本增量值得报告的问题。原结算校验和 writer 被复用；新增纯读接口承载真实的已付恢复差异，非空转发层。沿用角色事务参数与原始指纹字段符合仓库契约，不据此强推新的包装类型。

方法与核验：采用 code-review Standards 与 codebase-design 的 Seam／Locality 判断。静态 AST 解析两文件；核实已审 dream-r4 固定点精确字节、新 verifier 空基线、两端 SHA、21 项输入 SHA，以及规范化重建的 405 行 diff。普通 settle/ack 参数保持，原 ack 及其内部实现 AST 不变；六组恢复验证记录绑定候选 source SHA，另六组 ordinary binding 记录仅作为冻结输入读取。

未执行生产模块、DB、测试或 GUI；真实 producer/source CAS、共享恢复接线、真实引擎与现场客户端留给所属集成验收。本报告不评 Spec。


## Spec（r1）

# Spec

实现错误1项；遗漏0项；扩域0项。独立Spec轴，不合并Standards。

**[P2] 按持久租约身份比较新旧epoch。** 规格 `TASK_TERMINAL_RECOVERY_DECISION.md` 要求：“只有有效的新当前租约……可调用新公开Task recovery Seam。” `source/task_battle.py:495` 仅以 `finished.login_epoch==epoch` 排除同租约；但 `valid_task_epoch` 明确同时接受int/str，`_owner`则通过SQL比较持久租约。现役 `npc-repair-20261024T023920Z/source/accounts.py:35,119` 把epoch存为TEXT、返回int，因此原event/admission为整数7、当前调用epoch及witness为字符串`'7'`时，所有者查询仍匹配同一条有效租约，而Python相等为false，恢复入口误当新租约。它不需要修改原event。应按与持久层一致的规范身份排除同一lease，或明确拒绝这种跨表示输入；补充同租约int/str别名负例。此问题是受信调用方Interface的规则漏洞，不是wire授权漏洞。

其余所读路径符合规格：“不能构造修改epoch的BattleFinished”由原event校验和直接复用结算落实；pending核active/当前角色资格，使用当前actor生成共同奖励证据。producer/source CAS、唯一consumer回执及outbox事务明确留main，witness不是自证权限。新paid/read_current要求相同已存终态并纯读当前XP/wallet/profile，不走旧奖励/链修复；普通settle仍要求事件epoch等于当前epoch，原ack保持原字节逻辑。

方法/验证：code-review Spec静态核已审dreamr4基线、405行patch、2文件/21inputs全部SHA及root acceptance对应裁定SHA；原ack/proof/cancel AST不变。只读取6组新Task契约及6组旧binding报告，未重跑、未访问DB或真人。数值Participant/terminal及SQL outbox是fixture；真实engine、producer/source CAS、完整恢复链/并行、shared与GUI仍未证明。


## Standards（r2）

# Standards — r2 增量

硬违反：0。沿用 r1 的标准来源与范围：根 `AGENTS.md`、`revival/ARCHITECTURE.md`、`revival/DESIGN_AUTHORITY.md` 及冻结恢复裁定。`source/task_battle.py:495` 仅将同租约判别改为 `str(finished.login_epoch)==str(epoch)`，在既有类型与当前角色事务校验之后，对齐本地 SQLite TEXT 租约身份，符合 ARCHITECTURE“每个角色只允许一个有效 login_epoch／过期回调失效”的约束；原事件不被改写，普通 settle/ack、恢复 writer 和已付纯读分支均未变化。`source/verify_task_battle_recovery.py:94` 新增真实持久 admission 上的当前租约字符串别名拒绝用例，保留原契约夹具标识，不声称真实引擎或上线验证。

判断建议：0。完整检查 Mysterious Name、Duplicated Code、Feature Envy、Data Clumps、Primitive Obsession、Repeated Switches、Shotgun Surgery、Divergent Change、Speculative Generality、Message Chains、Middle Man、Refused Bequest；本增量未触发值得报告的气味。沿用现有 int/string 租约 Interface 的局部归一比较符合仓库兼容 Adapter，不因通用 Primitive Obsession 启发式强推全项目类型迁移。新增负例复用现有 admission 与事务，无推测抽象或跨模块扩散。

方法与核验：code-review Standards＋codebase-design 的 Locality 判断。静态核实两文件 baseline 与 r1/source 精确相同，两端 SHA、21 项输入 SHA、规范化重建的 39 行 diff、两文件 AST 解析；生产源码严格只有该一行变化。六组验证记录绑定 r2 source SHA，仅静态读取该记录，未重跑红绿或 DB／测试。

r1 结论保留；真实 producer/source CAS、共享接线、真实引擎和 GUI 仍由集成验收，本报告不评 Spec。


## Spec（r2）

# Spec

本次增量新增问题0项；r1的P2已闭合，保留原历史报告。独立Spec轴，不合并Standards。

依据root裁定“只有有效的新当前租约……可调用新公开Task recovery Seam”，唯一生产变化 `task_battle.py:495` 改为比较 `str(finished.login_epoch)==str(epoch)`，与现有SQLite TEXT租约身份一致；原整数epoch及其字符串别名现在被视为同一个租约并拒绝，不修改原event/admission，也不放宽合法新租约条件。

验证器新增负例位于 `acquire_lease` 之前，传入 `str(original_epoch)` 及相应Inventory/Witness；其余admission、终态、producer/source绑定保持有效，确实瞄准同租约别名，不能由错误owner或已换lease掩盖。冻结报告包含该负例和六组契约绿灯；修前实际红灯由本批执行方报告，本审查未重跑。

`settle_task_battle_transaction`、`_validated_terminal`、原ack及新paid/read_current函数AST均与r1相同；因此本次修复未扩大普通settle的old-epoch权限，也未改变已结算当前查询允许同租约/后续租约、拒绝pending及不重复DML的范围。r1其他结论沿用。

方法/验证：code-review Spec静态核r1/source与本批baseline精确一致、2文件两端及21inputs SHA、39行patch和报告source SHA，全匹配；AST确认只改recover生产函数。未运行DB/测试、修改源文件或接触真人。真实producer/source CAS、完整engine恢复链、并行、shared/发布/GUI仍未证明。


当前r2：Standards硬0/建议0；Spec新增0，r1 P2已由实际SQLite alias红绿和独立r2审查闭合。真实engine/source CAS、shared/发布/GUI未由本Task批验证。

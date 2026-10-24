# Standards — r2 增量

硬违反：0。沿用 r1 的标准来源与范围：根 `AGENTS.md`、`revival/ARCHITECTURE.md`、`revival/DESIGN_AUTHORITY.md` 及冻结恢复裁定。`source/task_battle.py:495` 仅将同租约判别改为 `str(finished.login_epoch)==str(epoch)`，在既有类型与当前角色事务校验之后，对齐本地 SQLite TEXT 租约身份，符合 ARCHITECTURE“每个角色只允许一个有效 login_epoch／过期回调失效”的约束；原事件不被改写，普通 settle/ack、恢复 writer 和已付纯读分支均未变化。`source/verify_task_battle_recovery.py:94` 新增真实持久 admission 上的当前租约字符串别名拒绝用例，保留原契约夹具标识，不声称真实引擎或上线验证。

判断建议：0。完整检查 Mysterious Name、Duplicated Code、Feature Envy、Data Clumps、Primitive Obsession、Repeated Switches、Shotgun Surgery、Divergent Change、Speculative Generality、Message Chains、Middle Man、Refused Bequest；本增量未触发值得报告的气味。沿用现有 int/string 租约 Interface 的局部归一比较符合仓库兼容 Adapter，不因通用 Primitive Obsession 启发式强推全项目类型迁移。新增负例复用现有 admission 与事务，无推测抽象或跨模块扩散。

方法与核验：code-review Standards＋codebase-design 的 Locality 判断。静态核实两文件 baseline 与 r1/source 精确相同，两端 SHA、21 项输入 SHA、规范化重建的 39 行 diff、两文件 AST 解析；生产源码严格只有该一行变化。六组验证记录绑定 r2 source SHA，仅静态读取该记录，未重跑红绿或 DB／测试。

r1 结论保留；真实 producer/source CAS、共享接线、真实引擎和 GUI 仍由集成验收，本报告不评 Spec。

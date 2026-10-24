# Standards

**Standards 1；P0=0、P1=0、P2=1、P3=0。**

P2（文档约束）：`family_maintenance_runtime.py:78` 在容量检查前把游标推进至整页末家族；82–84行容量满时中断，尚未调度的条目已被越过。实际 scheduler 容量模拟：batch_limit=2、limit=1，初始[1,2]只处理1却游标=2；每轮新增3至8并等待前轮完成，结果处理[1,3,4,5,6,7,8]，2始终pending。持续新增时旧家族可能永久饥饿，违背 FAMILY_GUILD_HISTORY_CONTRACT:19/25 的公平恢复要求及架构的可靠背压恢复原则。游标应只推进已调度/已运行条目，容量中断不得越过未处理者。反例使用真实扫描方法及隔离目录/完成 Adapter，未冒称真实源状态集成。

重读 code-review、codebase-design、writing-for-agents，按项目标准及完整 Fowler 启发式独立审查。其余无硬标准或判断性 smell 发现；源/家族archive/ack各自单写、事务与先消费后ack、历史保留、当前成员投影和提交后展示错误隔离均未见偏差。

9候选、6基线、692依赖、647资源、6规格及精确差异哈希匹配；28脚本/162导入（161源Module加runner）核验通过，独立新增七组与原生两组通过。证据见 standards-independent/checks.json。无Git，使用第22批r2固定源。未验跨库、GUI或商业容量，未改固定源、真人库或服务。

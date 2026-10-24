# Standards

**Standards 1；P0=0、P1=0、P2=1、P3=0。r1容量越过问题已修。**

P2（文档约束）：`family_maintenance_runtime.py:74–91` 的轮次没有固定上界，只在查询为空时绕回。某家族第一源consume/ack后，游标已跨过它，其下一pending源仍须等待空查询。实际scheduler及隔离目录/跨Owner消息Adapter反例：家族1有[101,102]、家族2有[201]，容量1/批2；每轮只新增一个高ID家族，消费依次为(1,101)、(2,201)、(3,301)…(8,801)，102一直pending。待处理家族总量始终2，非持续超载。违背 FAMILY_GUILD_HISTORY_CONTRACT“有界公平目录”和架构可靠恢复要求。应固定本轮目录上界，使新到高ID不能无限延长本轮，确保旧家族后续事件获下一轮调度。

沿既读code-review、codebase-design、writing-for-agents及完整Fowler基线全量复审；其余硬标准/判断性smell发现0。独立确认原容量拒绝修复、已有任务不重复、普通末尾绕回；新增八组真实Store/Runtime及原生两组通过。9候选、6基线、692依赖、647资源、6规格与两差异/保留红灯哈希匹配；28脚本最终索引在落报告时尚未齐，未冒称全绿。

两组调度反例均明确使用隔离Adapter，不冒称源持久化证明。证据见standards-independent/checks.json及backlog-fairness.json。未验跨库、GUI、商业容量；未改固定源、r1、真人库或服务。

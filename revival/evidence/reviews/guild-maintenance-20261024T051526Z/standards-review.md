# Standards：第25批帮派维护

候选 SHA `8ebf4028b91c982be0f95e95d1febedeb6794add037592462e1df097f9eb897c`；精确对第24批 accepted source 的冻结 diff，无 Git/commit 列表。**P0/P1/P2/P3：0/0/2/1，需修复。**

文档标准问题：

- **P2 — 旧凭据被新观察限额拦截。** `guild_maintenance.py:228` 在 `_prior` 前用当前 `member_limit` 拒绝。真实 Store 提交两人观察后，将政策上限改为1，原命令重放抛 `invalid_guild_maintenance_observation`。违反 ARCHITECTURE.md“重试返回既有结果”和维护合约“政策关闭或改变后仍可重放”。固定形状/绝对上限可提前检查；当前政策限额应只约束新来源。
- **P2 — 分区间共享名额没有公平准入。** `guild_maintenance_runtime.py:27–44` 只保留分区内 ceiling。两个待办、容量1时，低分区任务跨两次扫描后失败，其空页先重置 cursor；释放名额后该分区再次先占槽。真实 scheduler.scan + Store 索引分页的8个周期只接纳 guild2，guild3持续被拒，未新增来源。违反 ARCHITECTURE.md 局部故障隔离/不同所有者独立推进及维护合约公平回访要求；需有界分区准入轮转。写入任务为受控异步失败 Adapter，此反例未冒称真实经济结算或完整周期验收。
- **P3 — 验证来源哈希指错源码。** `verify_guild_maintenance_native.py:19,173` 从重定向 OUT 对应的工作区读取源码 SHA，实际却执行冻结 source。工作区修复后重跑原候选，5组仍通过，但报告记录工作区 `db0bdf…` 而非执行源 `b0e13d…`。违反 AGENTS 每批准确记录产物/验证的要求；源码用实际 `__file__`，资源根单独管理。

Fowler 判断性 smell：未发现额外可行动项。方法：code-review 完整基线逐项审查；codebase-design 核单 Owner/事务及调度 Interface；writing-for-agents 共置证据限制。

独立核10候选、752依赖、653资源及副本、8规格、基线来源和重建diff；固定32脚本全绿及实际import哈希均核实。另独立跑维护10组、原生5组、旧解散全套；实际 Runtime 尾部 IntegrityError 向上传播且完整回滚，提交后展示 OperationalError 返回成功且重试XP仍7。证据在 standards-independent。未验证正式数值、shared接线、真实GUI、终末其他Owner清理、跨库/商业容量；未改固定源码或运行服务。

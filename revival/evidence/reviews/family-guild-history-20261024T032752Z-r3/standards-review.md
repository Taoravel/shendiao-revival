# Standards

**Standards 0；P0/P1/P2/P3均为0。r1、r2两项P2均已修复，历史证据保留。**

沿code-review、codebase-design、writing-for-agents及完整Fowler基线全量复审，项目硬标准和判断性smell均无新增发现。无Git，以第22批r2固定源、完整差异及r2修复差异审查。

独立实际scheduler与SQL page/pending/event检查确认：容量拒绝不越过条目；每轮冻结ceiling，持续新增高ID仍回访旧家族后续源；已有任务不重复，末端清cursor/ceiling后可见低ID新源；一次消费背压后原源与后续源均恢复且不重复。真实SQL查询计划均用目录covering index，无临时排序。调度检查使用隔离目录数据/消费ack Adapter，不冒称真实producer证明；另独立九组真实Store/Runtime及两组原生验证全部通过。

9候选、6基线、692依赖、647资源、6规格与两份差异/保留红绿证据哈希匹配；28固定脚本、stdout及162实际导入（161源Module加runner）全部核验，源资源未变。单写者、事务、严格前序ack、档案保留、当前成员授权与提交后展示故障语义未退化。证据见standards-independent/checks.json。

未验跨数据库、实际GUI、商业容量或live部署；未改固定源、旧候选、真人库或服务。

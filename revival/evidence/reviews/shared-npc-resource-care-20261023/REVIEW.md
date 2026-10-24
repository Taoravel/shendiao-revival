# NPC修理与宠物恢复局部接线审查

固定比较基准、文件及前后SHA256见scope.json；项目非Git，无Git提交列表。root汇总重新核对冻结current全部哈希。当前工作区全部受审文件仍匹配冻结after哈希。

# Standards

0项发现。仅审固定2文件增量：含wild的准确base对care-after；生产变更限两函数，无Git／提交列表，不外推整个working已冻结。

沿用完整code-review／codebase-design，依据AGENTS、ARCHITECTURE和NPC正式签名核查事务Seam。runtime_storage.py:565–580去掉两处临时guard后，修理显式成对注入启动规则，保留三参数纯final编码hook；资源before、耐久／费用、专用equipment_repair与paid判定仍归NPC同事务。宠恢复直接注入原settle，由领域已验证凭据决定source-only重放，未在shared另开补写事务或复制资源算法。

12项Fowler smell逐项作heuristic判断，未见有实际后果的问题；两处Adapter执行必要依赖注入，未增空抽象、第二本HP、热DDL或全局锁。

静态核对冻结diff、验证脚本及交单，未执行测试、DB、战斗、服务或GUI；不评基础wild、用户退出故障及未冻结的并行源码。实际通过结果由根独立验收，本轴未复跑。

# Spec

0项可确证缺陷、遗漏或越权。

沿用code-review独立Spec轴、codebase-design的NPC调用方事务Seam。按scope.json审固定base/current两文件；base已含wild，无Git提交列表，不将其归本批。

SPEC_SOURCE.md:13要求“显式注入启动resource_rules/equipment_attribute_rules并保留纯final hook”“去掉kind2/3/4临时拒绝”。current/runtime_storage.py:565–578准确实现，保留原三参数final编码hook，未另加source-only或跨事务补写；两恢复入口沿既有统一路由。对照NPC_RESOURCE_SIGNATURES及实际npc_repairs.repair/npc_recovery.settle，fresh修理专用equipment_repair、宠物source-only、领域已付/current及legacy-paid语义由原NPC事务维持，规则成对注入。current/verify_resource_npc_care_runtime.py覆盖对应入口、晚期回滚与迁移后旧paid例，未将脚本声明当执行证据。

仅静态审查，未运行代码、数据库、服务、战斗或GUI；未验wild整体、自动激活、六槽HP增益或商业容量。

Standards 0项、无最高问题；Spec 0项、无最高问题。两轴仅静态；root另实际独立运行对应资源Seam/真实NPC Owner检查。未将结果外推wild整体、用户退出故障、GUI或商业容量；未部署或操作真实角色。

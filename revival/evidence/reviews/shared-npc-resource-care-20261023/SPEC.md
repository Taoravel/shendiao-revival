# Spec

0项可确证缺陷、遗漏或越权。

沿用code-review独立Spec轴、codebase-design的NPC调用方事务Seam。按scope.json审固定base/current两文件；base已含wild，无Git提交列表，不将其归本批。

SPEC_SOURCE.md:13要求“显式注入启动resource_rules/equipment_attribute_rules并保留纯final hook”“去掉kind2/3/4临时拒绝”。current/runtime_storage.py:565–578准确实现，保留原三参数final编码hook，未另加source-only或跨事务补写；两恢复入口沿既有统一路由。对照NPC_RESOURCE_SIGNATURES及实际npc_repairs.repair/npc_recovery.settle，fresh修理专用equipment_repair、宠物source-only、领域已付/current及legacy-paid语义由原NPC事务维持，规则成对注入。current/verify_resource_npc_care_runtime.py覆盖对应入口、晚期回滚与迁移后旧paid例，未将脚本声明当执行证据。

仅静态审查，未运行代码、数据库、服务、战斗或GUI；未验wild整体、自动激活、六槽HP增益或商业容量。

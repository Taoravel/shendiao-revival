## Standards

结论：文档规范违例 0；可行动的 Fowler smell 0。

固定点为真实字节，非 Git 提交：发布 `npc_repairs.py` 3cc→候选 e648，新探针为空基线，两份原冻结检查只改请求栏目（已穿检查另改描述标签）。已完整审阅四文件 diff；manifest SHA 与指定的 1e022635… 一致。

采用 code-review Standards 方法，对照冻结 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY、GLOSSARY/ADR 及全部十二项 Fowler 启发式；仓库未发现 CODING_STANDARDS/CONTRIBUTING。生产增量将原生栏目准入、物理位置校验和历史凭据 token 的差别留在所属 Module 内；没有新增共享写者、全局串行器、热配置读取或跨所有者网络发送。已有交易、租约、资源检查及最终编码仍沿原 Interface 执行。解析 legacy4 后于交易中区分已有付款和 fresh，不等于新增付款权限；局部 receipt token 保留不构成全局栏目映射。

独立实际运行六项检查全部通过：`baseline_red`、`native_compat`、`carried_transactions`、`carried_runtime`、`known_native3`、`equipped_native3`。每项前后校验 22 个本地和 3078 个外部固定输入。baseline_red 证明旧版明确失败，不计功能绿灯；跨进程真实旧 Owner 凭据、新租约当前恢复、fresh4 拒绝、真实加密 native3，以及携带回滚/旧租约和两类资源检查均有独立结果，位于 `verification/standards/`。

范围限于本片 NPC 候选及声明的测试数据适配。Asset 网络刷新仍旧4、最终兼容 policy/Asset Interface、商店查询、共享接入、部署及 GUI 均未由本审查完成；未改生产、政策、真实库或服务。

Standards：0 项，最严重问题：无。

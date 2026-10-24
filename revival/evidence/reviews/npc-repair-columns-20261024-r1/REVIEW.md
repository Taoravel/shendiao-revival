## Standards

结论：文档规范违例 0；可行动的 Fowler smell 0。

固定点为真实字节，非 Git 提交：发布 `npc_repairs.py` 3cc→候选 e648，新探针为空基线，两份原冻结检查只改请求栏目（已穿检查另改描述标签）。已完整审阅四文件 diff；manifest SHA 与指定的 1e022635… 一致。

采用 code-review Standards 方法，对照冻结 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY、GLOSSARY/ADR 及全部十二项 Fowler 启发式；仓库未发现 CODING_STANDARDS/CONTRIBUTING。生产增量将原生栏目准入、物理位置校验和历史凭据 token 的差别留在所属 Module 内；没有新增共享写者、全局串行器、热配置读取或跨所有者网络发送。已有交易、租约、资源检查及最终编码仍沿原 Interface 执行。解析 legacy4 后于交易中区分已有付款和 fresh，不等于新增付款权限；局部 receipt token 保留不构成全局栏目映射。

独立实际运行六项检查全部通过：`baseline_red`、`native_compat`、`carried_transactions`、`carried_runtime`、`known_native3`、`equipped_native3`。每项前后校验 22 个本地和 3078 个外部固定输入。baseline_red 证明旧版明确失败，不计功能绿灯；跨进程真实旧 Owner 凭据、新租约当前恢复、fresh4 拒绝、真实加密 native3，以及携带回滚/旧租约和两类资源检查均有独立结果，位于 `verification/standards/`。

范围限于本片 NPC 候选及声明的测试数据适配。Asset 网络刷新仍旧4、最终兼容 policy/Asset Interface、商店查询、共享接入、部署及 GUI 均未由本审查完成；未改生产、政策、真实库或服务。

Standards：0 项，最严重问题：无。

## Spec

结论：缺失/部分实现 0，越界 0，实现错误 0；本片所属候选通过 Spec 审查。

方法：按 code-review 独立 Spec 轴核完整四文件 `changes.diff`，逐项对照冻结的 `NPC_REPAIR_COLUMN_CANDIDATE.md`、root 已付兼容原则、27 组原生来源和诊断记录。固定点是发布版真实 3cc 字节、新探针空基线及两个原 harness 的输入差异；没有 Git 提交或伪造引用。manifest SHA 保持 `1e022635c8393e1eb8947c14c3e6eb7b72cf347f52fd517a2e3900901b35fb54`。

“fresh请求只授权column1携带、column3已穿”由交易内真实 owned item 位置判断实现；可解析 legacy4 仅供查询已有匹配凭据，fresh4 在随机、扣款和资产修改前拒绝。“该token不是Inventory栏目”对应私有 fingerprint 中保留历史4，未改背包、商店或存档。旧 paid4/new3 的相同物理意图保持同一凭据，换物品冲突拒绝；已付分支继续只取当前状态。

独立运行六项固定检查：`baseline_red`、`native_compat`、`carried_transactions`、`carried_runtime`、`known_native3`、`equipped_native3`，全部终态符合预期，每项前后校验22个本地和3078个外部输入。baseline_red 是准确重现旧版失败，不计功能绿灯。候选实证含原 Owner 生成真实旧凭据、新进程/新租约恢复、fresh4拒绝、加密 native3修理、物品变更冲突、后续修理/脱装/再损耗的 current-only，以及携带栏事务回滚、人物资源保持和重连。两处旧测试仅把请求输入4改为已证3，另同步一处描述文字，期待值未放宽。

范围边界与规格一致：旧 Inventory 网络刷新仍为4；Asset Interface、商店 query4、最终兼容 policy、共享候选、部署及完整 GUI 未验证。本报告不批准这些能力或生产启用；审查未改生产、政策、真实库或服务。

Spec：0项，最高严重程度：无。

总计：Standards 0（最严重：无）；Spec 0（最严重：无）。

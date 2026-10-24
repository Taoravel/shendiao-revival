# Spec

最终6文件195行：0项可确证缺陷、遗漏或越权。

沿用code-review独立Spec轴、codebase-design的资源/钱包事务Seam。最终12个base/current哈希全匹配（新增base为空）；非Git，无提交列表。

current/evidence/NPC_ROLE_HEALING_DECISION.md:9明确“该cause只是数值层允许值，不赋予NPC资格或收费权限”。role_resource_plan.py:110–122仅新增冻结npc_heal原因，中央政策仅增cash专用npc_role_heal，旧revision/receipt保持。既有上限、无复活、完整before/CAS与paid当前值合同未改。

最终微增量design/npc-role-healing-v1.json:16增加数值fee_coefficient=30，与:19“current authoritative ordinary role level times30”一致；等级1..155未改，费用不需从label解析。其余沿前次审查，不重复全审或测试。

verify_role_resource_healing.py明确npc_admission_or_full_fee_rule_verified=False。仅静态审查，未运行代码、DB、服务、GUI或战斗；294资格、死亡准入、满资源收费、NPC/shared与发布由后续领域验收，不冒称原服完整事实。

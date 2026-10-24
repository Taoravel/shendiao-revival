# Spec

0项可确证缺陷、缺失或越权。

沿用code-review独立Spec轴与codebase-design，以调用方事务Seam核对固定2文件增量；基准按scope.json，无Git提交列表。

Spec ROLE_RESOURCE_STORAGE_INTEGRATION.md:61要求“False才允许来源同步，True只严格当前组合读取”“精确未迁移返回None”“完全无来源变化不写receipt”。冻结current/role_equipment_storage.py:139–153符合：类型先验，资源读取仅捕获ResourceNotInitialized；已迁移角色重算实际totals，重放严格combine，fresh走inventory_change及完整CAS，无变化直接返回；哈希前缀独立，未创建profile。沿已审source_only政策，同caps/同成长才能推进来源且保持HP/MP/version。

领域payload与真实replayed是可信调用方前提，未误报为客户端授权。仅静态审查，未运行测试、服务、真实库、GUI或战斗；未验并行消费者全流程接线。

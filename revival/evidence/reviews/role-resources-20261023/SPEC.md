# Spec

结论：本批 foundation 未发现可确证的 Spec 缺陷或越权行为（0项）。

固定基准为 `runtime/deployments/20261023T063445Z/source`，待审对象为本目录 `current/` 与 `changes.diff`；项目无 Git，因此未执行提交/merge-base 流程。以 `current/design/role-resources-v1.json`、ROLE_RESOURCE_TRANSITION_DECISION、ROLE_RESOURCE_EQUIPMENT_SEAM_AUDIT 及 ARCHITECTURE 为依据。

已按要求核对：

- “one persisted role resource state”与“never permanently dual-write another HP/MP ledger”：`role_resource_storage.py:38–45,105–110`只新增来源/凭据表，当前值仍仅写既有 vitals；`role_attribute_storage.py:65–75,107,124`围栏阻止迁移后的旧读取/写入与成长路径继续使用裸身资源契约。
- “known current HP/MP retained then clipped”：`role_resource_storage.py:128–148`比较完整已知旧值，验证当前来源，在调用方事务一次迁移；同意图重试返回当前资源，未构造未知角色默认血量。
- “projection provenance-only changes retain resource version and still require full-snapshot CAS”：`role_resource_plan.py:123–126`区分数值变化与来源变化；`role_resource_storage.py:171–187`比较完整 before，并条件写 vitals 与来源。
- “paid command replays never repeat a cap change or heal”：`role_resource_storage.py:165–170`核对同请求指纹后重读当前值；`role_resource_plan.py:140–184`按成长、装备、治疗分别限制版本来源、裁剪和死亡行为。

方法：采用 code-review 的独立 Spec 轴，结合 codebase-design 的 Interface/Seam，沿真实存储、装备投影和旧调用方核对契约；未将可信内部 caps 输入误报成客户端可伪造漏洞。

验证范围：固定源码静态审查，未运行大回归、真实库、服务、GUI或战斗。药品/客栈/成长消费者迁移、最终 profile 编码、六槽运行时与实际激活属于下一阶段，本结论不证明这些已完成。

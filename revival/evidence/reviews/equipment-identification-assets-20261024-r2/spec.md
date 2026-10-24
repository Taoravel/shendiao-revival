## Spec

沿用完整在上下文的 `code-review` Spec 方法：冻结 diff 对照 NPC 单一政策／决定文档，静态审查与实际验证分别举证。范围为生产三文件及新增四测试；NPC 生产仅为只读依赖，未读取 Standards 报告。

输入验证：R2 `changes.diff` SHA256 `8839a50cdc1669f84ce045721b1a3035ede1373fb55480121ebdac32c2b4b752` 与 manifest 一致；7/7 current 审查文件、3/3 base 文件逐一匹配。原政策、决定及架构／来源边界文件 SHA 与 R1 相同；沿用同一已证明 BASE，不虚构 Git 历史。

(a) 缺失／部分需求：0。政策 `design/npc-equipment-identification-v1.json:23–24` 要求“already persisted…explicit_known_clean_instance”及“Preserve slot, binding, quality, condition”。`inventory.py:1230–1266` 仍检查当前租约、库存版本、携带量1、普通非特殊模板、已知color1、完整实例及持久来源；NPC继续唯一持有ticket／报价／扣费／领域凭据。

(b) 范围扩张：0。`equipment_detail.py:94–99` 的 `fixed_clean_unidentified` 仅集中原有固定结果判据，读门禁与写前各自调用；未改变默认生成、存量、随机属性或共享激活。政策 :39 的隔离实现／临时验证边界仍保持。

(c) 看似实现但错误：0。政策 :34 明确“revision+origin+full before JSON and expected inventory_revision；…identified0 to1 only”。`inventory.py:1250–1266` 的完整basis比较及库存CAS和 `equipment_detail.py:147–162` 的原JSON／来源CAS保持；新helper仍精确要求identified0、prefix1、score0及canonical基础map。公开同事务当前tips与cash-only追加purpose未改变。

实际验证：在 R2/current/revival，以指定Python及UTF-8独立运行四个 `verify_equipment_identification_{cas,currency,source,npc_compat}.py`，全部退出0／PASS。验证反馈包括六槽原生详情字段保留、版本／原JSON／旧租约拒绝、旧币种凭据兼容、实际钱包／唯一source／NPC凭据及晚期编码全回滚、严格只读已付重试与后来移动保留。证据仅生成于冻结 current/revival/evidence。

未验证：真实GUI、共享加密入口、部署、商业数据库及容量；不据此判定该资产片缺失。

计数：缺失／部分0；范围扩张0；实现错误0；Spec总计0。

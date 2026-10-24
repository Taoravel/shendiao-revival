## Spec

使用 `code-review` 的 Spec 轴：以冻结 `changes.diff` 为固定比较输入，逐项核对本地单一政策及决定文档，不依据测试通过推定正确。审查仅生产三文件及新增四测试；NPC 生产代码作为只读调用依赖。非 Git，无虚构提交或 tracker。

输入验证：`changes.diff` SHA256 为 `c24c933cef06f02f0ae3a8e0dbbdf8aa9c6a6e206474c18d6cf4f07078f77f13`，与 manifest 一致；7/7 current 审查文件和3/3 base 文件 SHA 均逐一匹配。基线来源采用 manifest 记录的前批 inventory 与真实发布 BASE 证明。

(a) 缺失／部分需求：0。

(b) 范围扩张：0。政策 `design/npc-equipment-identification-v1.json:39` 明确授权隔离领域／临时存储验证；完整随机结果、共享收费接线及部署不属于本片完成要求。默认生成值、存量及旧币种政策版本未改。

(c) 看似实现但错误：0。静态核对政策 :23–24 的“already persisted…explicit_known_clean_instance”与“Preserve slot, binding, quality, condition”，以及 :34 的“revision+origin+full before JSON and expected inventory_revision”：`inventory.py:1230–1268` 重读当前租约／完整实例和库存版本，限定携带量1、普通非特殊模板、已知固定0结果；`equipment_detail.py:141–157` 按来源／修订／原JSON做0→1 CAS，其余字段保留。`inventory.py:1270–1280` 在调用方事务编码当前详情；cash purpose 仅追加于 `design/currency-v1.json:12,20`。NPC稳定身份、报价、扣款及专用凭据仍由其所属模块承担。

实际验证：在冻结 current/revival、指定 Python、UTF-8 环境分别运行四个 `verify_equipment_identification_{cas,currency,source,npc_compat}.py`，全部退出0／PASS。反馈覆盖原解析器与六槽固定字段、完整来源／版本围栏、默认与历史凭据不变、实际钱包／source／NPC凭据故障及晚期编码全回滚、严格只读已付重试。生成证据留在冻结 current/revival/evidence。

未验证：真实客户端GUI、共享加密入口、部署、商业数据库与容量；未将它们计作该资产 slice 的缺失。

计数：缺失／部分0；范围扩张0；实现错误0；Spec总计0。

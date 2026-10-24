# Standards follow-up

2026-10-24。沿用已读 `code-review` Standards 方法及根 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY、GLOSSARY 的约束。只读追加审查新增伴随门槛，不改原 standards.md。

结论：**0 项发现**。

审查固定文件 `verify_world_portal_source_binding.py` SHA256 `857c64f3343140cd24bb85da334d2f0ae99bed632373e0cd2de4942df13a2c3a`，已实际核对。门槛直接从原 PFS 按完整属性和有序 goto 行构造期望值，随后与准确候选 catalog 全行比对；不将相同数量当内容相等。对副本修改一个真实 destx、保持行数的反例调用同一 compare，异常仅记为反例成功，不修改正式源或削弱正常比较。

静态核对 Parser 的实际路径、全生产 manifest 前后哈希、catalog 和原包前后哈希、casefold 资源查找及歧义检查。输出明确限制为原行绑定，不把坐标单位、可达性或客户端显示一并声明完成。无正式数据库/共享文件/运行服务访问，也未增加状态所有者或锁；无需修改业务架构。

只读核对 source-binding.json：脚本哈希与冻结脚本相同，304 张地图、142 个 goto 表、6275 行原记录匹配，same-count 反例被 `Original goto rows differ` 拒绝，inputs_stable 为 true。此为现有执行报告核对，未独立重复运行；不代替父任务的 212 对加密传送执行或 GUI 验收。仅新增本文。

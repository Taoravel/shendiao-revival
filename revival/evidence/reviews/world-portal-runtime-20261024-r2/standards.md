# Standards

2026-10-24。按既有 `code-review` Standards 轴、根 AGENTS/ARCHITECTURE/DESIGN_AUTHORITY/GLOSSARY 及 Fowler 基线，审查冻结实际 before→current。before SHA256 `c902399b21ddf36ce36987d41e56b097850b54e1d226b55f5136679755eac399`；current SHA256 `f3a0cb22a90a2a44d8dabd1195544b71c5c5da1386f14d96265552e2712d3dcd`，均实际核对。

结论：**0 项发现**。

实际检查：完整差异仅调整 expected_npcs 的原包查找及记录字段。新路径使用不歧义 casefold 索引；文件存在仍读原包、BXML 解码并记录 entry/SHA，缺失则返回严格空期望。真实 ADD_USER_SCREEN 消息仍逐批原 decoder 解码且 records==expected，不会跳过零 NPC 图，也不会容许额外 NPC。与 recover_world.py 的原恢复语义一致：npc_placements 初始为空，原 npc.xml 缺失时保持空列表。异常未被宽泛吞掉，无生产碰撞或地图政策变动。

只读核对新 pilot：1230→1231 的零 placements 与 1007→1014 的72 placements 均通过，后一项记录原表 entry/SHA；报告生产1442项及输入稳定。此为报告核对，未独立重复运行或读原包，也未把两组推广为212组全量结果。

原 r1 整批作业、原源码和红结果须保留。联合覆盖只有在逐对清单去重、准确 manifest/原包一致、采用版本/报告可追溯且失败对完整复验后才能成立；不能将 r1 的整批失败重写成单次全绿。父任务明确采用透明联合记录，符合项目证据分层要求。本审查未核验最终联合产物、实际客户端或正式服务；仅新增本文。

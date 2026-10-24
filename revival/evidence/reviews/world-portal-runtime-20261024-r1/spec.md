# Spec review

2026-10-24。方法：按 `code-review` 的 Spec 轴，对空基线到新增冻结脚本逐段核对父任务给定验收规格；无 Git 提交历史，不伪造 diff。只读核对源码、准确发布依赖和封存 pilot；未改生产、服务或数据库。

冻结对象：`verify_world_portal_runtime.py`，SHA256 `c902399b21ddf36ce36987d41e56b097850b54e1d226b55f5136679755eac399`。

## Findings

- **[P2] 原 portal 配置与候选 catalog 尚未形成本次证据绑定。** 规格要求“从原 map.pfs 的6275portal格227directedpairs中重新生成212普通原配置跨图对”。冻结脚本95–115行直接遍历 `catalog[mid]['portals']`，243–244行的 `maps()` 实际由准确候选 `world_catalog.py` 读取 `catalogs/world.json`；原 `goto.xml` 没有在本脚本重读或逐行比对。6275/227/212计数及候选 manifest 只能证明数量与候选稳定，不能证明各边仍等于原始入口。历史 `world-special-portals-audit.json` 有全行一致结果，但该报告没有记录所用 catalog 文件哈希，也未由本次报告绑定。应补一次对准确候选 catalog 的原 config/goto 全行独立核对，记录原包、catalog与脚本哈希，并把结果与本次212报告关联；或直接将该前置核对加入下一冻结版本。此项是证据绑定缺口，不是已证明某条边配置错误，不需要打断正在运行的作业。

其他所审规格未见缺失：逐对临时DB、显式实际源Owner采用、legacy未知实例不冒称完整存档、真实加密MOVE/STOP/发送完成、目标scene及NPC原生解码、位置版本/完整地址存储、同及冷runtime重登、四字节心跳均有对应断言。目标NPC配置名来自准确候选冻结定义，原始布置来自重新读取的目标 `npc.xml`。15特殊、完整路径、客户端ACK和GUI均明确未验，不把212代表扩大为全6275格。

验证：冻结SHA已重算相符；pilot两组 `all_passed/inputs_stable/production_stable=true`，3个原生NPC批次。完整212作业本轴未等待终局，也未独立复跑；不宣称全量通过。

Spec findings: **1 P2**。

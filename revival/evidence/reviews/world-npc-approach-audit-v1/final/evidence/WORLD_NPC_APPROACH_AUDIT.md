# 全摆放交互站位审计

2026-10-23。当前正常角色状态0→mask1；距离规则唯一来源 `design/npc-interaction-v1.json`。本批只增加离线审计与证据，不改变生产规则、原NPC坐标、碰撞、共享入口或运行服。

## 结论与适用范围

3443处原摆放、285张非空地图全部完成检查。3294处在当前交互圆内存在合法整数站位，并通过 `NpcScene.spawn/interact` 公开 Interface；149处在32像素圆内不存在合法整数站位。后149处涉及14张地图，不能通过加大寻路搜索预算满足当前条件。这里没有从某个角色起点寻路，前3294处仍可能因不连通、自动停靠位置或玩法资格失败；所有 `Location` 都是明确的隔离审计夹具，不代表真实角色到达。

血手印1006/p13/10498按已裁定的48规则，最近合法点1668/1008、距离平方1444（38像素），当前领域访问校验通过；原摆放仍1668/970。与此前32圆无解的原始研究不冲突。共享入口是否注入规则、自然读条/私有入场和客户端画面不在本审计范围。

149处中没有 `catalogs/tasks.json` 的主线mission直接target引用；这只排除这一种引用，不能据此宣布不需要交互。其中96处原 `npctype=51`，其余类型/隐藏标记逐行保留；本批没有把类型号猜作景物或活动语义。改用mask8的纯诊断也仅2处有圆内站位，不能以此为149处统一换角色状态。128像素内最近合法点只是诊断；未找到时不代表全图无合法点，不会生成新半径政策。

## 可复跑证据

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/audit_world_npc_approach.py
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_npc_approach_audit.py
```

`world-npc-approach-audit.json` 保存全部原身份、坐标、规则、站位或无解分类、主线直接引用、诊断mask8/128范围与输入哈希。启动重读原map.pfs的npc.xml/maze.dat及config.pfs的cnpcconfig，验证PFS长度/CRC、全部摆放顺序/属性和完整定义快照；源条目哈希附报告。输入执行前后必须稳定，否则拒绝形成结果。

审计将每个clear的16×16格与地图合法边界相交，取NPC到该整数矩形的最近点；覆盖完整距离圆涉及的每个格，因此空结果覆盖圆内所有整数位置。独立验证器另逐像素枚举，不调用矩形选择函数：3443处、11052590个圆内整数像素全部一致；149处的mask8诊断也逐点核对，2处有解。独立报告 `world-npc-approach-audit-independent.json` 绑定实际输入、审计报告与验证器哈希。此验证证明审计几何一致，原maze谓词依据已有原指令差分，不冒称本批全量执行x86。

## 后续决策与验收

检查某处不可交互时，先按完整map/placement/NPC身份读审计行，再核其原玩法用途、当前地图/角色状态及原自动接近消费者；按 `DESIGN_AUTHORITY.md` 由主策划逐处或按已证明共同机制裁定。NPC窗口维护唯一距离规则，主集成维护启动注入。恢复完成要由真实Owner处理正常移动及当前实体访问，再以客户端验证自动走近与交互；审计绿不能替代这些条件。全量地图目标仍未完成。

方法：diagnosing-bugs把血手印已有“目标圆无解”反馈扩大为有限全量审计；research优先重读原PFS；codebase-design只消费现有公开NPC Interface，不新增热路径或状态所有者；writing-for-agents把必要条件、证据与未验范围共置。无生产改动，不声称对本审计采用功能TDD。

# 自然嘉兴至血手印：当前交互范围内无可站立点

2026-10-23。原集成 `verify_prologue_touch_runtime.py` 先自然执行intro/master/装备/车夫/嘉兴100160前缀，然后从实际 `(1006,360,2264)` 向原10498/placement13 `(1668,970)` 接近，现有 `check_birth_site` 在state0/mask1、radius32、max100000下实际红：no_witness、visited44928。root独立原反馈见 `bloodmark-approach-root-baseline.json`。没有改角色位置、NPC坐标、半径或mask。

父世界窗口重新从原map.pfs CRC读取 `map_1006_jiaxing/maze.dat`，SHA256 `6f81a7407738d6ce9b7ca167c82c28849dea1db12e7f2aa7fe1285e747698351`，独立穷举NPC欧氏半径32内的全部逻辑整数像素：mask1 clear点为0。再对全图每个clear cell的逻辑像素矩形取精确最近点，最近 `(1668,1008)`，平方距离1444、距离38、cell `(104,63)`。结果 `world-bloodmark-approach-parent-observation.json`。

因此当前32像素资格不可能靠寻找另一条合法终段满足，不能把这次红只当BFS预算不足或格中心采样漏路。它也不证明原客户端完全不可接近；原NPC锚点、接近/自动寻路和服务器交互距离语义仍须一手核验。距离38是当前maze几何事实，**不是擅自采用38/48/64作新政策的授权**。

后台research已完成，父任务另独立运行 `verify_world_bloodmark_route.py` 退出0：3209个圆内像素均阻挡，22个覆盖格代表点逐一原6284f0核验；原pixel wrapper/kernel从自然source到附近道路输出 `(1032,1560),(1672,1016)`，773展开，与port一致。诊断折线再接精确最近像素 `(1668,1008)`，三段原DDA均0；最后8像素段明确是附加诊断，不是wrapper输出。source直连最近像素的原DDA为1，不能用直线瞬移代替。完整原采样见WORLD_BLOODMARK_ROUTE_RESEARCH及world-bloodmark-route-verification.json。

研究脚本的all_passed表示上述诊断成立，radius32_witness_exists仍false，不表示现32自然流程已通。主策划正在单独核原交互语义并准备局部规则，世界不并行修改world_npcs或另造距离绕过。本批未改共享、政策、原资源或实际角色。

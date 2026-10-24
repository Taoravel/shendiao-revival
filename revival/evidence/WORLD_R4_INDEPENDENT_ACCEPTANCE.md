# World 对第四版准确发布的独立核验

2026-10-24。候选/发布 `runtime/deployments/world-collision-20261023T204238Z`，GameRuntime SHA34f0b6dc6d7cf2d4fb1ddfb1e46be0ba3cad65ae9b61cff581dc33aba06a52bc，runtime_movement SHA0594837c886bb2902d3fd03476d5b9ca9a56a8d17bd70089513e1592c268f444。

World本批独立执行，不借用旧候选绿灯：

|报告|实际范围与结果|
|---|---|
|world-late-finalize-membership-r4.json|相同旧回执反例真实由r2/r3红转绿；空源幂等保持，新租约domain/cache/公开location均保持|
|world-movement-delivery-boundaries-r4.json|实际加密earlyACK先joined，drain前拒绝，drain后clear允许，墙内CHECK/STOP拒，存档/version不变，新epoch重登与心跳绿|
|world-resource-runtime-r4-pilot.json|1006/1404普通与特殊子集，加密入场/NPC原解码/同格合法一步/重登绿；候选manifest全部1442生产文件和原包前后稳定|
|world-scene-delivery-typed-barrier-r4.json|同候选的真实清理/pin路径，显式synthetic角色/目录/dispatch/transport六例绿，pending0、公开空槽64|

另外只读解析 main 的46项发布检查，全部returncode0；其同一候选全302报告位于harness/workspace/evidence/world-collision-all302-runtime.json，确认302可用图/3443配置NPC/294原decoder批次、输入与生产文件稳定；实际GameRuntime路径、SHA及candidate manifest SHA均与本r4一致。是World独立核对main全量结果，不宣称World重复执行了r4全部302。

只读核全部1442生产文件实际SHA与manifest逐项一致，当前启动记录的445项完整Python集合恰等于该manifest内Python集合；不只挑几个模块。结构化证据 `world-r4-independent-acceptance.json` 含原报告和启动记录哈希。

OS最初观察PID35568正式发布；随后再观察时35568已退出，未将一次缺口误当成永久故障或擅自重启。动态读取deployment记录和实际唯一监听发现main已以detached方式在同一r4 runner启动PID12512；重新核其445启动集合和监听归属通过。实际OS证据 `world-r4-listener-observation.json`，观察UTC2026-10-24T02:30:46Z，127.0.0.1:28993唯一PID12512。main的初次deployment-verification仍记原35568，保留历史，不修改其seal。旧恢复BASE3396和staging48572不再当当前进程。

因此可进入首轮真人测试：重新登录出图、点击移动、NPC对话、新手引导、切图。已由main唯一发布，World没有启动/停止服务、打开游戏、登录真人、访问正式socket/数据库或改存档；native GUI、原开场画面及整段交互未由以上离线/只读证据验收。

正式AI/所有怪物战斗、多人AOI、NPC全部模型/隐藏/方向、原1302/1307缺图、特殊传送分支、完整跳跃/连续轨迹及容量仍未完成。本轮成员绑定witness和Interface方案另见WORLD_ROLE_BINDING_INTERFACE_DESIGN，尚未实施或自动进入本发布。

方法：diagnosing-bugs使用同一历史回执反例确认修复；准确source/manifest/启动/OS分层核对；codebase-design保留domain单一权威与runtime Adapter修复的边界；原有验证工具Spec P2关闭不等于真实游戏验收。整个目标保持active。

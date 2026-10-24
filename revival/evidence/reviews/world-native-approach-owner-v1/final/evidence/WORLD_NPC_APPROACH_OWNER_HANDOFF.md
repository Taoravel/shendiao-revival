# 原生自动接近报文到实际角色/地图入口

2026-10-23实施，2026-10-24收口。`verify_world_npc_approach_owner.py` 已实际exit0，报告 `world-npc-approach-owner-verification.json`。以正常创建及开场、师父卡/武器/装备、车夫、嘉兴说书人的真实加密Owner链建立角色和任务，血手印接近阶段没有直接写角色位置、任务或私有检查点。

## 实际执行

CPU密集x86执行先于async运行时建立。复用WORLD_NPC_APPROACH_MOTION中的公开原入口1142620及同一actor，第二随机分支取radius3/方向1；当前原maze、原纠正/寻路/到达/STOP/Visit保持原指令。初始NPC Scene夹具的key在导航前设为当前运行时为原1006/p13分配的4320737099789，其余角色/地图/位置字段沿研究夹具；不是事后重写Visit线包。

原生成的消息依次为3个MOVE、STOP、CVisit。MOVE端点984/1608→1592/1080→1624/1016；STOP带原生成的history360/2264、984/1608、1592/1080。Visit在原consumer自然构造后由原e52020 marshal得到`000003ee0000000d`；无host拼移动history、STOP体或访问body。输入另存 `world-npc-approach-owner-native-input.json`。

角色经正常任务到1006/360,2264后，显式隔离启用prologue_touch，实际恢复100106 active；将以上原报文逐条送进同一Peer的RC4/MPPC/ConnectionOwner/RoleOwner/MapOwner。逐条记录事件及当前位置，未见gameplay_rejected。STOP实际保存1006/1624,1016，随后原Visit打开100106的原ready3菜单；退出并重登保留该停点，无战斗。最终点到原NPC欧氏距约63.66，旧48圈不兼容，当前冻结v2离散判据准入。主策划规则而非本脚本授予服务端距离条件。

报告绑定11份源码/政策执行前后稳定SHA；它是该源码结果，不等于运行服包含这些字节。世界没有改shared或启动游戏/服务。

## 范围与保留

前置新手任务链复用已有正常Owner验证，那里用原clear报告作为手工见证输入；仅本批血手印接近使用上述原自动导航/actor产生的MOVE/STOP/Visit。本批没有运行原mouse/完整App frame、Main定时CHECK、实际渲染、Scene真实注册/重复模板选择或真人客户端。Scene模板查询仍为明确Adapter。原Visit后opaque0xc0fa7仅保留原研究观察，不在本检查中赋义或投递。

本检查止于打开血手印菜单及STOP重连，不提交读条、不进入梦境或执行后继战斗；这些各由真实完整剧情/私有图共享检查证明。它也不证明所有NPC、随机组合、动态障碍、速度/时钟或商业负载。

方法：research执行第一方原指令；diagnosing-bugs把上批原选点接至真实报文/服务器反馈，后续原移动确实把墙内候选纠正，更新之前不能凭中间点认定卡死的判断；codebase-design保持native生成、连接编码、角色、地图与持久化的既有Seam；writing-for-agents将夹具及原生产行为共置。

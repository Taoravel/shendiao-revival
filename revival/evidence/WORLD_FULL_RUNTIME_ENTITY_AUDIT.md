# 全量运行时地图实体边界审计

2026-10-24。按根AGENTS、ARCHITECTURE、DESIGN_AUTHORITY及Matt Pocock research/diagnosing-bugs/codebase-design执行。根窗口负责302资源图的真实加密GameRuntime登录/投递/微小移动/重连；本批只审计其边界，不把显式初始checkpoint称作自然入口或完整剧情。没有改root新脚本、生产、shared、政策、PROGRESS、真实库或运行服，没有GUI、真人或战斗。

初始仅授权本文；根随后明确授权独占[verify_world_runtime_collision_probe.py](../verify_world_runtime_collision_probe.py)及其结构化结果，用于真实MapOwner碰撞接线缺口的红反馈。未修改任何旧codec/验证。

## 已复现、应与302图正向结果分开报告的缺口

**当前GameRuntime地图工厂没有给WorldDomain注入maze，运行时移动命令也没有传trusted movement_state；它会接受bounds内的原阻挡目标。** 302图各选一个clear格做+1px成功，只能证明该路径上的bounds、版本、投递/checkpoint/重连，不能证明运行时已经执行原网格碰撞拒绝。

第一方当前源码链：

- `game_runtime.MapOwner.__init__`约126–128行：`WorldDomain(address,catalog,capacity=...,transfer_capacity=128,mailbox_capacity=64)`，未传maze。
- `world_owner.MapOwner.__init__`170/176行：maze默认None并原样保存。
- `game_runtime.MapOwner.handle`约212–216行：`MoveCommand(current,...,kind,body)`未传movement_state。
- `world_owner._move`约559行将`self.maze`和`command.movement_state`交`plan_movement`。
- `world_movement.plan_movement`仅在`maze is not None`时检查显式state/mask和节点。当前因此只执行bounds判断，不是原碰撞代码算错。

### 确定性公开反馈

[默认安全红](world-runtime-collision-probe.json)、[精确缺口复现绿](world-runtime-collision-probe-gap.json)。三例分别建立实际`game_runtime.MapOwner`，经真实SerialOwner执行join、move_for_encounter、location；对照另一个显式原maze/state0的WorldDomain。原1006 `maze.dat`从PFS重读并CRC验证，SHA256=`6f81a7407738d6ce9b7ca167c82c28849dea1db12e7f2aa7fe1285e747698351`，384×296；源`360,2264`原byte8、mask1可走且bounds合法。

| 目标 | actual runtime结果 | version/位置 | 显式原maze/state0 Domain |
|---|---|---|---|
|361,2264，同格clear|接受|2 / 361,2264|接受|
|1664,960，原byte11|**接受**|2 / 1664,960|拒绝`Movement enters blocked maze cell`|
|32767,32767，bounds外|拒绝bounds|保留1 / 360,2264|拒绝bounds|

默认断言要求第二例拒绝并保留源/version，实际exit1（约2.14秒）；`--expect-gap`要求精确缺口且正例/bounds反例均正确，实际exit0（约1.95秒）。报告先于断言落盘，含实际导入路径、源前后稳定性、probe/原maze哈希。未向actual factory强注入state0来假装已接线。

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_runtime_collision_probe.py
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_runtime_collision_probe.py --expect-gap --report revival/evidence/world-runtime-collision-probe-gap.json
# 私有候选可加 --runtime-source <源目录> --report <独立路径>
```

也可`await check()`取得观察，再`assert_expected(report)`要求安全；观察函数本身不把缺口当PASS。identity、初始Position与普通1006场景前提是明确in-memory可信fixture；没有登录、数据库、RoleOwner/wild_move或battle调用。这里的原生state0来源是[WORLD_SCENE_MOVEMENT_STATE_RESEARCH](WORLD_SCENE_MOVEMENT_STATE_RESEARCH.md)已证成功普通A0分支，不是全图默认：1404、reason516023、加载失败、Process早退等必须保持特殊/未知。仅补maze而不补可信state也会使clear正例失败；不能用任意全图state0修绿。

接线建议交唯一main：启动冻结原maze快照，按map资源交给地图所有者；由已建立的场景状态向MoveCommand提供受信字段，保留特殊分支。节点检查也不等于路径段、速度、量化轨迹或portal落点纠正，不能把点击目标纠正套到传送落点。根另补加密Owner负例，本批没有代替那层反馈。

## 全302/3443的当前数据与工厂筛选

本轮从当前`world_catalog.maps`、`load_placements`、`load_npc_definitions`及shape catalog重新统计；全量原PFS一致性沿既有[WORLD_RESOURCE_HANDOFF_AUDIT](WORLD_RESOURCE_HANDOFF_AUDIT.md)，**本批没有重新提取302份原包**。只有上面1006 maze另从原PFS重读。

| 当前快照事实 | 数量 |
|---|---:|
|配置地图 / available资源图|304 / 302|
|available中有NPC / 原本无NPC的图|285 / 17|
|原摆放总数 / 工厂bounds有效|3443 / 3443|
|缺CNpcConfig / 默认modelID缺CNpcShape记录|0 / 0|
|同图重复配置组 / 多出的重复摆放|175 / 866|
|最大图摆放数|1007：196|
|原配置name为空的摆放|439|
|原placement dir非0|3430（其余13条dir0）|
|重复配置且各placement dir不同的组|64|

`game_runtime.py`约132–139行工厂只保留定义存在、x/y在`min(width,height,32768)`相应边界内的摆放，以`(template<<32)|placement_id`逐条独立注册，binding_capacity4096、batch64。当前3443没有实际被这个过滤器丢掉，也没有接近4096的地图；它仍会在未来缺定义或越界时**静默跳过**，因此独立全量测试应以原摆放为oracle核对完整key/config/name/坐标集合，不能仅将同一过滤器结果当expected以自证。

`load_placements`保留同图重复ID的独立placement_id；不能把expected转换成`dict[npc_id]`或set(configID)后计数。原client模板导航选择signed64最小key，精确key访问仍独立；见[WORLD_SCENE_NPC_LOOKUP](WORLD_SCENE_NPC_LOOKUP.md)。key按map template生成而不同instance内复用，不自动构成串实例：权限仍必须核完整MapAddress/generation/epoch。302公共图登录不等于私有实例隔离测试。

`verify_world_scene_spawns.py`原结果为3443/866、294批、无rejected；本轮只读，没有改/重跑其落盘程序。它用纯NpcScene编码，不能替代GameRuntime真实登录投递；另一方面302登录若只检查“有AddUserScreen”，也不能替代全部3443内容对比。17个空图不应被“必须有NPC包”误报，439条原空名不应被“名字不能为空”误报。

## 类型、hide与生命周期不能由数量绿覆盖

当前3443摆放跨22种npctype：1:569、2:96、3:68、4:862、5:321、7:160、8:10、15:6、16:793、18:106、20:47、23:85、24:7、30:3、31:5、32:5、33:10、51:274、70/71/72/73各4。bodytype分别0:3106、5:321、1:6、2:4、3:6；actionname0:3442、1:1。

hide分布0:2357、1:1046、2:29、4:3、5:8，即1086条非0。工厂并不按npctype/bodytype/hide过滤，原配置ID交给client后仍有其自己的构造/显示/任务条件。既有[PROLOGUE_NPC_VISIBILITY_RESEARCH](PROLOGUE_NPC_VISIBILITY_RESEARCH.md)已证明具体hide1目标依任务mark显隐，hide5又有刷新flag差异；**不能将所有非零hide直接从server删掉，也不能把发出NpcBasic算作它们已经可见/任务可交互**。

额外原指令分支：本轮重读SAddUserScreen handler `11e71f5..11e7220`，配置ID14500–14999走`11d9ff0`，而非一般`11d9c70`；当前摆放中有321条属于此范围。单一普通NPC10000的原decoder/模型fixture没有覆盖全部这个创建分支。CNpc初始化`1202263..12022ab`还按19/23/24/51及70–73执行虚槽+10传0；槽指向`1174e80`写entity+19。本数据382条命中这些类型；本轮不擅自将该byte业务命名为任务hide。

默认modelID均能关联到2152条CNpcShape catalog中的记录，这是数据引用完整性，不是物理模型/贴图存在或原Process加载成功。factory仅使用CNpcConfig静态摆放，不等于已接5635个monster模板/monster.dat区域、野怪AI或战斗规则，不能混用NPC与monster ID。

当前GameRuntime仍导入/构造NpcScene并缓存`spawn_packets`（约130、139、187行），AFTER_ENTER_WORLD约442行取该缓存。`npc-lifecycle-v1`要求fresh snapshot、可信变化控制与512绑定预算，`npc-motion-v1`为显式content opt-in且movement_enabled=false；这些独立政策/模块不能因文件存在就算当前factory已接动态增删/运动。全静态3443首次登录+重连不会暴露“动态移除后重连复活缓存”等生命周期接线边界。本轮未新增受信变化事件或改策略。

## 朝向新线索：wire、placement fallback与模型分支

`NpcScene.spawn`第84行只传key/config/name/x/y，因此所有NpcBasic其余槽目前默认0；原placement.direction没有被显式带出。但不能把field38猜作方向：原handler仅按`==1`转bool。

本轮只读追到更精确的方向消费者（原映像SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`）：

1. **NpcBasic对象+48（Python field_48，node+50）**经`11e71c1/11e71c4`传info+20；复制器`11fd176..11fd180`把它复制到CNpc+120。
2. `12020ea`或`1202187`在+120非0时，将其传CNpc虚槽+e4=`11f5b00`，再传actor虚槽+40=`652750`；`652750 → 651700`明确用0..7枚举构造方向向量。这是wire槽到朝向消费者的链，不是把数字巧合当语义。
3. +120为0时，部分分支在`1202106/12021ab`调用Scene `11db690(configID)`。该函数拼当前scene+168资源路径与`/npc.xml`，向前遍历原id，首个匹配后在`11db7f5..11db820`读字符串`dir`（UTF16@2453840）并返回。
4. 并非所有模型都直接使用该dir：`120213f`读取shape配置+100；有分支默认4，另有actor能力分支选择原placement奇数dir或rand的3/5。+120=0也不能简单说成“模型总朝0”。

本轮有界执行原`12020e0`起的实际选择分支三例，fixture CNpc+98=1，Scene dir getter明确Adapter，停止在真实`11f5b00`入口捕获原参数：

| wire经复制形成的+120 | Scene dir Adapter | 原setter参数 |
|---:|---:|---:|
|5|7|5，未查本地dir|
|0|7|7，实际调用Scene getter|
|0|2|4，原分支fallback|

这只执行方向选择Seam，未执行整个CNpc构造、原XML parser或实际actor旋转/渲染；原getter读取dir的结论来自完整原静态代码。64组重复配置具有不同placement dir，若同图都依“按configID首条dir”的分支，可能不能保留每个实例方向；但实际model flags/其他分支尚未逐个执行，**暂不报已证GUI朝向错误**。下一最小Seam是保留实际bean→info复制和该模型flag条件，进入原setter或actor朝向快照；不需要改field38或重做既有codec。没有改field_48命名/接口或生产发包。

## 不进入战斗、又保留实际移动链的方法

当前RoleOwner对MOVE/CHECK/STOP在地图接受后仍调用`wild_move`（约559–567、986行），后者使用真实WildEncounters；不应patch掉它来让全量移动测试“安全绿”。当前野外政策46图，其中39 hidden/7 visible；阈值64px、chance2000/10000、grace5000ms，这些是designed政策，不是原版数值。

安全的限定fixture：每图选原mask1 clear、bounds内、**非portal格**的格中心`x=16*gx+8,y=16*gy+8`，MOVE意图与STOP到`x+1,y`；验证前后`//16`格完全相同，并实际核无transfer/battle。这仍经过真实move_for_encounter、checkpoint和wild_move。

`WildEncounters.accepted_move`132行对MOVE无checkpoint且current==previous直接None；144行对同16px格STOP直接None，在随机抽取150行之前。因此安全不依赖测试赶在5秒内、SystemRandom碰巧未中或修改战斗资格。**不能把任意1px都叫同格**：从remainder15走+1跨格，若已有距离预算就可能触及遇敌抽签。

本轮另用真实WildEncounters公开Interface做有限对照（trusted MoveResult是明确fixture，不冒称实际地图接受）：1002 hidden图、clock已过grace、RNG Adapter只要被调用立即抛标记；MOVE意图无抽签；一次跨格63px积累后，同格71→72的1px仍无抽签；再跨格72→80才触到RNG标记。没有生成EncounterTicket/Fighter或BattleOwner，`pending`仍空。它证明同格门控确实在预算/RNG前，不执行任何战斗。根的302加密测试仍需分别核实际位置版本/checkpoint，避免只看到无battle便算移动成功。

## 本批快照与未验证范围

| 文件 | SHA256 |
|---|---|
|game_runtime.py|`ccd2bbdea1d1e40638e9553ce1236a7d115e037208fae92ffe36ea1a205c36e1`|
|world_npcs.py|`177f55e34168229665586f9fef6ddee3fcdeef17c3c47fde716ad7353ac7d1c4`|
|world_catalog.py|`f0194f55b1ee59e234155fd41a7e890555376e360955be0081895577f1f788dc`|
|world_entity_protocol.py|`d4977aa707e2e0c3d1cbca6bb11ddafa39f678ef3457128d13f9e5db8d66f964`|
|wild_encounters.py|`91590c5f42e0488114b85f3ccf29e49165dbd4d3c7140fe1fa4df1834138f378`|
|world_owner.py|`3a893ec87feab966adf4f07f1917779296669f143177cb78da580758c3ef4d5b`|
|world_movement.py|`d2238aaa4f9ce88743b26a32d7ae961148d6bd82999f29300442169dc2fea322`|
|npc_lifecycle.py|`8a0cd6313c761828c6acf5b483edbf96f72b043d307ae60bd20dc506fb8edf8a`|
|verify_world_scene_spawns.py|`9e28d59e44b6d37ca3c7a52fa0ab28ca9a432560ea202c18a2bd89594a8b4f38`|
|design/npc-interaction-v2.json|`d0f4081008982314f2b224b28cfe8d6c32701bc2835f11b063180c066d0951e1`|
|design/npc-lifecycle-v1.json|`31ac74006ca8c35d7b598eaec17528a43ddbe006f3efe154eecd7fcf7d71b387`|
|design/npc-motion-v1.json|`455f79b804899272dd66f18cbef2d378a6c22b0f7851e4d734f06a4f599d5635`|
|design/wild-encounters-v1.json|`f3fb7fbd200bbbcb5f4eaeecb419ad46685fc0a18772d53d636bb3636323a8a9`|
|catalogs/world.json|`22d74787c6e43d66bb8aa04d4b7e91befb9fe8897b0e1db780d71219c65cade6`|
|catalogs/knight.gsp.npc.cnpcconfig.json|`cf070e700e37a6d8d350ccb1e4d86610408e5ffcecad4710641cf2d06aca847d`|
|catalogs/knight.gsp.npc.cnpcshape.json|`fadadbe4ffeec2c52651473eefcdd899b1b8b4699f8583d2882cb9b1ee32a0ea`|
|WORLD_RESOURCE_HANDOFF_AUDIT.md|`ab7a4d46f684d546eb797c4fc0f6184ce1decb8b73fd171eca3649049a17ff3c`|
|verify_world_runtime_collision_probe.py|`af74d92ddff5fbf424a6486b17078e43da6d177f31f7c54af0b7930e89d20137`|

research实际决定是把catalog完整性、原handler分支、局部原方向执行、真实runtime碰撞红分层报告；diagnosing-bugs用明确clear/bounds对照排除坏fixture，仅blocked契约红，不把候选补丁当结果；codebase-design将maze与trusted state作为地图移动Interface的事实输入，保持NPC、移动、投递和战斗所有权分离。

未验证：root正在做的302图加密登录总结果、自然传送/全剧情、全3443原handler构造/可见/朝向/服务、dynamic lifecycle、monster渲染/AI/战斗、特殊地图状态/天气、连续轨迹/速度/所有阻挡、真实客户端视觉与商业容量。本批明确交出碰撞接线红例，不声称全量恢复已完成。

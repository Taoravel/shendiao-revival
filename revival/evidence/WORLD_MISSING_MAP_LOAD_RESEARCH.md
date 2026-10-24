# 1302/1307：原普通地图加载、资源请求与可选补丁边界

2026-10-23。采用 Matt Pocock research 的后台第一方追溯，先读 [WORLD_MISSING_INTERIORS_RESEARCH](WORLD_MISSING_INTERIORS_RESEARCH.md)，保留1593/1422仅候选的结论；已读根AGENTS、ARCHITECTURE、DESIGN_AUTHORITY。本批只新增独占研究脚本、结果及本文，未改旧报告、生产/shared/政策、客户端配置或资源、存档和运行服，未启动任何客户端、GUI、服务或patcher，未扫描整盘。

产物：[verifier](../verify_world_missing_map_load_native.py)、[机器结果](world-missing-map-load-native.json)、[原指令](world-missing-map-load-disassembly.txt)。原映像SHA-256仍为`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

## 结论与可证边界

**当前安装的已声明地图资源来源中，1302/1307请求的原目录确实缺失；本批没有找到可验证的1302→1593或1307→1422别名。** 原普通load按原resdir请求以下路径，首次RMP文件打开失败后直接返回false，没有继续尝试候选目录：

| 地图 | 原resdir | 原生实际请求 | 原PFS条目 / 精确loose文件 | 原load返回 |
|---|---|---|---|---|
|1302|quanzhenjiaozhenwudian|`/map/quanzhenjiaozhenwudian/map.rmp`|均不存在|AL=0|
|1307|taohuadaoxuanjitang|`/map/taohuadaoxuanjitang/map.rmp`|均不存在|AL=0|
|1593（路径正控）|map_1593_quanzhenjiaozhenwudian|`/map/map_1593_quanzhenjiaozhenwudian/map.rmp`|PFS条目存在|**未返回成功，打开边界前停止**|
|1422（路径正控）|map_1422_changshengdian|`/map/map_1422_changshengdian/map.rmp`|PFS条目存在|**未返回成功，打开边界前停止**|

这证明新鲜普通load的路径及“资源不存在”输入下的原失败传播，不是完整实际VFS、RMP解析或GPU加载。正控只证明不同地图请求不同路径，不证明替代兼容。没有把host返回成功当作资源存在：两个有条目的正控在该边界抛出限定停止，完全不返回AL=1。

存在一条原生**可选分段资源状态/输出路径支路**，不能无视后宣称“客户端绝无重定位能力”。但它依赖的`cfg/dicFile.dfl`与`cfg/segm.cfg`在本地缺失；原管理器初始化实际返回false并清空global。它不构成本地可用的旧地图映射证据。

## 原普通 Scene→World→RMP 路径

原config.pfs重新读取并CRC校验 `autoconfig/knight.gsp.map.cmapconfig.xml`，SHA-256为`374d400f933a74e83d402c8da948fef47823e7f92344ccb660414edfb87a1814`。四个原行完整属性保存在JSON。Scene+110（map ID）和Scene+168（resdir）为本夹具按这些原字段建立的初态，不把它当完整登录/配置初始化流程证据。

实际保留并执行：

| 地址 | 原作用 |
|---|---|
|`0x11e0310`|普通Scene地图load；使用Scene+168，而不是电影Setmap临时配置|
|`0x11e0386`|逻辑x乘1.5；fixture输入[120,160]仅是辨别路径的普通坐标输入|
|`0x11e03dd..0x11e0411`|拼接resdir与`/maze.dat`，把resdir、maze路径、point交给world虚表+4|
|`0x5f9770`|原World load薄入口，转入`0x5fcd50`，未替换为host load|
|`0x5fcd50`|处理fresh/cached分支、可选分段资源状态、分配Map解析对象，进入`0x672ff0`|
|`0x5fd0c9..0x5fd0fc`|先给maze路径增加`/map/`前缀，保留resdir供RMP路径生成|
|`0x672ff0`|原资源读取调度，首先通过`0x5f9b70`形成RMP路径并调用资源provider|
|`0x5f9b70`|原字符串运算拼接`/map/` + resdir + `/map.rmp`；没有1302/1307专用常量或候选转换参与此已执行支路|

每个地图的hit序列均为`11e0310 → 5f9770 → 5fcd50 → 672ff0 → 5f9b70`。fixture设置空的current-map字符串及未缓存状态，明确测**新鲜加载**，不推广到已有历史缓存的运行进程。

两项缺图均只有**一次**RMP请求。provider按已确认的缺条目/缺精确loose文件输入返回false后：

- 原`0x673113..0x6731ae`处理首次资源打开失败并返回false，不继续到后面的maze/其他资源读取。
- 原`0x5fd118..0x5fd140`释放Map对象、清World+298并置失败状态World+66c=1。
- 原Scene `0x11e0431`进入失败路径`0x11e07b7..0x11e07ff`，清加载过渡字段，AL=0。

已执行的这段失败链没有尝试1593/1422、增加`map_1302_`/`map_1307_`前缀或另选同尺寸地图。**这不等于全程序所有外部补丁/历史缓存都已排除。**

## 挂载、外部目录和可选资源配置

当前原 `cfg/mount.xml`只有一个`/map`挂载记录：

```xml
<mount root="/map" dir="/root/artres/map" pfs="/root/artres/map.pfs" mt="2"/>
```

原加载器`0x62a3e0`在`0x62a535`处理`/root`，`0x62a5a1..0x62a5db`将可执行目录与常量`\cfg\mount.xml`拼接并读取；不是凭安装中恰好有一份XML猜它用途。原`0x62a8b6..0x62a8da`读取`mt`，`0x62a902..0x62a989`读取`pfs`、检查存在并创建provider；该分支失败才在`0x62a991..0x62aa49`读取`dir`作另一个来源，成功后在`0x62aa4b..0x62aa57`注册mount。

这段静态链证明**有目录来源入口**，但不能称每个PFS内部缺文件都会自动回退loose文件：这里是初始化时对PFS/dir来源的选择。精确的provider内部优先级/后续mount覆盖没有在本批完整重放。两个目标loose文件路径也已直接检查不存在，故当前看不到可补齐它们的已声明目录内容。

普通绝对虚拟文件入口`0x4021e0`在`0x402203..0x402224`检测首字符`/`后交给`0x403f30`处理，而不是直接当工作目录相对文件打开。这支持沿`/map`挂载调查；本fixture的资源provider仍是明确Adapter，没有冒充完整原挂载树/PFS打开实现。

原分段资源入口另有：

| 地址/字段 | 可核查行为 |
|---|---|
|global `0x29994fc`|原映像保存值为0；World可选分支在`0x5fcf5e`检查它|
|`0x62b470 → 0x62a0e0 → 0x742490`|查询资源状态并处理输出wstring；World根据返回0..3选择不同后续路径。存在通用可选能力，不是旧地图ID映射表已找到|
|`0x7418a0`|分段资源管理器初始化/失败销毁与清global，本批实际执行|
|`0x742121..0x742145`|依次检查`cfg/dicFile.dfl`、`cfg/segm.cfg`；前者缺失就短路|

本批将原`0x7418a0`从入口执行，只有OS文件存在查询边界按本地文件系统结果适配。实际第一次查询为`cfg/dicFile.dfl`，不存在，原流程返回AL=0、global仍为0；另直接检查`cfg/segm.cfg`也不存在。因此普通路径测试采用global=0与原映像、当前配置初始化结果一致，不是为了避开可疑分支任意选择默认值。

该相对文件查询在fixture中解析到已知安装根；还精确检查安装根`cfg/`与`bin/cfg/`两处的这两个文件，四项均不存在，路径与结果保存在JSON。未启动客户端确认其他工作目录或外部安装的文件来源。

没有解析一份不存在的DFL来猜其1302/1307映射，也没有fabricate其命中结果。未来若取得真实分段资源配置或新版patch，需重验此分支与目标路径；本批结论不能用于断言任何未来原服补丁都没有旧图。

## 原包中相似名字的内容

本批只遍历原map.pfs的目录索引，针对`quanzhenjiaozhenwudian`、`taohuadaoxuanjitang`筛选，分别记录92和36个名称命中；完整名单在JSON。存在图元/候选地图复用痕迹，与旧报告一致，但**没有目标目录的map.rmp条目**。目录索引存在性不等于本批逐个读取并CRC校验全部这些图元。

1593与1422的真实RMP、尺寸和美术复用证据继续以旧报告为准。它们在本批作为“原resdir能请求已有条目”的正控，未复制、未重命名、未替换配置，未继承候选的maze/NPC/安全属性到旧门派内景。

## 实际方法、Adapters与未验证

研究问题拆为三种可判定预测：普通链若原生改名，则请求路径应改变；若失败自动fallback，则应出现第二目录请求；若本地分段资源管理器能启用，则配置检查和初始化结果应支持。前两项在fresh branch的原执行均不支持，第三项在当前缺配置环境原初始化失败。其他版本/外部patch的缺失信息保持未知。

独立Interface为脚本入口，无生产接线。原Scene/World load、路径字符串构建和缺文件失败传播执行；以下是明确host边界：

- 继承独占研究的MSVC字符串、堆分配、memcpy等库Adapter；新增`const wchar* + wstring`和wstring equality原语。
- Scene旧资源clear、World进度回调、日志为Adapter；Map解析对象constructor `0x5f99b0`只提供必要的资源context/vtable，未执行完整Map构造器；失败析构边界也适配。
- 资源provider的open是捕获边界。对确实缺失的两个目标，根据原PFS目录与精确loose路径的共同缺失返回false；已存在候选在此处停止，不返回成功、不运行RMP parser。
- 可选分段管理器的线程ID与物理文件存在查询适配；其初始化、缺文件分支、清global执行原指令。没有完整执行DFL解析或下载/更新器。
- 未重放完整原VFS挂载树、PFS解压/读取实现、外部patcher、历史地图缓存、网络进入场景、GPU显示或玩家交互。没有扩大到整盘搜索其他安装/版本。

## 验证与下一决策

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' revival/verify_world_missing_map_load_native.py
```

实际exit=0：`map_cases=4, segment_init=1, passed=true`。两个缺图在原fresh load上明确失败，两个候选仅到资源请求边界，分段配置初始化失败。当前不能将302/304可用实例统计改成完整，也没有可交付为client_verified的目录别名。

仍需主策划裁定或取得原资源后才能补齐：是否采用明确标为designed的兼容内景；若采用，分别指定地图身份、完整RMP与碰撞、任务NPC、门派交互、安全属性及进出落点。原资源缺失时，不以候选尺寸/图元复用自动继承这些规则。本批不实施这一策略。

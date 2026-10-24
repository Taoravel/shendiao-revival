# 客栈任务外层目标与室内NPC：原生导航研究

2026-10-24，端游1.6.1/网络601。结论：原客户端的一条按NPC模板ID导航的分派，确实把10157导航到其定义地图1376；原路径表也单独保存1007→1376、1376→1007两个有序项。**这些是客户端导航证据，仍不能证明原服务器怎样比较任务102002的ActiveInfoMapID1007与实际1376的NPC交互。** 本批未授权或实现地图alias，没有删除任务地图检查。

## 原始来源与版本

本批独立重读原PFS，使用[pfs.py](../pfs.py)验证条目解压长度与CRC，再核SHA并解码。既有[NPC原来源报告](npc-task-room-original-sources.json)的七个成员逐一匹配；本批另读paths.xml，不把派生地图连通性当原任务规则。

| 原成员 | 字节 / CRC32 | SHA256 |
| --- | --- | --- |
| config.pfs / autoconfig/knight.gsp.task.cmainmissioninfo.xml | 2026233 / 3f7ab7b3 | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |
| config.pfs / autoconfig/knight.gsp.npc.cnpcconfig.xml | 619832 / cc437e13 | b4fc5d440380fb535a36b8e5315c5a1bf10a99f550f5bfde55bd156fca864f85 |
| config.pfs / autoconfig/knight.gsp.map.cmapconfig.xml | 91110 / 3325016f | 374d400f933a74e83d402c8da948fef47823e7f92344ccb660414edfb87a1814 |
| map.pfs / map_1007_linan/npc.xml | 11666 / 1d815d03 | ad14d17f41bcbcf706420ab139e6bb43a4878b439220d47794278cf9c9f54aaa |
| map.pfs / map_1007_linan/goto.xml | 6165 / 982f08bd | 55f9cb3d15343b54f01043994f5628a8bf22186380a2b463f708ba28e697bdc6 |
| map.pfs / linankezhan/npc.xml | 179 / c21f12e6 | 6171bc0ba3a338e3a4b69e5072352d77298d77563609fca535389297d2314846 |
| map.pfs / linankezhan/goto.xml | 675 / c4d00f1f | 1c0de45e9125e688b633ab7ee058cb06950f54b99bea83be1db2908b01e602b7 |
| config.pfs / paths.xml | 235399 / 21ea11b3 | 5784fd5b9f3ccc65cb0974fee6cceb0185b4525286275363c2d639e55aaa9d10 |

原映像为[native-image.bin](native-image.bin)，VA基址0x400000，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。本批直接用[native_inspect.py](../native_inspect.py)反汇编下述地址并读取原UTF16字面量；地址仅对应此映像。

已有[任务侧来源/接缝审计](TASK_ROOM_TARGET_SEAM_AUDIT.md)列清五条原任务：102002、200602目标地图1007，102005、102006、200490目标地图1376，NPC均10157。原10157配置mapid1376、xPos33/yPos57；唯一静态实体为1376/p1(532,920)，1007没有第二实体。1376配置bShowInWorld=false/findpathin=true不等于已经证实一个通用parent-map关系。

## NPC模板导航：定义地图进入原入口

原指令链如下，本批不把整条UI分派直接命名为“任务追踪专用入口”：

1. `0x15725e7..0x15725f6`经CNpcConfig getter `0x89df90`，用`[ebx]`所存NPC模板ID查询配置；id=-1退出。
2. `0x1572601..0x1572625`有场景模式分支：若scene+0x364等于此处ebp值2，且scene+0x110当前地图不同于配置+0xfc地图，则进入另一错误分支。探针明确采用mode0，未验证mode2跨图行为。
3. `0x157262a`的模板0x2a9a另有专用坐标分支；10157不命中。普通分支`0x157264e..0x157265a`直接读取配置+0xfc地图、+0x100的xPos、+0x104的yPos。配置字段偏移与既有[原坐标解析研究](BLOODMARK_INTERACTION_DISTANCE_RESEARCH.md)相同。
4. `0x1572660..0x1572678`检查Ctrl(0x11)，按下走另一函数0x1567ad0。未按下时，`0x1572685..0x1572694`对配置x/y各左移4位，压入地图、NPC模板ID及其余参数，经`0x15721c9..0x15721d5`调用主角色+0x378的导航入口`0x1142620`。

root已实际运行既有[独立探针](../staging/research_task_room_navigation_native.py)一次，exit0、约0.52秒；原stdout转存[反馈记录](task-room-native-navigation-feedback.json)。本研究没有重复启动该探针、游戏或服务。两例current_map分别1007、1376，在0x1142620入口实际捕获相同七参数：

```text
(528, 912, 1376, 10157, 0, 0, 1)
```

适配仅为配置manager/lookup、Ctrl未按、明确非mode2场景与metadata0；x/y读取、分支、左移、压栈及原call均由原指令执行。停止在导航入口，**未执行全路径、跨门、NPC接近或CVisit**。

这证明上述模板导航分支选择CNpcConfig的1376，未从此分支读取任务的ActiveInfoMapID。它不证明所有任务追踪按钮都经过这一分派，不证明原任务服务器忽略目标地图。定义格点33,57×16得到(528,912)，与静态摆放(532,920)相差(4,8)；两份来源不得合并成一个“精确相同的坐标”。

## paths.xml消费：有序对查表，非地图等价

原路径装载器`0x1141ae0`读取UTF16字面量`/config/Paths.xml`(0x2291cd0)。`0x1141bd5`、`0x1141c15`、`0x1141c57`、`0x1141c97`分别引用sourceMapID(0x2291cb8)、destMapID(0x2291ca4)、xPos(0x226b284)、yPos(0x226b278)。`0x1141cd8..0x1141cfb`计算`sourceMapID*10000+destMapID`，经0x64fd50写controller+0x2c的map，并把xPos/yPos保存成关联二元值。构造器`0x1141ed0`经0x1141f75调用该装载器。

原`0x1141970`取scene+0x110当前地图及传入目标地图；相同直接返回true。不同则计算同一有序键，到controller+0x2c查询并按是否找到返回布尔。这里没有图遍历，没有把任意可达地图归为一类，也没有读取任务ID或NPC实例证明。`0x1142620`的`0x1142820..0x114282d`实际调用该函数作为导航分支判据；这仍是客户端导航许可分支，非服务器任务受理。

原paths.xml精确两行：

| sourceMapID | destMapID | xPos | yPos |
| ---: | ---: | ---: | ---: |
| 1007 | 1376 | 205 | 248 |
| 1376 | 1007 | 70 | 85 |

root探针先调用原空map构造器0x1141170，再真实执行0x1141970：空表同图两例true、跨图两例false；用原插入器0x64fd50放入这两条原有序项后，双向查询各true。此夹具只放两项，未调用完整XML装载器；本批静态核原装载器与查询器使用同一键，不能把夹具说成完整路径表运行。

另核`0x1141e60..0x1141e98`以当前地图与controller+0x10所存目标构同一有序键，读取关联x/y后各左移4位输出。这给路径表关联坐标以导航消费依据；本批未执行此函数，未证明它最终选择哪个门格、是否自然跨门、路径中途如何更新或怎样抵达实体。原goto.xml双向各25格与路径表有序项均是旅行资料；均不能转成任务地图受理等价。

## 仍未知的服务器受理与后续决定

`client_verified`仅覆盖原来源、上述模板导航参数、装载/查询指令和有界离线查表反馈。既有[NPC诊断](NPC_TASK_COVERAGE_AUDIT.md)则在真实临时RoleOwner下复现恢复实现拒绝102002的`Task acceptance NPC mismatch`；那是当前恢复服行为，不是原服规则。

原服务器究竟针对102002/200602比较模板、实际地图、逻辑地图或另一个精确关联，仍**unknown**；原客户端本批没有服务器接受算法。已有官方端游客栈投宿叙事的支持范围沿用任务侧审计，不重搜、也不外推地图ID或接受规则。若根设计者采用精确映射，须明确标designed及具体任务范围；原本已经写1376的三条任务不因这项缺口扩域。禁止删除全局地图检查、按任意连通图放行或伪造1007第二个10157。

codebase-design在此实际影响决定：客户端导航Interface选择目标定义，是一个Seam；角色任务接受/完成Interface消费实际NPC证明，是另一Seam。前者的可达性结果不替代后者的权限。若后续设计匹配Module，菜单、接取和完成应复用同一精确规则，保留1376完整地址、真实placement、角色epoch、位置版本及世代；本批没有定义或实现此新Interface。

## 产物、方法与未验范围

research按原PFS/原映像第一方追溯，作为root依技能委派的后台研究写此单一Markdown；codebase-design用于区分导航与任务受理Seam。沿用脚本未改，SHA256 `3df7d16cff612a702b2373a3f7df6603d2ae5211f09e355df4b3583f236e9a22`；其NativeBattleDecoder依赖[research_battle.py](../research_battle.py) SHA256 `4aa276ece9ea4a9f13d9c4f9a0de2900f97cf77ff3783aeecc92e7d5f3a47b45`。root反馈JSON本批读取时SHA256 `a2f574841f63486f8d8c316a8952dc64be33c73b998aaca1f37763731566ae01`，具体probe调用时间依据见其字段，不伪造本研究自己的重跑。

验证：本批七成员独立CRC/长度/SHA复核与paths.xml直接解码通过；原静态反汇编与root实际有界反馈相符。未验：任务追踪UI完整来源、原寻路引擎/自然门户穿越/实际NPC到达、原服接受算法、GUI、在线角色、真实DB或任何部署。没有改Task/World/shared实现、中央政策、现有Module、在线服或正式战斗；研究收敛在此未知项，不继续无限还原寻路引擎。

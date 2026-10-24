# NPC访问兼容差例：血手印62像素处原发包、当前服拒绝

2026-10-23；本地端游1.6.1 / 网络601。按research、diagnosing-bugs及ARCHITECTURE/DESIGN_AUTHORITY开展独立只读审计。本批只新增本文和[npc-interaction-compatibility-audit.json](npc-interaction-compatibility-audit.json)，没有改生产/主政策/他窗脚本，没有客户端、GUI、出网、真人数据库、服务或战斗操作。

## 结论与推荐

**存在已实际复现的客户端请求准入兼容缺口。** 原血手印placement `(1668,970)`，角色在原map1006 mask1合法点`(1668,1032)`，欧氏距离62。由原正向坐标setter生成模型点后，原交互入口实际算得格距4<13，构造并提交CVisitNpc；当前NpcScene对同一绑定实体和同一位置，旧radius32与已批局部radius48都抛`NPC out of interaction range`。

“自动寻路最终停点尚未知”不能否定本差例：在已满足本条交互入口可见/对象状态前提、角色处于上述点时，原代码**直接选择发送访问包**，没有进入需继续接近的`0x11fe700`路径。是否已恢复完整鼠标命中或自然导航，是另一层验收；当前服务端拒绝此原可产生的合法点访问请求，是可独立检验的差异。

**建议root另立显式服务端兼容政策，采用与原共享CNpc离散格判据匹配的准入，而不继续把32/局部48作为此共用路径兼容完成标准。** root要求追加的10908说书人、10380女大夫两例均独立执行相同距离比较及CVisit提交，证明13格不是血手印距离特例；仅10498跳目标碰撞查询。普通两例的碰撞允许为明确fixture，不能冒称其实际点击/路径已通过。保留当前租约/实例/绑定/位置版本/active/角色合法位置及任务资格。原客户端共享判据为client_verified；“服务器默认采纳同一判据”仍是designed，原官方服务器距离仍unknown。不得改写成“原服208像素圆”，也不能取消未知其它NPC模式的独立门控。

## 反馈环：本批实际红例

先读[NPC_APPROACH_NATIVE_RESEARCH.md](NPC_APPROACH_NATIVE_RESEARCH.md)、其[公开研究helper](../research_npc_approach.py)及[NPC_INTERACTION_DISTANCE_DECISION.md](NPC_INTERACTION_DISTANCE_DECISION.md)。现规则是默认32、仅精确血手印48。这一旧政策打通此前32无路径见证的自然链，但没有覆盖原直接访问允许域。

本批最小反馈由两步组成：一次原`inspect_approach`执行→把捕获的原q64 key绑定到真实placement13→调用当前`NpcScene.interact`。只含这个角色位置，不调用任务、交易、奖励、传送或BFS。实际终端红例（exit1）：

```text
SERVER_REJECT NPC out of interaction range
AssertionError: Native CVisit at legal distance62 (cell_distance4) is rejected by current NPC policy
```

断言要求当前服接受这条原客户端可产生的访问；保持现政策即稳定变红。另一个诊断执行以“预期双方不同”为断言收集证据，输出JSON；它的exit0只证明差异被准确复现，不表示兼容已经修复。

本批三项可证伪假设：

1. 当前圆形radius过窄：同一真实坐标应原发CVisit、当前拒绝。**已实际证实本例**。
2. 模型输入并非逻辑x×1.5/y，旧相对坐标probe可能不足：若正向setter不产生预期模型点或当前点不mask1合法，差例不成立。**原setter及原mask检查已排除此解释在本例的影响**。
3. 原此位置应继续接近而非发包：如果执行落到原行动依赖而无visit_send，即反证。**实际到原构造和sender，未进入接近依赖**。

没有进入修复/回归转绿阶段，因为本批明确禁止改政策/生产；报告不宣称原red已修复。

## 逻辑位置到模型点：独立核验的正向consumer

原映像[native-image.bin](native-image.bin)，BASE `0x400000`，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

- CNpc原vtable `0x22985e4`的+c8是**`0x11f6480`**。函数读取输入整型逻辑x/y，`0x11f6489..0x11f64ac`执行原x87 `x*double1.5`、按符号±0.5后原整数转换，再将y原样写入临时点；`0x11f64cb`调用实体虚槽+cc。
- 原NPC初始化`0x12022ad..0x12022d6`从entity+0x10c/+0x110（复制后的实例info位置）取点并调用该+c8 setter；原info复制器`0x11fd158..0x11fd161`确实将源info+c/+10搬入该位置。它不是cnpcconfig的xPos/yPos导航字段。
- 本批实际执行完整`0x11f6480`至下一虚槽+cc的明确Seam；仅将+cc适配为捕获，不手算替换乘法。输入NPC逻辑`(1668,970)`得模型`(2502,970)`；输入角色逻辑`(1668,1032)`得`(2502,1032)`。两个x均为偶数，精确1.5倍不存在半整数舍入歧义。
- 随后将这两个**原setter输出**传给新公开`inspect_approach(...,npc_model_point=...,actor_model_point=...)`，只作为模型API依赖返回；原实体+d0/+d4 getter、模型转格、距离、原混淆控制流、CVisit构造及原sender调用仍执行。

这闭合了本例“逻辑像素→原模型点→原访问距离”的数值链。没有执行完整模型backend、角色创建/鼠标点击生命周期；这些不影响已执行setter和该入口的条件输出，但不能冒称真人GUI通过。

## 单一差例的完整结果

本轮从原map.pfs直接CRC读两条成员。npc.xml第13条确为10498、posx1668/posy970/dir4，与当前placement目录交叉；不使用配置104/60代替它。

| 原成员 | bytes / CRC32 | SHA256 |
|---|---|---|
| map_1006_jiaxing/npc.xml | 3571 / 51217023 | 72b66cc70e41d78997fb8369c74c5f21a69f500e790797718a41d56ff857752c |
| map_1006_jiaxing/maze.dat | 113676 / cda771b4 | 6f81a7407738d6ce9b7ca167c82c28849dea1db12e7f2aa7fe1285e747698351 |

| 项目 | 实测结果 |
|---|---|
| NPC / placement / map | 10498 / 13 / 1006 |
| NPC原逻辑位置 | 1668,970 |
| 角色逻辑位置 | 1668,1032，原mask1 clear=true |
| 欧氏像素距离 / 平方 | 62 / 3844（均超过48与32） |
| 原setter模型点 | NPC2502,970；角色2502,1032 |
| 原helper格点 | NPC104,60；角色104,64 |
| 原整型格距 | 4，原比较4<13 |
| 10498目标碰撞/分区查询 | 均未调用；collision fixture为0但该模板分支根本不读它 |
| 原提交 | `0xc2329`，原CVisit ctor `0x120eea0`，到虚sender；没有等待host调用报文builder |
| 原q64 body | `000003ef00000001`，仅为原隔离helper的明确实体key |
| 当前NpcScene旧32 | 拒绝：NPC out of interaction range |
| 当前NpcScene已批局部48 | 同样拒绝 |

key是原helper内显式fixture，值不是原服发行算法；本例把**同一个捕获key**绑定到实际placement13后交两次当前server Interface。其高32位不作为地图语义解析，因而不会发生“拿另一个NPC/另一个map来造距离差”的误导。实际MapAddress为1006/1006/partition0，Location的role/epoch/version及expected/current一致、active，期限有效；失败确定发生于距离判断。

另做一次原DDA段查询：从此前已批48自然路径末点`(1656,1016)`到本例`(1668,1032)`，mask1 segment_clear=true。这条短段说明该差点可以由已知近点沿正常原clear段到达；本批没有重跑整图BFS或完整角色运动，不能把段查询冒称已实际向服务器移动。

## 原离散predicate与208圆的区别

原流程在`0x11c5ba0`把模型x/24、y/16按有符号向零截断为格点；`0x6bba90→0x5a5370→0x19191e0`计算并截断欧氏格距；`0x29d6f58..0x29d6f62`要求整型结果<13。这是当前可执行的一手证据，不是unknown。

对合法非负整型逻辑坐标，原正向setter的x舍入后除24与`floor(logical_x/16)`数学等价，y为`floor(logical_y/16)`。因此root若制定只覆盖此普通逻辑域的兼容投影，可显式描述为：

```text
role_cell=(floor(role_x/16),floor(role_y/16))
npc_cell =(floor(npc_x/16), floor(npc_y/16))
接受 iff (role_cell.x-npc_cell.x)^2 + (role_cell.y-npc_cell.y)^2 < 169
```

此处是将已核验原转换/截断链表述为服务端设计输入，**不是本批已实现或全域差分验证的新函数**。root后续应独立验格边界和距离平方168/169等实际存在的边界样例；不要忽略旧位置信息版本、动态NPC/飞行状态或不在已知普通逻辑域的输入。

该区域因格取整对齐而非以NPC精确像素点为中心的固定圆。简单改成208圆无法与之完全相等；本研究不推荐用208圆代替。已批48打通一条见证，不等于覆盖整个客户端允许域；不应继续用“只差自动停点unknown”否认本例已实际出现的请求差异。

## 最小服务端设计建议及仍保留的未知

将本批三条差异及共享原consumer交root裁定：新增版本化、启动冻结的**离散格距离规则**，保留原placement/mask，供NpcScene与NpcLifecycle同一距离Interface消费。仅继续给10498局部加半径不能覆盖下面两条普通模板的共用距离条件；root可以选择新版默认匹配该CNpc路径的精确predicate，但必须明确为服务端兼容设计。当前`radius_for`只返回整数半径，不能真实表达该非圆区域；若采纳，需演进所属Module的判定Interface而非在调用方各抄一份格公式。见证/测试也需消费同一规则，不再单独假定r48。

保留当前严格角色租约、当前完整MapAddress、entity-key绑定/生命周期、active/位置版本/有效坐标与当前任务资格；本研究不授权穿墙、取消任务前置、任意远程访问或跨实例引用。10498原客户端跳过的是目标点碰撞/分区检查，不代表服务器应允许角色站在阻挡点，本例角色点本身确实合法。

原官方server是否比client更严格仍unknown；即使原服可能有更严规则，也不能消除当前恢复客户端可直接产生本请求而本服拒绝的兼容风险。这里推荐的是**明确选择兼容原客户端共享距离条件的恢复服设计**，不宣称已找回原server源码。下面普通模板两例已证明共享距离分支的具体差异，不能再将此问题只留给血手印；其真实目标碰撞/分区条件仍未恢复，须继续分开记录。

## 追加两例：普通NPC共享距离条件

按root追加的窄范围，使用同一公开helper及同一原正向setter，各再执行一个普通模板，不重跑48矩阵。本轮另直接CRC读`fubenjiaxing/npc.xml`及原map1007的npc.xml，逐条核对下列placement；成员长度/CRC/SHA与原行保存在唯一JSON的sources。

| 模板 | 原map / placement | NPC原逻辑位置 | 角色mask1合法点 | 原setter模型点（NPC / 角色） | 距离 / 原格距 | 当前服 |
|---|---|---|---|---|---|---|
| 10908 说书人 | 1501 / 10 | 1049,1559 | 1049,1623 | 1574,1559 / 1574,1623 | 64 / 4 | 默认32拒绝range |
| 10380 女大夫 | 1007 / 34 | 1996,3963 | 1996,4027 | 2994,3963 / 2994,4027 | 64 / 4 | 默认32拒绝range |

10908的逻辑x为奇数，原setter真实得到1574（而非把1573.5作为整型模型输入）；原getter/格转换仍得到x格65。10380得x格124。两例都实际进入原`0x1215790`，到`0x29d6f58`比较4<13，调用`0x120eea0`并到sender捕获CVisit；与10498同一consumer，距离比较本身未按模板另选13。

与10498的重要差别：两例均实际调用原`0x11c5c00`目标碰撞查询，本次给明确Adapter返回1，随后进入距离/发包；没有把它替换为“真实地图碰撞已允许”。未调用的分区查询也不能据此宣布实际场景会允许。站立点mask1合法，仅证明人物本点不是阻挡；**不证明该NPC真实目标查询、连通区域、鼠标命中或从某前缀位置走到这里的路径**。这仍足以证明：只要普通分支的独立前提允许，原共用距离会接受64而当前32会拒绝；它是条件已清楚的协议兼容风险，不是完整GUI可达验收。

新增JSON字段`ordinary_cases`分别保存原events、collision_adapter_result=1、real_collision_or_path_verified=false及真实server拒绝。既有血手印条目保持；没有重写所属原研究脚本或将这些case混作其既有48套。

本批不新增外网检索：任务是审计新原执行证据的推论，原客户端直接发送已能实测；旧官方资料没有距离数字且不需要再次泛搜来覆盖新的本地一手结果。

## 复现、方法与未验证范围

结构化证据记录全部native events、原helper源码SHA256、NpcScene/交互规则/政策的当前SHA256、输入点、原setter输出、两种server结果及原资源散列。独立复现核心调用：

```python
case=inspect_approach(0,0,collision=0,template=10498,
    npc_model_point=(2502,970),actor_model_point=(2502,1032))
# 需先用原11f6480确认这两个模型点；本报告已实际执行。
key=next(e['npc_key'] for e in case['events'] if 'visit_send' in e)
# 当前NpcScene绑定key到原placement13，Location=(1006,1668,1032)
# 调真实interact(expected=current, active, 有效deadline)：现32/48均range拒绝。
```

research回到原逻辑→模型正向consumer及原发包，不只相信相对坐标表；diagnosing-bugs使用上述实际红反馈，先最小化单NPC/单位置、再与真实当前Interface对照，不改native门槛造绿。首个尝试沿旧helper字符串寻找相对fixture时因NPC窗口已新增绝对位置公共参数而断言停止；未改原文件，随后改用新公开Interface完成本批正式执行，未将失败尝试计入成功证据。

codebase-design沿用已完整读取的方法，把未来距离判定演进集中于所属NPC Module，避免测试端/任务端各自补临时半径。只执行血手印例、追加两普通模板例及一条短DDA；未重跑48矩阵或其它修理/战斗批次。

未验证：原服务端完整准入、完整鼠标命中/自动寻路/模型backend、其它NPC类别和状态、此新设计实施/发布、真人GUI与网络现场。本批结果足以提出具体兼容修复，但没有把来源核验、服务端设计、实现与实测合并成一个完成状态。

# 原NPC导航到运动完成与访问发送

2026-10-23；本地端游1.6.1原映像离线执行。本批遵循根AGENTS、ARCHITECTURE、DESIGN_AUTHORITY，沿用Matt Pocock research的后台第一方追溯、diagnosing-bugs的可重复反馈和夹具单变量校验、codebase-design的公开入口Seam与显式Adapter。只新增本独占脚本、本文与JSON；未改上一批13例、生产Module、共享入口或政策，未操作游戏、GUI、服务、真实存档、战斗或网络。

产物：[research_world_npc_approach_motion.py](../research_world_npc_approach_motion.py)、[两例原生结果](world-npc-approach-motion.json)。原映像SHA256为`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。JSON记录本脚本、复用脚本、原PFS条目哈希及关键原指令字节。复用既有[原点击到达夹具](../verify_world_click_arrival_native.py)和[原阻挡目标纠正夹具](../verify_world_blocked_goal_adjustment.py)，没有修改它们。

## 本批实际闭合的范围

**两个实际最终候选均已从公开导航入口，自然运行至原路径规划、同一actor更新、到达回调与CVisitNpc发送。** 没有在host设置到达状态、注入到达事件、直接调用角色移动、完成consumer或Visit来拼接流程。Scene按模板取实体仍是明确Adapter；所以这是限定场景夹具下的原指令链，不是完整客户端场景注册/GUI验收。

原调用链：

```text
1142620(auto,1664,960,1006,10498,0,0,1)
  → 1141f90 / 原保护跳转与consumer
  → 1215410 call 12143b0(x,y,1)
  → 原目标阻挡/区域检查
  → 11f8800 → actor虚槽+170 / 652a40 → 6bc2f0
  → 6138d0 → 6212f0原规划 → 原路径压缩与队列
  → 原CRoleMove构造/发送
  → host只提交有限actor tick：655c80 → 6bc7a0
  → 原engine event → 81c670 → 11d57f0 → 1217580
  → 120c350原base callback → 原STOP
  → 1217670 call 12172f0
  → Scene模板查询11d1870（Adapter返回已布置NPC）
  → 1217433 call 1215790 → 原保护链 → 120eea0 → 原CVisit发送
```

上一批[WORLD_NPC_APPROACH_NATIVE](WORLD_NPC_APPROACH_NATIVE.md)在`12143b0`入口停止；本批补上它之后的部分。另一个窗口的[NPC_APPROACH_NATIVE_RESEARCH](NPC_APPROACH_NATIVE_RESEARCH.md)已验证访问距离，本批只观察自然走到那一比较的两个新值，没有重做其48例或重新制定半径。

## 原资源与输入身份

本脚本重新读取并CRC验证`config.pfs/autoconfig/knight.gsp.npc.cnpcconfig.xml`、`map.pfs/map_1006_jiaxing/npc.xml`、该图`maze.dat`及`map.rmp`，BXML解码核对10498。原配置`xPos104/yPos60/mapid1006`经原导航消费对应`1664,960`；原placement为`1668,970`。脚本没有用placement替换导航目标。原指令乘16入口的来源见[BLOODMARK_INTERACTION_DISTANCE_RESEARCH](BLOODMARK_INTERACTION_DISTANCE_RESEARCH.md)。

source初态沿用上一批红例的逻辑`360,2264`；原model/path存储`540,2264`。这一批执行原主角位置getter，没有沿用上一批“整段位置getter直接返回常数”的Adapter。NPC夹具使用真实CNpc虚表`22985e4`，model使用原actor虚表`2462544`，初始化原model坐标`2502,970`，之后通过原`11f6450/11f6540`等getter消费。这里的初态布局由host建立，并非声称执行了完整CNpc构造/场景注册。

首层rand固定radius1/方向0；第二层只取上一批已证的两组：radius1/方向0与radius3/方向1。rand Adapter供应整数，原余数、扫描、mask筛选、失败回退及实际最终选择仍执行原指令。NPC实例key为明确的夹具非负q64 `0x5060708010203040`，并非原服务器捕获的真实角色/实体数据。

## 目标确实会再纠正，然后落到格中心

| 第二helper实际传入12143b0 | 原移动入口交11f8800 | 原规划最终队列端点 | 距placement1668,970 | 原访问整数距离 |
|---|---|---|---:|---:|
|1664,960（mask1阻挡）|1664,1008|1672,1016|46.1736|3，原比较`<13`通过|
|1616,1008（mask1可走）|1616,1008|1624,1016|63.6553|4，原比较`<13`通过|

第一例原`1214449`目标查询为blocked，`121447a`替代mask8查询也blocked。`1214502..12145bd`原搜索按16像素步长，实际候选依次为`1664,976`、`1648,960`、`1664,992`、`1648,976`、`1632,960`、`1664,1008`，最后一项首次clear。然后原`121491d`许可及`1214930`的`11f8800`调用均运行，传入修正后的`1664,1008`。

第二例目标初查clear，未运行上述纠正循环；`11f8800`仍收到`1616,1008`。两例各自仅有这一次`11f8800`调用，没有夹具残余的0,0重规划。

原wrapper/kernel输出格中心，保存在同一engine与character未来队列，未由host填路径：

- 第一例：`1032,1560 → 1672,1016`。
- 第二例：`984,1608 → 1592,1080 → 1624,1016`。

所以“helper给了哪个点”“角色入口修正哪个点”“原规划最终走到哪个格中心”是三层不同事实。第二例最终仍在placement欧氏48外，且原自然访问比较通过；这提供了原链反例，**不把63.6553或本例整数4升级成通用半径**。原服务器交互规则、所有NPC/随机分支仍不是本批结论。

## 到达、role+314与真实发送顺序

`12153d6..12153e9`在调用移动前由原指令保存NPC模板到role+314及metadata到+318/+31c。两例在入口观察到314=10498；初始导航返回时只捕获第一段MOVE，还没有Visit。

后续每个更新都从原actor入口`655c80`执行，使用原`6529b0`设置1.0倍率、有限clock/delta `[2000,1000] [3000,1000] [4000,1000] [4001,1]`。这些是确定性夹具输入，不代表原服务器速度公式或真实时间单位。原`6bc7a0`改变位置、消耗节点，自然发engine event1；host没有写当前位置、队列节点或“已到达”标志。

`1217580`原callback先运行`120c350`。最终队列为空时，原base链经`1218000/1217f00`发送STOP并清history；随后原`1217650..1217675`调用`12172f0`。本批显式取消复用夹具对`12172f0`的旧Adapter，保留其完整原体执行。

该consumer的原逻辑：

- `121737a..121739b`检查世界模式和App模式。
- `12173a1`读role+314；10499另走特例，本例10498进入普通后续分支。
- +318/+31c非零：`12173eb..1217418`用q64 key调用`11d5260`，再核实体+150模板等于314，才调用Visit，并清metadata。**这条非零metadata分支本批只静态确认，未执行。**
- +318/+31c均零（本例）：`1217420..1217433`以模板调用`11d1870`，返回非空实体则调用`1215790`；`1217438`清role+314。

`12172f0`也有别的调用者（例如移动失败分支），因此不将它命名为“所有情况下只在到达才调用”的函数。本批的调用来源明确为原actor完成回调，caller return=`1217675`；原Visit入口caller return=`1217438`。

本例`11d1870(10498)`的Adapter返回预布置NPC；之后原保护访问链、真实实体getter、原距离比较`29d6f58`、真实`120eea0`构造及原发送全部执行。自然消息序列：

- 第一例：`CRoleMove ×2 → CRoleStop(0xc0faa) → CVisitNpc(0xc2329) → 0xc0fa7`。
- 第二例：`CRoleMove ×3 → CRoleStop → CVisitNpc → 0xc0fa7`。

后包0xc0fa7只作为opaque观察，不在本批赋予业务身份或自行发包。MOVE/STOP沿用原live对象marshal；Visit在发送Seam复制原构造的16字节对象后，以原marshal`e52020`输出`5060708010203040`，再经原decoder`db3500`核key完全一致。**没有host构造Visit线包、调用Visit入口或替原consumer决定是否访问。** 最终314=0、engine/character未来队列与history均空，位置保持上述原端点。

## Adapter与夹具修正

反馈从只在kernel中途耗尽150000指令预算开始；本新夹具对每次原入口设4000000指令上限，只有自然返回且端点/顺序/清理均满足才通过。不是以“未崩溃”判成功。

本批发现并排除了两项host初态污染：

1. 原路径堆会增长至`0x535bxxx`。初版将113664字节maze放`0x5300000`，遭原堆覆盖，改变中间点；现独立映射到`0x5400000`，与原堆预算上限隔离，每例结束逐字节核对maze未变。**只有maze未变的最终JSON是交付证据；中间试跑不作为路径定值。** 原数据未改。
2. 复用点击夹具未初始化role+140等不相关action坐标，零值使原base callback误认为有排队0,0目标。原base constructor `120a364`将EAX=-1，`120a3c9..120a3fd`写+140..15c；新夹具按这组原默认值初始化。并按原MainCharacter constructor `12198b9`后续初始化+330/+334=-1。最终断言只有一次真实导航到`11f8800`，无host用额外重规划制造成功。

研究Module的Interface为本脚本入口，内部`Motion.navigate()`只调用公开`1142620`，后续`actor_tick()`只调用真实actor tick；寻路/到达/访问的决定留在原指令内。输入和实现之间的Seam有明确用途：

- 环境Adapter：level=10、普通非门派受限场景、空auto路由树、空动态区域表、初始化scene/actor/model和原网格内存、1.0速度倍率、固定rand/clock。
- 场景Adapter：actor→role关联、`11d1870`按模板取本夹具NPC、无其他特殊实体；**未执行原Scene实体容器注册/查找，也未证明重复模板时该getter如何选择实例。**
- 继承Adapter：CRT分配/释放、安全cookie、sqrt ABI、日志/字符串、若干动画/外观/无render效果依赖、engine额外navmesh/world查询、网络sender成功返回。完整函数列表及实现可按JSON中的dependency脚本哈希复核；`12172f0/120c350/1174f80`等本链关键函数明确执行原体，未沿用相应旧短路。
- 发送Adapter只捕获原对象并返回成功，没有真实socket/加密投递。mouse设备Adapter虽存在于继承类，本任务入口未使用鼠标输入。

## 复跑与未验证

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' revival/research_world_npc_approach_motion.py
```

两例断言分别检查helper传入目标、原纠正结果、唯一actor规划调用、规划终点、初始无Visit、原到达后空队列、MOVE/STOP/Visit顺序、原距离3/4、Visit真实key编解码及maze未变。不存在新生产补丁。

未验证：完整App frame/OS点击或GUI可见性、真实渲染/动画资源、原服务器速度/时间、在线网络、Scene实际注册/模板重复选择、非零metadata实例key分支、普通NPC所有类型、跨地图/私有实例、全部rand组合、所有mask/动态障碍/区域表及失败预算。当前新证据可供主策划和NPC所有者修正接近流程与访问规则的证据范围，不能单凭两例宣布全NPC交互已恢复。

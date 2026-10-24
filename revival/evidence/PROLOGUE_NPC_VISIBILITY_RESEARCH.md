# 序章 DisPlayNPCID：本地可见性、创建次序与服务器边界

本批为 research Skill 的后台委派研究，唯一写入本文件。只读原 PFS/BXML、原 native-image 和公开 world_npcs 源码；不操作当前客户端、在线服、真实数据库，不运行 AI8001 或其他战斗。本文件的 `client_verified` 指原资源及隔离原指令证据，不代表 GUI 已实测或生产已接线。

## 可直接用于接线的结论

1. **DisPlayNPCID 确实参与原客户端实体可见性，并非只有任务图标。** 列表成员经任务状态计算器得到本地 NPC mark；对本批 `hide=1` 的静态 NPC，mark0 隐藏，mark1/3/6 显示。mark 与 Scenario bean 的 state 是两个不同枚举，不能互换。
2. **本批列表不是服务器增删 NPC 的名单。** 原 accept 另有只对 `npctype=10` 生效的本地 type7 实体创建路径；本批说书人、血手印、梦魇均 `npctype=4`，不走该创建。静态实体保留在场景中，由可见性设置器隐藏/显示。
3. **任务先到、NPC 后到的 CNpc 创建路径也会重算。** 原创建成功后跳回与已有实体更新共用的 `1258df0 → 11fe390`；实体先到时，accept/state refresh 又会更新已有目标和列表实体。不能把创建时一次求得的隐藏状态永久缓存。
4. **100106 completed / 100107 active0 时，1501 说书人10908本地显示。** 显示依据是100107的 ActiveNpc10908，其原 mark 为3；100106自己的列表是10083，并不是10908。仅有100106 active 而无100107时，10908没有本批任务引用，隔离样本 mark0。
5. **100179 active0/ready3 时，10908显示，10910/11/12也显示。** 10908是目标，原 mark6；三怪来自 DisPlay 列表，原 mark1。100179移除且无其他引用时归mark0；但原唯一后继100190仍是 ActiveNpc10908、DisPlay=[10910,10911,10912]，正常同步后继会继续显示。不得把“100179完成”实现成三怪永久删除/隐藏。
6. **这些事实只决定本地表现。** 服务器 NPC 存在、entity key绑定、当前实例/AOI、交互距离、任务授权、正式战斗准入仍属各自所有者。客户端显隐不能替代1501私有实例隔离，不能令公共场景里的同模板NPC跨角色共享交互许可。
7. **源场景说书人10083/10491是hide5，不能套hide1的立即隐藏。** 原state1移除bean并重算列表，但该列表刷新用flag0；mark0/hide5/flag0不改原可见值，初建或批量重算的flag1才会隐藏。已显示的源说书人不因这一段state1列表刷新就必然消失。

## 一手来源与完整性

原映像为 `revival/evidence/native-image.bin`，VA基址0x400000，长度50675712，SHA256：
`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

本批直接重读以下原PFS成员并BXML解码，未以派生catalog替代原表。CRC列为原成员CRC32，SHA针对解包后的原成员字节。

| 包 / 成员 | 字节数 | CRC32 | SHA256 |
|---|---:|---|---|
| config.pfs / autoconfig/knight.gsp.task.cmainmissioninfo.xml | 2026233 | 3f7ab7b3 | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |
| config.pfs / autoconfig/knight.gsp.npc.cnpcconfig.xml | 619832 | cc437e13 | b4fc5d440380fb535a36b8e5315c5a1bf10a99f550f5bfde55bd156fca864f85 |
| config.pfs / autoconfig/knight.gsp.map.cmapconfig.xml | 91110 | 3325016f | 374d400f933a74e83d402c8da948fef47823e7f92344ccb660414edfb87a1814 |
| map.pfs / map_1006_jiaxing/npc.xml | 3571 | 51217023 | 72b66cc70e41d78997fb8369c74c5f21a69f500e790797718a41d56ff857752c |
| map.pfs / fubenjiaxing/npc.xml | 888 | 06370594 | 3e96b678f8213459052fcf8c9fccc9c1eb7222ac33672d2a966600513f7b32fa |

## 43路线汇入的十组原节点

43条原角色/门派创建路线的逐条原Post边，见同源的 [PROLOGUE_FIRST_SKILL_RESEARCH.md](PROLOGUE_FIRST_SKILL_RESEARCH.md)；本批重读以下30节点及十个技能后继的原列表，没有按ID规律计算。旧101001→101002→101003→101004族仍保留，不混成这十组，也不将其改向100179。

| 原门派 | 血手印节点 / DisPlay | 第一战 / DisPlay | 掌握技能 / DisPlay | 技能原唯一后继 |
|---|---|---|---|---|
| 古墓11 | 100106 / [10083] | 100107 / [10909] | 100179 / [10910,10911,10912] | 100190 |
| 丐帮12 | 100206 / [10491] | 100205 / [10909] | 100279 / 同上 | 100290 |
| 密宗13 | 100306 / [10491] | 100305 / [10909] | 100379 / 同上 | 100390 |
| 白驼14 | 100406 / [10083] | 100405 / [10909] | 100479 / 同上 | 100490 |
| 大理15 | 100506 / [10491] | 100505 / [10909] | 100579 / 同上 | 100590 |
| 全真16 | 100606 / [10083] | 100605 / [10909] | 100679 / 同上 | 100690 |
| 桃花17 | 100706 / [10491] | 100705 / [10909] | 100779 / 同上 | 100790 |
| 绝情18 | 100806 / [10083] | 100805 / [10909] | 100879 / 同上 | 100890 |
| 百花19 | 100906 / [10083] | 100905 / [10909] | 100979 / 同上 | 100990 |
| 少林111 | 103206 / [10083] | 103207 / [10909] | 103279 / 同上 | 103290 |

血手印十行均 type10、ActiveNpc10498/Map1006、ProcessBarTime3、JumpType3→Map1501/(63,79)，有Note。第一战十行均type40、ActiveNpc10908/Map1501、AI8001。掌握技能十行均type10、ActiveNpc10908/Map1501、ProcessBarTime1、无Finish/Note/Animation/Jump。技能后继十行均type40、ActiveNpc10908/Map1501，DisPlay同为三只梦魇；例如100190原AI8027。这些字段不批准运行该战斗或自动授技能。

### 原 NPC 定义与实际摆放

| NPC / 名称 | 原map / npctype / hide | 原npc.xml posx,posy,dir |
|---|---|---|
| 10083 说书人 | 1006 / 4 / 5 | 348,2244,3 |
| 10491 说书人 | 1006 / 4 / 5 | 1538,2368,5 |
| 10498 血手印 | 1006 / 4 / 1 | 1668,970,4 |
| 10908 说书人 | 1501 / 4 / 1 | 1049,1559,5 |
| 10909 梦魇杀手 | 1501 / 4 / 1 | 919,1613,3 |
| 10910 梦魇邪兽 | 1501 / 4 / 1 | 860,1735,1 |
| 10911 梦魇邪兽 | 1501 / 4 / 1 | 858,1556,3 |
| 10912 梦魇邪兽 | 1501 / 4 / 1 | 1075,1733,7 |

1501资源目录是fubenjiaxing；1006是map_1006_jiaxing。这里引用实际原摆放像素，不以cnpcconfig里的xPos/yPos替换。`world_npcs.load_placements`也是按world目录中的原posx/posy读摆放；`NpcScene`按address/map/placement与服务器entity key绑定。只读此公开契约，没有修改或调用其spawn/bind/interact。

## 字段解析到真正的可见性设置器

### 1. 原拼写和内存布局

- UTF16 `DisPlayNPCID` 位于0x226bd28；`0xbb6928`压入该字段名做XML子节点匹配，存在时`0xbb693b lea eax,[esi+0x114]`，随后进入原int-vector读取路径（0xbb6afb）。
- 这是配置对象+0x114的vector，元素begin位于+0x118，end位于+0x11c。下面所有循环均按4字节整数元素读取，不是NPCkey，也不携带显隐操作码。
- NPC原`hide`字段名0x2265018由0xbaeccb读取，0xbaecf7写入NPC config+0x108。CNpc init `0x1201c44..0x1201c5d`取对应cnpcconfig并复制到entity+0x150；原复制器`0x11f30e5..0x11f30eb`明确复制+0x108，因此entity+0x258就是原hide。

### 2. 任务集合到本地 NPC mark：0x1258df0

- `0x1258e6f..0x1258ecb`扫描Scenario active list（manager+0x24），按bean taskID取原任务配置。
- `0x1258ecd..0x1258ed7`先匹配ActiveInfoNpcID（config+0x168）。MissionType/10==4在`0x1258ef0..0x1258ef3`跳0x1259956，返回**mark3**，所以100107/100190的10908为3。
- 其他目标NPC，如果taskID处于100001..199999，`0x1258ef9..0x1259027`返回**mark6**，所以100106的10498、100179的10908为6。这一分支对本批不依赖bean.state0还是3。
- 非目标NPC在`0x1258f52..0x125901f`扫描DisPlay列表；命中且不等于ActiveNpc时，`0x1259005..0x1259015`记录**mark1**。本批列表ID不触发0x2b62特例，也不属于0x18e7c/0x30f9e/0x3351a三个state3特例。
- 函数继续查看其他任务集合；最终无其他引用时，0x1259bec返回累积mark（默认0）。因此“移除一个任务后一定隐藏”只在不存在其他有效引用时成立。本文不推断任意多任务冲突时的全局优先级。

### 3. mark 不是只有问号：0x11fe390 → vt+0x30

- CNpc原vtable0x22985e4的+0x30指向**0x11f6ee0**。
- `0x11fe3e9..0x11fe3f0`保存mark到entity+0x144，经0x11fe6d8跳表分支。
- mark0：`0x11fe43b..0x11fe450`在hide==1时调用vt+0x30(false)。hide>1另受第二参数flag1约束（0x11fe455..473），因此不把10083/10491的hide5直接套成hide1。
- mark1：`0x11fe478..0x11fe490`在hide>=1时调用vt+0x30(true)。mark3的同类显示调用位于0x11fe4da..4ec，mark6在0x11fe5a6..5b8；之后的任务标记文字是另一层表现。
- 真正setter `0x11f6eef`写**entity+0x18可见byte**，并在0x11f6ef2..0x11f6f54向模型(entity+48/+44)和附属对象传播bool。原指令足以否定“只改任务图标”的解释。
- 电影管理器存在且byte+0x3c==1时，0x11fe3c9..3e4先强制隐藏，绕过正常mark分支。这是另一重客户端表现覆盖；正常任务可见规则不保证电影播放途中显示。

## 接取、刷新、完成分别怎样消费

### SAcceptScenarioQuest：不存在才加入

原vtable0x227df7c，Process **0x125d5c0**。0x125d5c3取taskID，调用1257ac0；已有同ID active bean时直接返回。缺失时将内层bean交给**0x125d070**加入active列表。

新加入后，0x125d12c..137为ActiveNpc调用125a950；0x125d1c3..247遍历DisPlay：0x125d20b调用125a950(0,0,npcID)，0x125d217调用1132590(npcID)。循环没有对本批incoming state0/3作差别限制。ID>=14000另有11fc220调用，本批列表均低于门槛。

125a950调用1258df0，并将结果交11fe390；目标实体按NPCkey或ID查找，同时更新小地图。**重复SAccept不是现有bean的状态更新接口**；不能用重复accept期待刷新已经存在的列表/状态。

### SRefreshScenarioQuestState：state0/3重算，state1先移除再重算

原vtable0x227e4e0，Process **0x125ea00**→125e660；普通Scenario分支0x125e6c0..6c6进入**0x125c020**。

| 条件 | 具体原路径 |
|---|---|
| 已有bean、state0或3 | 0x125c0ee..0f5写bean.state；0x125c367..377更新ActiveNpc，0x125c399..3eb遍历DisPlay→125aa10。不会因ready3移除本批列表 |
| 已有bean、state1 | 0x125c0fe..105先125bb30移除active bean；0x125c10a..117重算ActiveNpc；0x125c124..166逐项125aa10，故使用的是移除后的当前任务集合 |
| state1后置表现 | 0x125c168起继续Finish→Note→fallback，较后的0x125c240..286再对列表调用1130980；本地显示更新和对白/动画后置不能混称NPC永久删除 |
| 已有bean、state-2移除 | 0x125c2c4..365有相应重算/1130980路径；本文不赋予该值业务授权语义 |
| 无bean却收到state1 | 0x125c04d..0e9走Finish/Note/fallback等，不进入上述active-bean列表移除循环。不能把重复state1当完整显隐重建 |

125aa10在0x125aa23重新计算mark，扫描scene+0x68的NPC实体；0x125aa91按entity+0x150匹配NPC模板ID，0x125aaa0调用11fe390(mark,flag0)。所以实体先到也能随任务变化重算。本批hide1可隐藏；不能据此声称所有hide>1的NPC在flag0路径都会隐藏。

Scenario bean **state2是failed**，不是正常active；尽管本批显隐计算的部分分支不检查beanstate，也不能据此投影active2。正常0/ready3/移除1沿项目已确认枚举。

### 另一条只对type10 NPC创建/删除的路径

1132590经89df90取NPC config；**0x11325b7检查config+8的npctype==10**才继续。它登记角色manager+0x260的本地列表，并经11da920建立scene type7实体。1130980移除该登记，并经11d55b0(type7,ID)删除本地type7实体。本批八个表列NPC全为npctype4，不走该创建，也不会因这段type7删除而删除对应静态type1 CNpc。

0x1255e70完成fallback只按Animation/Jump及ActiveNpc处理，其对ActiveNpc的11fcc50调用不是读取DisPlay列表的通用删除函数。不能把函数位置接近state1 handler或字段名当作“删除所有列表NPC”的证据。

## 入场创建与任务先后次序

**CNpc入口0x11d9c70两条路径最终汇合：**

1. `0x11d9cbc`按64位key查询已存在实体。已存在则0x11d9ccd..cd8调用vt+0x184更新，再到0x11d9cda。
2. 不存在跳**0x11d9ed8**分配0x2d8字节，0x11d9ef7调用CNpc构造12017f0；0x11d9f1f调用vt+0x184（1201bd0 init）。成功则0x11d9f25..f2e插入scene+0x68，**0x11d9f30跳回0x11d9cda**。
3. 共用段0x11d9cda..cea压入模板ID和完整key，**0x11d9ceb调用1258df0**；**0x11d9cf7调用11fe390(mark,flag1)**。

因此对该正常CNpc创建/更新入口，已有当前task bean时，实体初建后就采用当前任务集合的mark；实体先到、任务后到则由accept/refresh消费者重算。这是两条实际原调用链，不是靠约定下发顺序猜测。

另有场景批量恢复可见性 **0x11d3620**：0x11d362b先作场景show，0x11d366c..693逐个读取NPC模板ID/key，调用1258df0后11fe390(flag1)。本批确切找到的调用者0x12c0a4d位于电影结束路径：此前构造0xc0018并清movie byte+3c。**不把这个批量函数冒称“所有地图加载必调”**。

尚未把原map.pfs静态场景loader的每个首次show变体全部闭合，也未GUI验证网络时序。上面已证明的两种次序严格限正常CNpc创建入口及任务更新；不能扩大为任何脚本实体/任意场景加载路径皆无时序问题。

## 少量隔离原指令验证

只在Unicorn映射原DATA中执行原**完整1258df0**；合成单一active bean和四个空/单元素容器，配置getter返回原字段对应的合成内存，未模拟服务器规则。manager+0x18/+0x24/+0x30/+0x3c各有自循环sentinel；active node+0xc为taskID、+0x10为state。NPCkey为0，匹配原静态ID路径。引擎、模型、网络、真实DB均不参与。

| 单一active任务（state0） | 10498 | 10083 | 10908 | 10909 | 10910 | 10911 | 10912 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 100106(type10,target10498,list10083) | 6 | 1 | 0 | 0 | 0 | 0 | 0 |
| 100107(type40,target10908,list10909) | 0 | 0 | 3 | 1 | 0 | 0 | 0 |
| 100179(type10,target10908,list三怪) | 0 | 0 | 6 | 0 | 1 | 1 | 1 |
| 移除全部active bean、其他容器均空 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

另直接执行11fe390中mark0/1/3/6对应的可见性分支，虚表+30保留**原11f6ee0**，hide=1、模型/附件为空，在首次文字资源边界前停止：entity+18分别得到**0/1/1/1**。这验证实际bool写入，没有借stub伪造显示结果。state3与state0在本批分支相同另由上述原条件逐支闭合；未将它当整个任务UI的同义状态。

补充源说书人最小样本：hide=5、mark0、初始可见byte=1，执行原0x11fe43b..0x11fe5f3并保留原setter，flag0结果仍1，flag1结果0。这只证所查刷新/初建分支差异，未外推hide5的所有其他消费者。

最小计算探针可复用`research_task_jiaxing_scenario.Probe`的离线内存/lookup adapter；本批以内联python -B执行，没有另建脚本。关键构造如下，便于复核此次数据适配范围：

```python
# super().__init__(quest_id) 已映射原DATA，原getter只返回合成task config。
self.w(self.task + 0x164, mission_type, active_npc)
self.w(self.task + 0x118, display_begin, display_begin + 4*len(display))
self.w(display_begin, *display)
for offset in (0x18, 0x24, 0x30, 0x3c):
    head = 0x500a000 + offset*16
    self.w(self.manager + offset, 0, head, 0)
    self.w(head, head, head)
    if offset == 0x24 and present:
        node = 0x500c000
        self.w(head, node, node)
        self.w(node, head, head, 0, quest_id, 0)
self.w(self.stack, return_sentinel, 0, 0, queried_npc_id)
# ECX=manager, ESP=stack；执行1258df0到return_sentinel，读EAX。
```

## 接线边界、方法与未验证范围

- research实际方法：原包重读/CRC及SHA→BXML真实行与原Post列表→固定字段parser/消费者→指定callee有限xref→单bean原指令及可见setter小探针。没有在线搜索，因为原资源/原代码已直接回答客户端事实。
- 决定影响：DisPlay用于本地任务可见性；静态type4与本地type7创建分开；任务状态与NPC mark分开；移除后按当前集合重算，不能为100179编造永久隐藏规则。
- 跨模块边界：任务所有者提供当前可信bean集合/状态投影；地图实例所有者保持NPCkey/摆放/归属/距离授权，正式战斗另受准入控制。本文只提供原证，不修改或发布服务器策略。
- 当前结算接线只读核对：`task_domain.py`完成计划把原DisPlayNPCID保留在continuation_fields；`task_rewards.update_reward_delivery`将非空且未列入continuation_resolved_fields的字段计入followups_pending。原state1的确会移除bean并重算该列表，**但客户端可见性委托不等于服务器创建/删除待办已经兑现**。本批不改此pending状态，也不自行标resolved；是否把已委托的本地表现记为resolved须由集成方明确消费者/投递契约并另行裁定，不能用本报告偷偷消除资产/后继待办。
- 当前unknown：原服1501实例分配/复用、服务器是否另按阶段筛NPC、任意多任务冲突优先级、所有静态loader及脚本首次show变体、电影/对白中的完整可见时序、真实SAddUserScreen与accept乱序GUI表现。未读取在线角色或推进章节来填这些空白。
- 产物/验证：仅本Markdown；原函数探针上述样本通过。没有源码实现、生产导入检查、在线协议投递或GUI实测，不能把本报告标成现场恢复成功。

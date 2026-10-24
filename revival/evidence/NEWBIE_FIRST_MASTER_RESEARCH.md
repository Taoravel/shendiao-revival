# 首位门派师父：三句对白、武器选择卡与装备目标

2026-10-23；本地端游1.6.1 / 网络版本601。遵循 research、codebase-design及当前ARCHITECTURE / DESIGN_AUTHORITY，只读原包与既有原映像。先读 [research_newbie_equipment.py](../research_newbie_equipment.py)、[newbie-equipment-sources.json](../catalogs/newbie-equipment-sources.json)、[TASK_REWARD_VARIANTS_RESEARCH.md](TASK_REWARD_VARIANTS_RESEARCH.md)，再核对世界窗口新增的 [WORLD_MASTER_CARD_PROTOCOL.md](WORLD_MASTER_CARD_PROTOCOL.md)。本轮只新增本报告，不修改领域、共享入口、目录或设计，不启动客户端/服务、不发包、不运行战斗或大回归，不重复世界窗口的codec探针。

## 首要结论

**43条route的首师父任务虽为type10，但都不是普通空对白任务：每条有3句原对白，ScenarioInfoAnimationID对应CCardEffect武器选择卡，不能按空对白完成，也不能把它当成root的CG电影。**

**不存在“200xx动画结束也回同一个CEndPlayCG、只换授权阶段”的证据。** 该切片的原对白后上行是 **CQuestDialogEnd `0xc4a52` + questID**；独立下行为 **SPlayCardEffect `0xc001c` + effectID**，两个按钮发 **CGetCardItem `0xc041f` + effectID + itemID**。它们与root的SStartPlayCG/CEndPlayCG是不同协议和消费者。

**赠武器来源已从另一张原表找回：** 全部43张选择卡明确二选一给49001..49010中的两件，每个选项数量1。CItemAttr对这10件均写着“1级见师父主线任务奖励的武器”。任务本身没有RewardItem列表的事实继续保留；不是据空列表臆造401xx普通武器，也不是借102071的后续奖励补本次来源。**绑定、实际服务器发卡时点、任务完成与选择提交的原服事务顺序仍未知。**

## 原始资料与核验范围

通过 [pfs.py](../pfs.py) 本轮直接读取 `D:/神雕侠侣/artres/config.pfs`，检查本地头/目录一致、解压长度和CRC后BXML解码；不是只相信既有JSON：

| autoconfig/包内表 | 行数 / 字节 | CRC32 | SHA-256 |
|---|---:|---|---|
| knight.gsp.task.cmainmissioninfo.xml | 2460 / 2026233 | `3f7ab7b3` | `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706` |
| knight.gsp.task.ccardeffect.xml | 53 / 4855 | `0cd73222` | `1e7cdcb4360d544edc2cfb7e21f228e7079f73167848585d2c0cf1d14566006e` |
| knight.gsp.item.citemattr.xml | 12280 / 4096369 | `a3add081` | `974a3b38049c5f5f7cdae418718ffadd2741d373a5846a40fb71289af25e726f` |
| knight.gsp.item.cequipeffect.xml | 1521 / 467441 | `e354a76d` | `8ef1aacae8d016f875a37a8cf907b16a077b89fa522a87e349dd54d320572fe8` |

原生VA统一来自 [native-image.bin](native-image.bin)，BASE `0x400000`，SHA-256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。本轮用 [native_inspect.py](../native_inspect.py) 静态复查相关分支。既有世界窗口16项原生用例只引用 [world-card-native.json](world-card-native.json) 及WORLD_MASTER_CARD_PROTOCOL，不重复执行，也不把它当本轮完整UI实测。

## 全部43条首师父任务的交叉结果

读取 [newbie-routes.json](../catalogs/newbie-routes.json) 的43条路线，逐项以successor_task_id查原任务，再以ScenarioInfoAnimationID查原CCardEffect：

该既有目录把后继表现字段命名为`successor_movie_id`，这是旧工作名；本批43条的实际值应按**card effect ID**消费。字段名本身不构成CG语义证据，本轮未修改该目录或其调用方。

- 43条全部MissionType=10；ScenarioInfoNpcConversationList长度全部为**3**。
- 43个不同effect全部存在原CCardEffect；相应 `movie/<effectID>.txt` **全部不存在**。结合实际卡UI消费者，可排除在此把200xx当110xx电影脚本的接法；不以“数字在20000段”单独推断种类。
- 每张卡item1/num1和item2/num2都有原值，num1=num2=1；item3=item4=0、num3=num4=0，零项保留。
- 43条任务均无RewardItem属性/子列表，ExpReward、MoneyReward、PetExpReward、SMoney全为**0**，不能把0当缺失奖励补设计经验。
- 10个后继type59仍无RewardItem表。本轮新增CCardEffect来源并不篡改任务原表的空奖励事实。

例：古墓角色9，任务100186，NPC10014/map1100，AnimationID20006；少林角色9，任务103286，NPC13291/map1110，AnimationID20044。原CCardEffect20006完整相关字段为：

```text
id=20006 head=luwushuang
button1=获得伞    weapon1=sidai item1=49009 num1=1
button2=获得环圈  weapon2=huan  item2=49006 num2=1
item3=0 num3=0 item4=0 num4=0 info=古墓云夕
```

`weapon1=sidai`等是原卡面表现值，不能替换item1的真正模板ID。全部43条按角色行分组后的两项选择相同，门派差异保留于各effect头像/信息与来源任务：

| 原角色行ID | 选项1模板 | 选项2模板 |
|---:|---:|---:|
| 1 | 49001 师承的重剑 | 49004 师承的柴刀 |
| 2 | 49002 师承的白纸扇 | 49005 师承的铁剑 |
| 3 | 49003 师承的木枪 | 49001 师承的重剑 |
| 4 | 49004 师承的柴刀 | 49002 师承的白纸扇 |
| 5 | 49005 师承的铁剑 | 49003 师承的木枪 |
| 6 | 49006 师承的铁环 | 49008 师承的绣刃 |
| 7 | 49007 师承的竹弓 | 49010 师承的双铁剑 |
| 8 | 49008 师承的绣刃 | 49007 师承的竹弓 |
| 9 | 49009 师承的油纸伞 | 49006 师承的铁环 |
| 10 | 49010 师承的双铁剑 | 49009 师承的油纸伞 |

CItemAttr49001..49010均level=1、needLevel=1、maxNum=1、使用方式“右键点击穿戴装备”、effectdes为**“1级见师父主线任务奖励的武器”**。CEqipEffect对应roleNeed分别为(1,3)、(2,4)、(3,5)、(4,1)、(5,2)、(6,9)、(7,8)、(8,6)、(9,10)、(10,7)，与两选项对当前角色兼容相符。itemtypeid分别264、520、776、1032、1288、1544、1800、2056、2312、2568；沿已证装备槽公式均为slot0。本轮未重复执行槽位探针。

旧research_newbie_equipment仅筛40100..41099，因此漏了这些490xx“师承”模板；它当时的reward_policy_resolved=false正确反映其范围，不能把候选普通/礼包武器当本次唯一可用物品。本报告补充了原表来源，不改那份目录。原102071的40301/40501等按形象选择奖励是另一个后续任务，见TASK_REWARD_VARIANTS_RESEARCH，不应用于首师父。

**CCardEffect没有绑定字段**；CItemAttr/CEqipEffect的bCanSale=0只表示相应出售限制，不能当作任务绑定1的原始证据。数量1和二选一来自卡配置及按钮取值链；服务器实际按该选择发奖是恢复采用的规则，不等于已取得原服结算二进制。具体绑定策略仍可由主策划明确designed。

## 原NPC对白、后置表现与上行报告

后续原生反馈纠正：本节DialogEnd指令的phase3前提不能外推到首师父phase2 Start读尽。原正常结束只发CCommit；旧“等待End才发卡”接线已被真人卡点及原生反馈反证。详见[FIRST_MASTER_CARD_TRIGGER_AUDIT.md](FIRST_MASTER_CARD_TRIGGER_AUDIT.md)；下面保留原phase3证据作为对照，不作为Start必发End的依据。

沿用已恢复 [TASK_PROTOCOL.md](TASK_PROTOCOL.md) / [WORLD_ENTITY_PROTOCOL.md](WORLD_ENTITY_PROTOCOL.md)：SVisitNpc `0xc232a`按真实npcKey查场景实体，把两份vector交`0x120f4e0 / 0x1635f10`；已接普通任务state3经第二vector进入可交付对白。菜单中的任务ID不是无条件完成证明；NPC实体、地图/距离、当前阶段仍由地图/任务所有者核对。

普通type10提交函数 **`0x1643360`** 用任务表getter`0x89ebd0`取配置，`0x16433a0`检查任务+0x164为0xa；普通提交分支构造 **CCommitScenarioQuest `0xc4a44`**。原布局是BE i32 questID、BE u64 npcKey、BE i32保留选项（16字节）；非空三句原对白不应替换为一项“空对白即交付”的恢复捷径。

对白后结束片段 **`0x1644c1a..0x1644cf8`**：

1. 要求UI局部阶段 **UI+0x60==3**；这里不能把UI阶段3直接等同于wire任务state3。
2. 按UI保存的任务号查原任务配置，`0x1644c39`检查配置+0x2ac（ScenarioInfoAnimationID）>0即走`0x1644cb6`。首师父43条都满足。
3. `0x1644cbd`调用后置表现 **`0x1255e70(config)`**；随后`0x1644cc2..0x1644cd1`在栈上构造 **CQuestDialogEnd `0xc4a52`**，字段是该任务ID，`0x1644ce1..0x1644cf2`经连接发送。该上行是4字节任务号，不是电影ID。

`0x1255e70`对本批200xx且配置+0xc8=0，进入`0x1255e8b..0x1255e8c → 0x12550c0`。后者的30000..59999另一分支不适用于这些200xx；本批走`0x1255105..0x1255110 → Scene::0x11ca790`的普通effect边界。**这条本地表现链没有直接打开CCardEffect卡UI，也没有构造SStartPlayCG。** 原WORLD_MASTER_CARD_PROTOCOL的两项fixture已捕获此分支；本轮静态指令复查一致，未执行GPU资源加载。相同数字同时被另一张效果表/消费者使用，不能据它自动推断武器卡已显示。

状态刷新`SRefreshScenarioQuestState → 0x125c020`在state1有移除任务、对白/后置表现等路径，见旧协议研究。客户端会有状态消费副作用，**不能把服务器发state1这一动作反过来当“玩家已完成对白/领武器”的证明**；原服是在CCommit、CQuestDialogEnd、发卡和领物中的哪一步原子提交任务，本轮无法从客户端源码闭合。

## 选择卡的独立消息与按钮消费者

复用世界窗口已有 [world_card_protocol.py](../world_card_protocol.py) 的纯codec，不复制或改写：

| 消息 | payload与原生身份 |
|---|---|
| SPlayCardEffect `0xc001c` | 4字节BE signed i32 effectID>0；vt`0x22704e0`，构造`0xd54b80`，marshal`0xe40e40`，unmarshal`0xd54c10` |
| CGetCardItem `0xc041f` | 8字节BE i32 effectID + BE i32 itemID；vt`0x2276640`，构造`0xd919d0`，marshal`0xe4c480`，unmarshal`0xd91a70`；不含questID/npcKey/数量/绑定/CG结束状态 |

SPlayCardEffect::Process **`0x1744540`**，`0x1744543 → 0x89eb50`查原CCardEffect表；不存在(id=-1)不显示。200xx小于40000，`0x1744577..0x1744582`经`0x17444a0 → 0x1744070`填充武器卡。配置effectID存UI+0x40，item1/item2从配置+0x90/+0x98存UI+0x44/+0x48。

原按钮 **`0x1743990`**取UI+0x40/+0x44构造并发送CGetCardItem；按钮 **`0x1743a10`**取UI+0x40/+0x48发送同包。两者发送后调用`0x1743740`关卡面，**没有发送CEndPlayCG**。因此按钮2是传item2的真实模板号，不是传“选项索引2”；两件不能同时发放。

本轮没有新的CG脚本或CG结束消费者可补给这些type10。root的CEndPlayCG0xc0018（movieID）继续只归原CG通路，见 [NEW_CHARACTER_OPENING_RESEARCH.md](NEW_CHARACTER_OPENING_RESEARCH.md)；不得拿它代替这里的CQuestDialogEnd或CGetCardItem。

## type59装备目标及未知判定

10个后继目标为100188/100288/100388/100488/100588/100688/100788/100888/100988/103288。它们都为type59，ActiveInfoNpcID/TargetID/TargetNum均0，ScenarioInfoAnimationID=0，地图为对应门派原图。原目的完整短句为：

```xml
<T t="装备师父赠与的"></T><G t="武器" npcid="10390" c="ff33ffff"></G><T t="。"></T>
```

10390是原背包/武器UI引导链接，原NPC表mapid=0，不能据链接在世界刷一个10390实体来交任务。后继分别是100104、100203、100303、100403、100503、100603、100703、100803、100903、103204；原图与边保留于既有newbie-equipment-sources。

客户端原表没有列出该type59必须匹配的具体模板号/物品实例、强化等条件。结合前一节点的选择卡，可以设计“实际穿上本次合法选择所得师承武器”的判定，但这仍是服务器恢复规则，**不能由targetID=0推断任意装备或无需装备即完成**。原CEquipement是另一件装备意图，具体codec已由世界窗口恢复；是否已穿戴须资产所有者提交后发可信装备事件，不让NPC空对白、领物请求或任意客户端报告直接推进type59。

## 官方端游旁证、交接决定与验证边界

本轮定向检索同款端游官方“第一次做任务/师承武器/序章缘起”，取得[官方剧情任务资料（路径日期2012-07-28）](https://sdxl.wanmei.com/info/renwu/script/20120728/133491.shtml)：其序章介绍支持向各门派师父取武器后乘门派车夫去嘉兴的大方向。该来源没有卡ID、两选模板、绑定或发卡精确时点，不能覆盖本地10派/43路线；精确模板优先采用当前原包。未采用手游或《神雕侠侣2》资料。

research实际用于先复用已恢复证据，随后原包43条逐项联查、排除CG脚本、补CCardEffect→490xx→装备适用角色来源，再静态核对对白报告和按钮发送。codebase-design实际影响决定：在现有任务 **Module** 的NPC对白 **Interface** 之后，使用独立选择 **Seam** 关联可信角色/任务/effect及合法二选一项；codec **Adapter** 只负责原8字节，不把未知任务身份塞进包里；物品与装备事务归角色资产所有者。数量与选择集合可取原表，绑定和原服提交时序留给主策划明确设计。

供主策划设计的精确余缺：发卡在CCommit/state1/CQuestDialogEnd的哪一阶段授权；任务完成、选择凭据、物品入包和type59接取如何一次性原子提交；绑定；关闭卡/断线/背包满后的恢复与重试。选择必须校验已保存的源任务/effect/角色与当前授权，按原item1/item2之一发1件，不能任意effect+itemID即发奖，也不能重放再选另一件。原服务器这些事务实现未取得，不能假称已证。

本轮验证仅原包CRC/解码、43条原值与约束核对、列明原指令静态复查及已有报告交叉一致。未执行codec、界面状态机、卡面渲染、服务端实际发奖/穿戴、任务恢复或真实客户端测试；本报告不是新手首师父流程已接入的声明。

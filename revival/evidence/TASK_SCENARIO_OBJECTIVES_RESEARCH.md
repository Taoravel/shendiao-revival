# MissionType50：非新手剧情任务的原生提交与表现

日期：2026-10-23；本地端游1.6.1、网络版本601。方法采用 `D:/User/Documents/Codex/.codex/skills/research/SKILL.md`：本窗口本身是委派的后台研究，追溯原PFS与原映像，一份证据文档交付，不递归委派。已重读 `ARCHITECTURE.md`、`DESIGN_AUTHORITY.md`；本批没有修改任何生产源码、政策、catalog或共享入口，没有启动/操作客户端、在线服、战斗或角色存档。

## 可直接用于恢复的结论

1. **234条type50不是234段CG。** 原表234条中，Animation非零12条（10个已恢复intro root，另102622→10026、206103→10020）；其余222条动画为零。按互斥的表现元数据优先级分为movie12 / NpcConversation18 / FinishConversation142 / Note20 / empty42。这里的“NpcConversation”只是字段名，不证明自动启动。[S1]
2. **存在可用的type50普通NPC提交路径。** active bean的state3→NPC菜单class3→本地NpcConversation；其为空且BranchNote为空时，菜单点击立即落入默认CCommit。该默认分支适用于MissionType50，发送 `0xc4a44 + BE(i32 task_id,u64 npc_key,i32 option=0)`。已执行一例隔离原指令确认，不是按type10猜出来的。[N1、P1]
3. **FinishConversation是state1后的完成表现。** `SRefreshScenarioQuestState(state=1)`移除active bean，然后调用原FinishConversation UI；它不能倒过来作为首次完成授权。服务端先验证合法NPC提交并提交完成/奖励事务，再发state1，与该客户端链相容；何时把任务置ready3仍属服务端规则。[N2]
4. 主表元数据审计的130条“无额外机制finish”中：124条ActiveNpc非零，其中226701/226901为999999；剩余**122条只可称普通NPC提交候选**。另外6条ActiveNpc为零，不能套NPC路径。RequestMissionList等前置、周期资格和真实NPC实例仍须单独校验，不能因为有一句Finish就自动完成。[S1、S4]
5. **无动画18条NpcConversation的通用自动启动入口尚未闭合。** 本次已证实的是NPC菜单路径；未证实SAccept本身、ActiveMap匹配或入场reason自动打开这段对白，也没有确认一个可替代的“自动剧情对白下行”。101x09等带传送节点不能仅凭字段套CQuestDialogEnd完成。[N1、N3、N5]
6. **CEndPlayCG正文是movieID，不是taskID**；10026/10020确有原movie脚本。独立SStartPlayCG会启动电影；任务state1的通用后置函数对这两个小于20000的ID只登记pending值，未直接调用CG管理器，不能把state1当作电影启动下行。[S2、N4]
7. **重复state1会重开FinishConversation/提示/后置处理，即使bean已被移除。** 客户端没有在这一handler用“已完成”去重。state2为failed、state0为normal、state3为ready；禁止继续使用旧active2口径。[N2、P1、S5]

## 一手来源与范围

| 标记 | 来源 | 校验/用途 |
|---|---|---|
| S1 | `artres/config.pfs` → `autoconfig/knight.gsp.task.cmainmissioninfo.xml` | 本批直接PFS长度/CRC检查、完整BXML解码，提取全部234条；raw SHA256 `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706` |
| S2 | 同PFS → `movie/10020.txt`、`movie/10026.txt` | 本批直接CRC检查、UTF-16解码；原脚本身份和语句，不执行脚本 |
| N1–N5 | `revival/evidence/native-image.bin`，base0x400000，文中地址均为VA | SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`；定向反汇编和小段原指令执行 |
| S3 | 已有 `NEW_CHARACTER_OPENING_RESEARCH.md`、`TASK_NEWBIE_COMPLETION_DISPLAY.md`、`TASK_JIAXING_SCENARIO_RESEARCH.md` | 复用CG/后置函数证据，当前结论又对关键分支重读映像；不把历史文档的模糊资源称谓当新证据 |
| S4 | 同批主线程 `task-scenario-catalog.json` | 全234原字段审计与额外机制标记；本窗口直接重读S1独立确认234/12/18/142/20/42及145 NPC、164 Map非零统计。200个元数据候选是审计范围，不是200个获准完成任务 |
| S5 | `TASK_TRACKER_FAILURE_RESEARCH.md`、`DESIGN_AUTHORITY.md` | 当前显示枚举与旧active2纠正；NPC菜单class和tracker显示是不同概念 |

本批未引用手游/神雕侠侣2资料，没有用外部攻略代替原客户端调用事实。原服务端未包含在这些来源中；接取、奖励、完成、传送授权的未知项保持未知。

## S1：静态分组与不能合并的任务族

互斥分组按Animation非零→NpcConversation→FinishConversation→NoteInfo→empty顺序统计。字段出现不等于原服触发规则。

| 表现字段分类 | type50总数 | 无额外机制元数据候选数 | 这些候选的ActiveNpc非零 | 候选ActiveMap非零 |
|---|---:|---:|---:|---:|
| Animation非零 | 12 | 0 | — | — |
| NpcConversation | 18 | 8 | 7 | 7 |
| FinishConversation | 142 | 130 | 124（其中2条999999） | 127 |
| NoteInfo | 20 | 20 | 0 | 0 |
| 无上述本地表现 | 42 | 42 | 4 | 7 |
| 合计 | 234 | 200 | — | — |

全234条ActiveNpc非零145条、ActiveMap非零164条；排除10个intro root之后共224条。所有非intro条目的ProcessBarTime与AIInfoAIID均为0，不代表没有其他资格/后置机制。完整字段与主线程阻挡族保存在S4，不在本文另造第二份catalog。

130个finish候选中ActiveNpc=0的6条：`102317,102392,102490,203501,230801,230901`。124个非零中 `226701,226901` 原值为999999；该值不是“任意NPC”授权。非零124条有26条非空RequestMissionList；本研究未解释这些列表的原服AND/OR或分支资格。

正常NPC样本200101原字段：type50、ActiveNpc10958、ActiveMap1007、矩形全零、Animation0、JumpType0、无NpcConversation/BranchNote、FinishConversation1句，PostMissionList=[200190]。因此它适合证明“空前置对白→CCommit→state1后Finish”的客户端代码路径；不据此声称其领取/后继业务已获原服证明。

18条NpcConversation逐项原字段：

| task_id | ActiveNpc | ActiveMap | JumpType | NpcConversation句数 | 原非空RequestMissionList |
|---:|---:|---:|---:|---:|---|
| 101001 | 0 | 0 | 0 | 3 | 100199,100299,100399,100499,100599,100699,100799,100899,100999 |
| 101109 | 0 | 1004 | 1 | 1 | — |
| 101209 | 0 | 1007 | 1 | 1 | — |
| 101309 | 0 | 1007 | 1 | 1 | — |
| 101409 | 0 | 1007 | 1 | 1 | — |
| 101509 | 0 | 1007 | 1 | 1 | — |
| 101609 | 0 | 1007 | 1 | 1 | — |
| 101709 | 0 | 1007 | 1 | 1 | — |
| 101809 | 0 | 1007 | 1 | 1 | — |
| 101909 | 0 | 1007 | 1 | 1 | — |
| 103309 | 0 | 1004 | 1 | 1 | — |
| 201201 | 10903 | 1002 | 0 | 2 | 102099 |
| 230401 | 13286 | 1007 | 0 | 1 | — |
| 230701 | 999999 | 1007 | 0 | 2 | — |
| 323001 | 13922 | 1007 | 0 | 1 | — |
| 323101 | 13922 | 1007 | 0 | 1 | — |
| 323201 | 13922 | 1007 | 0 | 1 | — |
| 323301 | 13922 | 1007 | 0 | 1 | — |

例如101109的原对白是到达临安后的报名官引导，NpcConversation speaker=[10014]，RewardMapID1007/X179/Y299、JumpType1；但ActiveMap是1004、ActiveNpc0。这些静态字段不能自行证明“地图1007入场自动开始”或“对白结束后才传送”的顺序。四个323x01的活动/周期语义及230401季节资格需另核，不能作为永久普通入口。

## N1：ready3 NPC菜单、空对白与type50的CCommit

已确认调用链：

1. `0x1257b20` 先查active bean。`0x1257b44` 只有type40直接走class3；type50随后在 `0x1257b4d` 检查bean.state==3，是则class3，否则class2。无active/其他候选记录的样本为class1。class2并不证明tracker正常，state2仍是失败显示。
2. NPC菜单点击 `0x1636b81 → 0x164d780`，保存NPCkey和taskID。`0x164d865` 检查class3，`0x164d86c` 设置本地对白UI阶段2，`0x164d873 → 0x164b530`。
3. `0x164b581–0x164b5b8` 用本地UI+0x50的对白序号访问config+0x2e0的NpcConversation。列表为空/读尽时检查BranchNote.length（config+0x2c8）；同为空则 `0x164bb51` 返回al=0。
4. 首次菜单在 `0x164d878–0x164d87e` 因false直接调 `0x1643360`；有对白时，下一句回调 `0x164c3d6–0x164c3ef` 在phase2调用同一函数，读尽后亦调 `0x1643360`。
5. `0x1643360` 读取MissionType；type50不匹配type10/40/12/13/11/17分支，走默认路径。原taskID200101也不匹配此处少数按任务ID特判的UI。
6. `0x16437a8` 检查ProcessBarTime；本批type50均0，进入 `0x16437ca`。`0x16437ce → 0xdd4780` 原构造器明确写vtable0x227d670、type0xc4a44，option+0x18初始化0。`0x16437d3–0x16437ef` 从UI填taskID与64位NPCkey，`0x1643804` 发送。

原协议仍为 `CCommitScenarioQuest=0xc4a44`，wire正文BE `i32 quest_id, u64 npc_key, i32 option`，普通default尾字段0。该包不包含movieID、当前位置或“完成对白已播放成功”。本批没有更改codec；正文布局沿用原协议研究，原构造/发包路径又以P1最小探针核验。

仅将active0同步给客户端，不会让type50自动获得class3；必须由服务器可信状态/策划规则决定ready3，而不能伪造state2或直接把所有type50标ready。选择NPC提交实现时还须使用真实NPCkey、地图/交互凭据、当前任务实例和前置资格。

## N2：state1后Finish/Note/fallback、重复与失败

`SRefreshScenarioQuestState=0xc4a47` 正文BE `(i32 quest_id,i32 state)`；Process `0x125ea00 → 0x125e660 → 0x125c020`。

- active bean存在：`0x125c0f5` 先写bean.state，state1在 `0x125c105 → 0x125bb30` 删除active记录并更新NPC标记；然后 `0x125c168–0x125c19b` 检查FinishConversation（config+0x304/+0x308的vector）并调用 `0x1129af0 → 0x164beb0`。
- Finish UI的 `0x164bf0a–0x164bf10` 设置taskID及本地阶段3，按config+0x300的FinishConversation和FinishNpcID逐句渲染；下一句由 `0x164c3f9–0x164c412` 回到此函数。读尽后 `0x164bf5e–0x164bf7a` 还可显示NoteInfo，再返回false/关闭。
- 没有Finish时：`0x125c1a2–0x125c1be` 检查NoteInfo.length并调 `0x156d130(NoteInfo,1,1,1)`；二者皆无时 `0x125c1c8 → 0x1255e70` 做后置效果处理。
- **无active bean仍处理state1**：`0x125c045–0x125c052` 并未忽略，而在 `0x125c058–0x125c08b` 重走Finish分支，之后同样有Note/fallback。因此重复下发会重复对白；P1捕获两条分支均调用相同Finish UI。
- state2并不进入state1完成表现分支；`0x125c2c4` 还单列state=-2的删除处理。这里未见state2自动停止正在播放的CG。state2的“失败”tracker语义以S5为准，不能把state=-2、2和完成1混在一起。

本地阶段3清理 `0x1644c1a–0x1644cf2` 在满足条件时发送 `CQuestDialogEnd=0xc4a52 + BE i32 quest_id`。条件为AnimationID>0，或JumpType>0，或本地64位task值>300000；其余分支可能仅做NPC场景清理。`0x1644cb6` 先调后置函数，随即发送报告，并非等资源播放自然结束。**并非每个Finish都有此包**；尤其200101这类Animation0、Jump0、taskID<300000的普通finish不满足该分支。

因此142条Finish族的CQuestDialogEnd（若有）是已经收到state1后的UI生命周期事件，不能作为同一个任务的首次完成依据或统一“对白完成扣奖”授权。重试奖励回执也不能无条件重发state1来重播表现；网络投递/重连策略仍需明确设计。

## N3：无动画NpcConversation的自动入口缺口

本次任务/UI代码范围（VA0x1000000–0x1800000）定向扫描的直接call：

| 被调函数 | 发现的直接call地址 |
|---|---|
| 0x164b530 NpcConversation | 0x164c3e0（phase2下一句）、0x164d873（NPC class3菜单） |
| 0x164d780 菜单入口 | 0x1636b81 |
| 0x164beb0 FinishConversation | 0x125c08b（无bean state1）、0x125c19b（有bean state1）、0x164c412（phase3下一句） |

三函数在整个映像的绝对地址引用搜索未返回函数指针引用。该结果约束本次找到的入口，**不声称证明全程序没有间接/其他自动显示路径**。

`SAcceptScenarioQuest` Process `0x125d5c0` 先按taskID找bean，已存在则直接返回；不存在则 `0x125d5e0 → 0x125d070` 插入列表、刷新NPC/DisplayNPC标记、通知观察者等。已跟进 `0x125d247 → 0x125cb80`，后者登记通知/时间并投递回调；未在所查路径闭合到NpcConversation入口。不能把“接包有通知”写成“接包必自动弹对白”。

另定向重读到区检查 `0x1257d50`：`0x1257e2a–0x1257e3b` 检查MissionType余数为6，type50余数0不走后面的矩形自动CCommit分支；该函数不能为type50的ActiveMap/矩形提供同一自动触发依据。已有type56/reach-scene研究不能直接外推给type50。

当前没有确认：101x09/103309的无NPC对白如何开场，SRoleEnterScene reason是否携带所需任务上下文，地图为0/非0在type50启动中的通用分支，以及一个可安全填入当前任务ID的自动对白下行。未发现的包不命名为SNotifyScenarioQuest，也不误用SEnterDialog、活动专用STaskProcess或无关NPC问答包。服务端可继续恢复已确认的NPC提交族，但自动节点需独立原证或主策划明确设计。

## S2/N4：仅剩两条非intro电影任务

| task_id | 原AnimationID | ActiveNpc/Map | 矩形L,T,R,B | PostMissionList | 原movie资源 |
|---:|---:|---|---|---|---|
| 102622 | 10026 | 0 / 0 | 0,0,0,0 | 102623 | `movie/10026.txt` |
| 206103 | 10020 | 0 / 1506 | 1,1,75,120 | 206104 | `movie/10020.txt` |

两条JumpType均0、无NpcConversation/FinishConversation。10026脚本SHA256 `299f1c51d71acabefd8bfc2faadf78cff5e617dd42f76783f9728e59bf83c04c`，含Setmap1242 pos52,62、黑衣人/靛青麟/黄药师、Start/Speak/MoveNPC/Jump/Return/End；10020脚本SHA256 `4fa5ad5b9c087d7c0032d3591d9d698c3da0779767fed3e51066478ce686b054`，是说书人轻功演示，含Setmap、Jump、Return/End。10020首物理行还并列了Setmap1506 pos25,95与Setmap1501 pos99,40，本文不猜解释器对同行第二语句的处理，不从脚本字面推权威传送端点。

**启动协议与字段**：SStartPlayCG0xc0017的原vtable0x22708b0，构造0xd574b0，marshal0xe410e0，decode0xd57540，body为一个BE i32 movie_id。Process `0x12c43b0` 读packet+8，`0x12c43c0 → 0x12c4140`；`0x12c4336` 保存movie_id到CGmanager+0x38、+0x3c设playing、+0x40保存旧场景，`0x12c437a → 0x12c3f10` 装载movie脚本。

**结束协议与限制**：CEndPlayCG0xc0018原vtable0x226fab8、构造0xd4f070、marshal0xe3fd70、decode0xd4f110，body为BE i32 movie_id。清理函数 `0x12c0970` 在playing期间，`0x12c09b2–0x12c09b9` 把manager+0x38复制进packet，`0x12c0a24–0x12c0a3e` 发送。它没有taskID、场景世代、播放nonce或结束原因。已知清理也由失败/跳过/关闭路径调用（如0x12c4383、0x1570bfd、0x1570f9e），不能称该包证明完整观看。

**state1不会直接启动这两部CG**：通用后置 `0x1255e70` 在 `0x1255e75` 读取Animation；10020/10026<20000，在 `0x1255ea3` 存入taskmanager+0x70，后续只是NPC清理；没有直接调用CGmanager。`0x12550c0(0)` 虽可读pending，但对<20000提前返回。因此电影的SStart时序、任务授权、CEnd→完成事务/后继、失败/重登播放恢复均不能仅从任务Animation字段推定。已有intro专用恢复设计不是这两条非intro的原服设计证据。

本批type50没有600xx或200xx的Animation条目。60001的章节特效、师父200xx选择卡分别见S3及 `WORLD_MASTER_CARD_PROTOCOL.md`；不能拿CEndPlayCG覆盖这些资源。旧文档若把200xx笼统叫电影，应按实际消费者修正理解，而不是将所有Animation整数送SStartPlayCG。

## P1：少量必要离线验证与未验证范围

仅以内联Python `-B` 复用已有 `research_task_jiaxing_scenario.Probe`，执行原映像小段，配置/网络/GUI/资源加载在边界由fixture替身截获，没有真实发包、渲染或执行CG。没有新增/修改.py或生成另一份证据JSON。

| 原指令范围/设置 | 捕获结果 |
|---|---|
| 0x164b581→0x164bb53；空NpcConversation/BranchNote、初始序号0 | AL=0，未发送包 |
| 0x16433a0→0x1643806；type50、Process0、task200101、NPCkey0x1122334455667788 | 原构造并发送type0xc4a44、task200101、该NPCkey、option0 |
| 0x125c168→0x125c1cd；非空Finish vector | 调用Finish UI(task200101) |
| 0x125c058→0x125c090；无active bean的state1分支、同一Finish vector | 仍调用Finish UI(task200101) |

另直接原PFS重读确认234条分组、18条NpcConversation及两份原movie脚本。一次最小探针末尾读取寄存器时缺少常量import导致工具退出，补齐import后重跑通过；不涉及原指令/生产改动。未做扩大验证。

本批未验证：真实GUI/NPC可见性、资源是否全部可渲染、CG自然完整结束、实际网络顺序、在线任务/奖励/重登行为、原服务端前置/周期/完成规则、自动无NPC对白入口、type50地图/矩形的服务器触发策略。原生codec/分支成立与生产接线/部署/现场成功分开记录。

唯一写入文件：`revival/evidence/TASK_SCENARIO_OBJECTIVES_RESEARCH.md`；写入批次时间2026-10-23 15:59:44之后（Asia/Shanghai；最终mtime随交付核对）。本批所有其余操作均为只读/隔离内存探针。

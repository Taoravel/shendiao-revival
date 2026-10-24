# type50 start-only：本地开始对白、CCommit与完成表现

2026-10-23。本地端游1.6.1、网络版本601。采用 `D:/User/Documents/Codex/.codex/skills/research/SKILL.md`，本批已重读全文；当前本身为后台委派研究，不递归委派。沿用上下文中完整的 `ARCHITECTURE.md`、`DESIGN_AUTHORITY.md`：只确认客户端事实，不代替角色所有者的任务授权、事务、周期资格与投递设计。本批唯一产物为本文，没有修改任何.py、政策、catalog、共享入口或运行状态，没有操作当前客户端/在线服/战斗。

## 恢复结论

1. **真实NPC入口可复用现有TaskConversation表现链。** 对已获服务端授权的当前任务，用正常active bean、ready3状态及真实NPC任务菜单进入原本地NpcConversation；原客户端读完最后一句、处理下一次继续对白事件时，发送 `CCommitScenarioQuest(0xc4a44, task_id,npc_key,option0)`。对白文字来自客户端原配置，不需要另发正文协议。[N1、N2、P1]
2. **18条start-only均没有BranchNote/Option/Finish/Note，Animation和ProcessBarTime全0。** 不需要车夫phase5分支菜单，也没有原CG开始/结束链。完成state1的handler不读NpcConversation，故不会重播Start；它仍做任务删除/标记更新、pending效果值清零和NPC清理，不能说state1完全没有副作用。[S1、N3、P1]
3. **不增加CQuestDialogEnd门槛。** 本地Start用phase2；该包的清理分支先要求phase3。即使323001任务ID>300000，phase2仍直接跳过该分支。它不是“全部type50对白读尽包”。[N4、P1]
4. 额外机制筛选后的8条，仅6条具有实际非零、非999999的ActiveNpc：`201201,230401,323001,323101,323201,323301`。这些是NPC路径候选，不是全部可无条件开放：201201有前置102099，230401是劳动节内容，四个323x01为新春轮次活动。原周期、领取和后继实例规则不能由客户端发包证明。[S1]
5. 另12条不能直接套现有真实NPC票据：11条ActiveNpc=0（101001及10条入城节点），230701为999999。NpcConversation中的speaker ID不是ActiveNpc或实体key；不得用speaker自动填补交互目标。NPC0的原自动入口及服务端顺序本批仍未闭合，明确保留缺口。[S1、N5]

## 一手来源、地址与方法

| 来源 | 校验与定位 |
|---|---|
| `artres/config.pfs` → `autoconfig/knight.gsp.task.cmainmissioninfo.xml` | 本批直接读PFS记录、长度/CRC核验、完整BXML解码；解压字节SHA256 `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706` |
| `revival/evidence/native-image.bin` | 本批SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`；base0x400000，以下地址均VA。定向反汇编，内联Python `-B` 运行局部原指令 |
| 既有 `TASK_SCENARIO_OBJECTIVES_RESEARCH.md` | 复用上批234条分类与NPC菜单链，本批又直接读取18条Start和核心分支，不以手工JSON替代原来源 |
| 既有 `TASK_CART_BRANCH_RESEARCH.md` | 对照BranchNote/phase5布局；当前18条全部没有该分支。不沿用其历史“state2进行中”的过时措辞，当前normal0/failed2/ready3以 `TASK_TRACKER_FAILURE_RESEARCH.md` 为准 |
| `task_conversation.py`（只读） | 只核对现有Interface是否已有ready3+SVisitNpc、真实NPC票据和CCommit接缝；不是原客户端证据，也没有扩大其生产支持范围 |

research影响的决定：以原调用者、列表耗尽和构包指令为完成意图依据；将数据字段分类与业务授权分开；对未闭合的自动入口不虚构新包或使用通用对白结束授权。原配置/原指令事实可标 `client_verified`，是否纳入本地玩法与活动/前置规则仍由主线程/主策划处理。

## S1：18条原字段与范围

全部MissionType50、AnimationID0、ProcessBarTime0、BranchNpcID0；没有BranchNote、OptionList、FinishConversationList或NoteInfo。ScenarioInfoNpcID列表长度均与NpcConversation句数相同。其余完整原字段沿用 `task-scenario-catalog.json`，该文件不是本批写入产物。

| task_id | ActiveNpc | ActiveMap | Start句数 | 原speaker列表 | JumpType | 非空RequestMissionList/特殊范围 |
|---:|---:|---:|---:|---|---:|---|
| 101001 | 0 | 0 | 3 | 10083,1,10083 | 0 | 100199,100299,100399,100499,100599,100699,100799,100899,100999 |
| 101109 | 0 | 1004 | 1 | 10014 | 1 | 入城/传送机制，不能套普通NPC |
| 101209 | 0 | 1007 | 1 | 10184 | 1 | 同上 |
| 101309 | 0 | 1007 | 1 | 10195 | 1 | 同上 |
| 101409 | 0 | 1007 | 1 | 10273 | 1 | 同上 |
| 101509 | 0 | 1007 | 1 | 10209 | 1 | 同上 |
| 101609 | 0 | 1007 | 1 | 10163 | 1 | 同上 |
| 101709 | 0 | 1007 | 1 | 10172 | 1 | 同上 |
| 101809 | 0 | 1007 | 1 | 10272 | 1 | 同上 |
| 101909 | 0 | 1007 | 1 | 10161 | 1 | 同上 |
| 103309 | 0 | 1004 | 1 | 13291 | 1 | 同上 |
| 201201 | 10903 | 1002 | 2 | 10903,1 | 0 | RequestMissionList=[102099] |
| 230401 | 13286 | 1007 | 1 | 13286 | 0 | 原名[劳动节]周伯通的新计划 |
| 230701 | 999999 | 1007 | 2 | 11105,1 | 0 | 原名[赠人鲜花]寻人；999999不解释为任意NPC |
| 323001 | 13922 | 1007 | 1 | 13922 | 0 | 笑迎新春-张贴春联($round$/10) |
| 323101 | 13922 | 1007 | 1 | 13922 | 0 | 同上 |
| 323201 | 13922 | 1007 | 1 | 13922 | 0 | 同上 |
| 323301 | 13922 | 1007 | 1 | 13922 | 0 | 同上 |

“纯附加机制8”是排除10个JumpType1节点后的元数据分类，不代表另外8条已获相同任务激活/完成策略。原前置列表的AND/OR与活动日期/重置不在本批原客户端指令证明范围。

## N1：NPC菜单如何开始、逐句继续

`0x1257b20` 查任务bean；type50没有type40的菜单特例，在 `0x1257b4d` 仅state3得到UIclass3，其他已存在bean得到class2。state0同步并不会直接打开Start；state2是失败显示，不是可以用来激活这条链的进行中状态。

NPC任务菜单点击 `0x1636b81 → 0x164d780`，此前已保存实体NPCkey与taskID。`0x164d865–0x164d873` 对class3设置UI+0x64=2并调用 `0x164b530`。

该函数的关键原位置：

| VA | 原处理 |
|---|---|
| 0x164b581–0x164b5af | 读config+0x2e4/+0x2e8，按0x1c字节字符串元素算Start数量 |
| 0x164b5af–0x164b5b8 | 读UI+0x50的当前句号；若index<count，跳0x164baad |
| 0x164baad–0x164bafa | 读取config+0x2f0的speaker向量，要求数量与对白相符 |
| 0x164bb75–0x164bc86 | speaker=1使用玩家名字/外观路径，和实际NPC交互目标分开 |
| 0x164bca3起 | 读取当前句原字符串，处理NAME/SCHOOL等本地替换并送原对白UI |
| 0x164be0f | index加1；0x164be7a返回al=1，表示还有已显示的对白内容 |
| 0x164c3d6–0x164c3e0 | 继续对白事件在phase2调用同一Start函数 |

最后一行显示后，index已经等于句数；**随后一次继续事件**才读到列表耗尽并走提交。不能把“开始显示最后一句”与“已经发CCommit”合并。这里没有证实独立“完成任务”中文按钮的实际像素/caption；已证实的是原继续对白回调和包的调用关系。

## N2：列表耗尽、BranchNote与实际提交

列表耗尽后 `0x164b5be` 处理已有本地提示对象；`0x164b5dc` 检查config+0x2c8（BranchNote字符串长度）。

- BranchNote空：`0x164bb51` 返回al=0；首次入口 `0x164d878–0x164d87e` 或phase2继续回调 `0x164c3e5–0x164c3ef` 调 `0x1643360`。
- BranchNote非空：`0x164b5eb` 切phase5，`0x164b5fc` 起渲染BranchNote，`0x164b6b0` 起遍历OptionList；是否进此分支不是由BranchNpcID非零决定。phase5选择沿用0-based CCommit末字段，见车夫研究。本批18条均不进入它。

`0x1643360` 读MissionType；50不命中特定10/40/12/13/11/17分支。默认分支 `0x16437a8` 查ProcessBarTime，本表全0；`0x16437ce → 0xdd4780` 构造CCommit0xc4a44，并初始化末字段option为0，`0x16437d3–0x16437ef` 填当前taskID与64位NPCkey，`0x1643804` 发送。此处按任务ID的少数其他特例不命中这18条。

原wire体固定16字节：

```text
BE i32 task_id | BE u64 npc_key | BE i32 option(0)
```

原marshal `0xe57530` 对应对象+8、+0x10/+0x14、+0x18。它没有对白文字、读过的句数、完成时间、坐标、票据或阶段。服务端必须使用角色租约、当前任务/交互票据、真实NPC与位置验证；wire option0本身不能证明用户实际读完了文字。客户端事实只证明存在这一正常提交意图路径，不证明原服务端的奖励/后继规则。

## N3：state1不会重播Start

`SRefreshScenarioQuestState=0xc4a47`：BE taskID/state。Process `0x125ea00 → 0x125e660 → 0x125c020`。

active bean存在且state1时，`0x125c0f5` 写state，`0x125c105 → 0x125bb30` 移除active，然后：

1. `0x125c168` 检查FinishConversation（config+0x304/+0x308）；本18条全空。
2. `0x125c1a2` 检查NoteInfo长度（+0x94）；本18条全空。
3. `0x125c1c8 → 0x1255e70` 处理Animation等后置字段。

**这段handler没有读取config+0x2e0的NpcConversation，也没有调用0x164b530。** Animation0在 `0x1255e75–0x1255ea3` 写taskmanager+0x70=0，随后按ActiveNpc调用 `0x11d1870` 查场景对象，存在则 `0x11fcc50` 做NPC处理。任务state1后其他奖励提示/标记更新仍属于通用handler，不能以“不重播Start”推定没有其他UI变化。

无bean收到重复state1时，`0x125c058` 同样检查Finish→Note→fallback，所以对这些start-only也不重播Start；但仍可能重复后置/标记处理。若服务器再次下发ready3/NPC菜单并让用户重新点击，那是重新开放phase2入口，不能归因于state1重播。资产幂等和菜单/投递重试政策仍需服务端定义。

## N4：CQuestDialogEnd与CG的排除条件

本地清理 `0x1644c1d` 首先检查UIphase3，非3在 `0x1644c21` 跳 `0x1644cf8`，跳过本段CQuestDialogEnd构包。该函数的this偏移使phase读为[esi+0x60]，与主要UI+0x64字段对应，不能将phase2误读为3。

只有phase3通过后，才检查AnimationID>0、JumpType>0或本地64位task值>300000，再由 `0x1644cb6–0x1644cf2` 调后置函数并发送 `CQuestDialogEnd0xc4a52 + BE i32 task_id`。所以323x01即使ID>300000，仍不能绕开最前面的phase3条件。本18条没有FinishConversation，正常Start/menu链只设phase2，不建立Finish的phase3。

本18条Animation0，没有配置CG；正常Start回调和构包没有SStartPlayCG/CEndPlayCG要求。10条JumpType1本身也不能证明在phase2结束后必发CQuestDialogEnd；更不能用该包替代地图权威传送事件。原CG协议和10020/10026是上一批单独两条type50的范围，不能套到本18条。

## N5：NPC0与999999仍未知

已知的Start函数直接调用者为 `0x164c3e0`（继续句）和 `0x164d873`（NPC class3）；菜单入口0x164d780的直接call为0x1636b81。上批已定向查接受handler `0x125d5c0 → 0x125d070`、通知0x125cb80，尚未闭合到自动Start。到区函数0x1257d50按MissionType余数6筛选，不能为type50余数0提供相同自动到区触发依据。

这些证据不证明全程序绝无其他间接入口；仅说明当前无法给出可复用的NPC0自动包/触发契约。ActiveMap非零、speaker非零或JumpType1都不是“自动开始”的充分证据。不得用speaker10083/10014/11105等替代ActiveNpc0/999999，也不猜SNotifyScenarioQuest、SEnterDialog或场景reason。需进一步原证或明确策划设计后才接自动节点。

## P1：最少必要原指令探针

内联Python `-B` 复用既有 `research_task_jiaxing_scenario.Probe`，没有保存/改动脚本。Unicorn只运行映像小段，lookup/网络/NPC对象/渲染边界使用隔离fixture，不访问进程、socket、数据库或GPU。

| 样本与原范围 | 观察结果 |
|---|---|
| 201201（2句）、323001（1句）；0x164b581→0x164baad，index0 | 原分支跳入剩余Start渲染入口 |
| 同两例；index=句数，0x164b581→0x164bb53 | BranchNote0，AL=0，无phase5 |
| 同两例type50/Process0；0x16433a0→0x1643806 | 捕获原CCommit0xc4a44、对应taskID、synthetic NPCkey0x1122334455667788、option0 |
| 同两例phase2；0x1644c1a→0x1644cf8 | 跳过CQuestDialogEnd构包分支，无本段发包；包含323001>300000对照 |
| 同两例，非空Start但空Finish/Note/Animation0；0x125c168→0x125c1cd | 仅捕获NPC清理lookup10903/13922，pending效果从0xabcdef变0，没有Start函数调用 |

探针均退出0。没有执行完整UI字符串绘制、真人点击或原CG；“原剩余对白分支”“原提交对象捕获”与“真实客户端画面已完成”分开。NPC lookup替身返回空对象，未执行真实NPC对象清理方法。

## 接缝建议与未验证范围

现有TaskConversation已具备真实NpcInteraction/位置版本票据、ready3+SVisitNpc以及匹配CCommit的接缝；对获准的真实NPC start-only，其表现方式与本次原链相容。需要由主线程为该任务族建立独立支持判断/证据类型及原前置、活动实例授权，不能扩大普通对话或finish-only谓词，把NPC0/999999一起放开。本文没有更改这些Interface或接线。

交付时主线程已告知：当前一次性能力只支持201201/230401两条；四条含`$round$`的323x01周期任务继续排除，NPC0、999999和JumpType1亦排除。**6条是原配置的真实NPC元数据候选，2条才是本轮主线程选择恢复的非循环范围**，不能将前者写成6条已可结算。主线程还报告201201真实NPC场景离线事务通过、其原完成奖励0XP/0SMoney保持0，可接摘要数值不覆盖原奖励；201202正式任务战斗尚未开放，后继保留pending而不跳过。此段是跨模块交接状态，本窗口未另行运行生产事务或GUI验证，不构成原服活动资格/事务规则证据。

服务端可在合法CCommit后，按既有角色所有者事务完成当前任务/奖励/后继，提交成功再排队state1；不得新增等待CQuestDialogEnd/CEndPlayCG。这是与原客户端链相容的接入建议，原服事务时序未提供，设计状态应与客户端证据分开登记。

未验证：完整真实GUI、具体点击区域/caption、关闭/取消全部事件、在线包顺序、重连、实际活动资格/周期重置/前置逻辑、NPC0自动入口、999999业务意义、JumpType1传送时序/坐标。没有把下行排队等同于GUI播放成功。唯一写入：本文；最终文件时间另以交付时mtime核对。

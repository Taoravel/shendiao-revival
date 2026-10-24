# 嘉兴柯镇恶任务与60001章节特效

日期：2026-10-23。适用本地1.6.1端游、网络版本601。按 `research` 技能追溯一手原配置、资源和原native指令，当前本身为背景委派研究，不再递归委派。已读 `ARCHITECTURE.md`、`DESIGN_AUTHORITY.md`，遵守角色状态/事务与网络投递所有权。本批仅产出本文及独立离线fixture；未运行当前客户端、在线服、GUI、战斗、原角色数据库或共享入口。

## 可指导下一批恢复的结论

1. **60001是普通本地章节标题特效，不是CG电影或武器选择卡。** 原 `CQuestEffect[60001].Path=geffect/chapters/xuzhangyuanqi`；`effect.pfs` 内实际资源是 `geffect/chapters/xuzhangyuanqi.efct.xml`，由 `animation/chapters/xuzhang`、`animation/chapters/yuanqi` 与 TitleFlower 粒子组成。[S2、S3、N2]
2. 这10条都为普通MissionType10、3句 `NpcConversation`、无BranchNote/FinishConversation/NoteInfo，AnimationID60001、RewardMapJumpType0。原可交付菜单显示本地3句对白，耗尽后走普通CCommit；**没有该任务必须再等CQuestDialogEnd或CEndPlayCG(60001)的证据**。[S1、N1、N3]
3. 服务端发任务 `state1` 后，原客户端删除active任务，并在没有Finish/Note的路径直接请求60001的CQuestEffect资源。可把“保持原AnimationID、发state1、委托原客户端显示”作为本批恢复方式；**这不等于已确认真实GUI出现或已播放完成**。[N2、P1]
4. **重复state1会再次请求60001。** bean已经移除也不会令state1直接忽略；无bean的state1分支仍会调同一后置特效函数。任务/奖励事务幂等不自动提供视觉去重。[N4、P1]
5. 本地3句对白→合法普通CCommit→服务端完成/奖励120XP/唯一后继事务→提交后state1的恢复方案与本次客户端路径相容；事务授权、发包顺序、断线恢复与去重属于服务端设计，不能称为从原服实现复原。这里没有新增玩法裁定或接线。[S1、N1–N4]

## 一手来源与校验

| 来源 | 原路径/条目 | 本批校验 |
|---|---|---|
| S1 | `artres/config.pfs` → `autoconfig/knight.gsp.task.cmainmissioninfo.xml` | 原PFS长度/CRC、完整BXML重读；SHA256 `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706` |
| S2 | 同包 → `autoconfig/knight.gsp.task.cquesteffect.xml` | 同法重读；SHA256 `8fbbda8366389fe8da2635a4f4160717a6c30b25f3d969f163906366243c9e45` |
| S3 | `artres/effect.pfs` → `geffect/chapters/xuzhangyuanqi.efct.xml` | 原PFS长度/CRC、BXML解码；SHA256 `fb21ac8730895bc23dcae66fff69acf96fda6e78fcecc3669306a93b5b74254a` |
| N1–N4 | `evidence/native-image.bin`，base0x400000，以下均VA | SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`；定向Capstone、原指令fixture |

辅助既有证据：`TASK_DIALOG_PROTOCOL.md`、`TASK_CART_BRANCH_RESEARCH.md`、`WORLD_MASTER_CARD_PROTOCOL.md`、`NEWBIE_FIRST_MASTER_RESEARCH.md`。本批仍从原PFS重读当前10条和60001资源，没有以既有手工JSON代替原来源。

## S1：10条任务的原字段

以下全部 MinLevel/MaxLevel=0/0、MissionType=10、ActiveMap=1006、AnimationID=60001、ExpReward=120、RewardMapJumpType/ID/X/Y=0，普通Money/PetExp/SMoney均0、ProcessBarTime0、BranchNpcID0。每条NpcConversation恰好3句；没有BranchOption、BranchNote、FinishConversation或NoteInfo。120只是原ExpReward字段，原服经验倍率仍沿用奖励研究中的未知范围。

| 车夫后继task | ActiveInfoNpcID | ScenarioInfoNpcID三项 | 唯一PostMissionList |
|---:|---:|---|---:|
| 100105 | 10212 | 1,10212,10212 | 100160 |
| 100204 | 10492 | 1,10492,10492 | 100260 |
| 100304 | 10492 | 1,10492,10492 | 100360 |
| 100404 | 10212 | 1,10212,10212 | 100460 |
| 100504 | 10492 | 1,10492,10492 | 100560 |
| 100604 | 10212 | **10212,10212,10212** | 100660 |
| 100704 | 10492 | 1,10492,10492 | 100760 |
| 100804 | 10212 | 1,10212,10212 | 100860 |
| 100904 | 10212 | 1,10212,10212 | 100960 |
| 103205 | 10212 | 1,10212,10212 | 103260 |

所有任务文字指向“向柯镇恶打听黄药师的下落”；10212与10492均保留原值，不把同名NPC随意合并。三句大意是：玩家问候并打听黄药师；柯镇恶答不知；推荐去陆家庄外找说书人。原富文本还替换 `$NAME$`；100604首句NpcID与其他九条不同，保留原资料差异，不在研究中修表。

## S2/S3：60001的实际资源身份

原CQuestEffect记录只有以下关联：

```xml
<record id="60001" Path="geffect/chapters/xuzhangyuanqi" />
```

实际effect资源根：`<data total_frames="61" fps="8.000000" bindType="0" hasaudio="0" ...>`，4个clip：

| start_frame | layer | res_file | 原播放参数示例 |
|---:|---:|---|---|
| 28 | 0 | particle/psl/chapters/TitleFlower | play_mode1, loop_num1 |
| 7 | 1 | animation/chapters/yuanqi | play_mode2, play_time5000；位置与alpha关键帧 |
| 0 | 2 | animation/chapters/xuzhang | play_mode2, play_time5900；位置与alpha关键帧 |
| 28 | 3 | particle/psl/chapters/TitleFlower | play_mode1, loop_num1 |

资源中没有CG脚本Section/Setmap/Return链，也没有武器卡两个按钮/可领物品字段。本文根据资源路径与组成称它“序章缘起章节标题特效”，未渲染其真实像素，也不从61帧/8fps推定服务端等待时间。

同包另有 `geffect/chapters/xuzhangyuanqifinish.efct.xml`，它含chapterfinish层；**60001的Path并未指向这个finish变体**，不能只凭文件名相近改用它。

| 类型/具体例 | 原资源/消费者 | 结束或选择意图 |
|---|---|---|
| root11001 | 原movie脚本、SStartPlayCG与CG管理器 | CEndPlayCG0xc0018，body movie_id |
| 师父卡20006 | CCardEffect[20006]；独立SPlayCardEffect0xc001c打开卡UI | CGetCardItem0xc041f，effect_id+item_id；详见武器卡研究 |
| 本批60001 | CQuestEffect[60001] →普通effect加载器，实际efct资源 | 本链没有新增CG结束包或选择包；state1副作用为本地特效请求 |

ScenarioInfoAnimationID只是任务配置中的通用整数，不足以把三者当成同一协议。普通后置函数对200xx也可能进入generic effect分支，但这本身不会替代独立武器卡下行。本批原CQuestEffect查找只看到60001，而原CCardEffect对照记录20006明确有两个物品选项。

## N1：本地3句对白后是普通CCommit

原可交付普通任务路径：NPC菜单查询 `0x1257b20` 将state3的ScenarioQuest分类成UI3；菜单点击进入 `0x164d780`。`0x164d86c` 设置本地对白UI阶段+0x64=2，`0x164d873` 调 `0x164b530` 渲染本地NpcConversation。

该函数以UI+0x50为对白序号，逐句读config+0x2e0的vector；渲染后 `0x164be0f` 序号加1。下一句回调 `0x164c350` 在阶段2再次调用该函数。三句耗尽后：

- `0x164b5b8` 不再跳入NpcConversation渲染。
- `0x164b5dc` 检查BranchNote.length（config+0x2c8），本批为空。
- `0x164bb51` 返回al=0。
- `0x164c3e0–0x164c3ef` 对al=0调用普通提交 `0x1643360`；该函数对MissionType10、ProcessBarTime0进入 `0x16433e9–0x164342a` 构造/发CCommit。

仍使用已有 `CCommitScenarioQuest=0xc4a44`：BE `i32 quest_id, u64 npc_key, i32 option`，普通路径option=0。没有电影ID60001、目标地图或“特效播放成功”字段。服务端必须按既有可信交互票据/NPC/位置/当前任务验证后完成，不能凭客户端填一个任务ID/0值即结算。

## N2：state1委托本地60001效果

下行 `SRefreshScenarioQuestState=0xc4a47`，body BE `i32 quest_id, i32 state`；Process `0x125ea00 → 0x125e660 → 0x125c020`。

active bean存在且state1时，`0x125c0f5` 写状态、`0x125c105 → 0x125bb30` 删除活动记录并刷新显示相关对象。然后：

1. `0x125c168` 检查FinishConversation，无；
2. `0x125c1a2` 检查NoteInfo.length，无；
3. `0x125c1c8` 调 `0x1255e70(config)`；
4. 后置函数 `0x1255e75` 读取AnimationID60001，因>20000且RewardMapJumpType0，在 `0x1255e8c` 调 `0x12550c0(60001)`；
5. dispatcher的30000–59999分支不适用，`0x1255110` 调Scene `0x11ca790(&60001)`。

Scene路径更具体的原调用：

| VA | 行为 |
|---:|---|
| 0x11ca798–0x11ca7b9 | 已有Scene+0x3a0效果对象时释放/置空，随后请求新效果 |
| 0x11ca7c3 | CQuestEffect getter `0x89ec50`（配置root+0x1090） |
| 0x11ca7cc–0x11ca7d6 | 以60001查记录 |
| 0x11ca7da | 记录+4，即Path字符串对象 |
| 0x11ca7dd–0x11ca7ef | engine getter `0x5a6660`，调用虚函数+0x120(Path,0)，保存返回效果对象 |
| 0x11ca83f–0x11ca887 | 对普通ID按当前屏幕宽/高的一半设置效果坐标；这不是世界地图坐标 |
| 0x11ca889–0x11ca8b6 | 建立回调对象，vtable0x2296c64，交效果对象虚函数+0x68 |

其中回调函数 `0x81ae80` 解绑回调、调Scene清理 `0x11c65a0`、销毁自身；清理函数移除Scene+0x3a0效果对象。所查这些局部回调没有构造CQuestDialogEnd或CEndPlayCG。加载失败返回空时，`0x11ca7f9 → 0x11ca8b8` 直接返回；没有由此推得一个服务端可依赖的“标题已显示”确认。

因此恢复状态应分开记：**AnimationID原值已保留 / state1逻辑消息已排队或发送 / 原客户端效果已委托**；真实GUI可见、效果完整播放没有验收，不能写“动画已完成”。

## N3：CQuestDialogEnd与CEndPlayCG不应套用

`0x1644c1a` 是另一段对白收尾代码，`0x1644c1d` 检查UI阶段3（该函数this偏移下读+0x60），只有该阶段且满足原条件才会在 `0x1644cb6` 调后置函数，再于 `0x1644cc5–0x1644cf2` 立即发送 `CQuestDialogEnd=0xc4a52 + BE i32 quest_id`。

这里的“调用后置函数后立即发报告”不是等待effect61帧播完。用synthetic阶段3可令同一60001进入该路径，但这10条原表没有FinishConversation；state1走N2的直接fallback，没有建立完成对白阶段3的原配置依据。本批阶段2对照探针没有发此报告。因此不可把“有AnimationID”变成服务端必须等CQuestDialogEnd的新门槛。

`CEndPlayCG=0xc0018` 来自原CG管理器独立生命周期，body是movie_id。60001本次查到的是effect加载器和清理回调，没有进入CG管理器、没有构造SStartPlayCG、没有等待该上行。不得为60001补发SStartPlayCG、伪造CEndPlayCG或把它映射为当前任务完成证据。

## N4：无bean时重复state1仍请求特效

`0x125c045–0x125c047` 查不到active bean后，并未立即忽略消息：`0x125c04d` 比较传入state1，然后从 `0x125c058` 同样检查FinishConversation；空则 `0x125c0a1` 检查NoteInfo；仍空则 `0x125c0d6` 调 `0x1255e70(config)`。

所以重复state1会再次请求60001；若前一个特效仍存在，N2所述Scene函数会先移除已有对象再加载新对象。这里不存在因“已完成任务”自动去重的保证。资产回执可以幂等奖励，但重试逻辑不应为了重放历史回执而无条件再次投递该视觉消息。具体投递/重连快照政策由集成方决定，并标为服务端设计。

## P1：少量必要离线验证

新增 `D:/神雕侠侣/revival/research_task_jiaxing_scenario.py`，已运行：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 revival/research_task_jiaxing_scenario.py
```

退出0，断言通过：

- 直接重读10条原任务，核对3句、无Branch/Finish/Note、60001、map1006、JumpType0；关联CQuestEffect及实际efct资源；
- 10条分别执行原state1显示选择片段 `0x125c168–0x125c1cd`，保留真实后置函数、dispatcher和Scene查表指令，均捕获CQuestEffect60001查找、Path对象传入engine加载Interface；
- 原普通提交构包片段捕获CCommit(task100105,synthetic64位npcKey,option0)；
- 原对白收尾阶段2对照无报告；synthetic阶段3捕获60001效果请求后CQuestDialogEnd(task100105)，没有CEndPlayCG；
- 原无bean-state1片段 `0x125c058–0x125c0db` 连续执行两次，捕获两次60001效果加载请求，验证不能假设视觉去重。

fixture只替代配置lookup、网络发送Interface、NPC查找，以及engine资源/GPU加载边界。engine加载stub记录原Path对象参数后返回空，不实际创建/绘制效果，也不执行后续成功创建对象的全部显示链；后者仅做静态调用检查。阶段3为反事实对照，不假装本批任务原UI已经建立该阶段。每个片段仅数百条指令预算，没有大规模模拟。

## 服务端待设计与确切未验证范围

原客户端事实支持在合法普通CCommit后，完成任务与奖励/唯一后继同事务，提交后state1委托60001显示的恢复方案；原服在何时发状态、奖励和后继、如何持久化与重试的代码并未取得。方案不得扩大成任意动画ID都属于普通对话，不修改既有 `supports_plain_dialogue` 的收窄契约；应按确证名单单独授权本地effect能力。

不要求60001的CG结束/完成对白结束报告，是基于本批真实资源和调用链；这不排除其他任务确有FinishConversation及其CQuestDialogEnd时序。公网协议也不能证明玩家逐字看完3句对白。

未验证：真实NPC菜单与玩家点击、GUI字体/标题图可见、粒子/GPU生命周期、最终资源加载成功、真实网络投递和断线重连、后继任务与资产事务、原服务器精确先后次序。本文没有改变任何领域/共享/原客户端文件或在线状态。

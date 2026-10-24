# 新手“宠物设为参战”十一条任务研究

2026-10-23，本地1.6.1端游、网络版本601。按 `D:/User/Documents/Codex/.codex/skills/research/SKILL.md` 从原PFS/BXML、原生映像和当前公开资产Interface追溯；本任务已经是后台研究，不递归委派。已读AGENTS、ARCHITECTURE和DESIGN_AUTHORITY。本批唯一产物为本文；不改生产、共享入口或政策，不运行客户端、服务、战斗，不接触在线角色库。

## 结论与证据等级

原主表91条MissionType59中，任务目的包含“参战”的恰好是下列11条。它们是独立的**参战状态引导目标**：文案明确要求宠物界面点击“参战”；原客户端CSetFightPet确实发送一个宠物实例key，SSetFightPet更新当前选中参战宠。上述为 `client_verified`。

但这些证据**不证明原服完成判定**。以实际 `Inventory.selected_fighting_pet(db)` 非空作为本地恢复完成事实、在合法设置参战后或重连时进行reconcile，应标 `designed`。不能将文案、“收到CSetFightPet请求”或任意type59统一视为已完成；也不能从“赠送宠物”文字编出宠物模板、实例或获取凭据。

## 原包与十一条完整字段归并

直接 `PfsArchive('artres/config.pfs').read('autoconfig/knight.gsp.task.cmainmissioninfo.xml')`，校验PFS本地/中央记录、解压长度和CRC；BXML解码后，2460行全部attributes与lists和已提取目录逐行相等。本轮不是只引用旧目录。

- 展开长度2026233字节，CRC32 `3f7ab7b3`。
- 展开SHA256 `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706`。
- 映像 `native-image.bin` SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

所有11条的attributes与100189逐字段比较，仅`id`不同；另101014的TaskInfoTraceListA少了面板链接。下列是完整字段归并，未列出的额外字段/列表不存在，不能视作隐含0字段：

| 字段组 | 原值 |
| --- | --- |
| MissionName / MissionTypeString / MissionType | `[主线]序章缘起` / `主线剧情` / 59 |
| MinLevel / MaxLevel / TransMinLevel / TransMaxLevel / TransformID | 全0 |
| ExpReward | 200 |
| MoneyReward / PetExpReward / ShengWang / SMoney | 全0 |
| RewardMapJumpType / RewardMapID / RewardMapXPos / RewardMapYPos / ProcessBarTime | 全0 |
| ActiveInfoNpcID / ActiveInfoMapID | 0 / 1006 |
| ActiveInfoLeftPos / TopPos / RightPos / BottomPos | 全0（各字段均以ActiveInfo开头） |
| ActiveInfoTargetID / ActiveInfoTargetNum / ActiveInfoMiniStep / ActiveInfoStepProbability / ActiveInfoMaxStep | 全0 |
| ActiveInfoTeamState | 1 |
| ActiveInfoTimeLimit / ActiveInfoIsRestartTimer / ActiveInfoGiveBackMoney / ActiveInfoGiveBackPetID / ActiveInfoUseItemID / ActiveInfoOtherType / QuestionInfoNpcID | 全0 |
| AIInfoAIID / AIInfoBattleResult / AIInfoDeathPunish / AIInfoTeamSteate | 0 / 1 / 0 / 1（Steate为原拼写） |
| BattleInfoBattleMapType / BattleInfoBattleZoneID / BattleInfoDrop / BattleInfoBattleTimes / BattleInfoMonsterNum / BattleInfoDropItemID / BattleInfoDropItemNum | 1 / 0 / 0 / 0 / 0 / 0 / 0 |
| ScenarioInfoAnimationID / ScenarioInfoBranchNpcID | 0 / 0 |
| DisPlayNPCID | `[10086]` |
| PostMissionList | 各自唯一后继，见下一表 |

三项原文本字段（均是客户端原值，不作为服务端判定代码）：

```xml
TaskInfoDescriptionListA = <T t="少侠果然好身手，那这只宠物就送给你，你可要好好待他，记得给他喂吃的，可千万别饿着他。" c="ff12c4ff" ></T>
TaskInfoPurposeListA = <T t="将宠物设定为参战状态。（点击屏幕右上方的宠物头像打开宠物界面，点击“参战”按钮就可以使宠物参战了。）"></T>
TaskInfoTraceListA = <T t="打开"></T><G t="面板" npcid="57"></G><T t="设置宠物为参战状态"></T>
```

101014的Trace单独为 `<T t="将宠物设定为参战状态"></T>`。`57` 是追踪富文本中的界面链接参数，不能当作本任务要求交互的真实NPC；ActiveInfoNpcID仍是0。DisPlayNPCID10086也不能替代要求实际NPC接近或CCommit的字段证据。

没有 `ScenarioInfoNpcConversationList/ScenarioInfoNpcID`（Start），也没有 `ScenarioInfoFinishConversationList/ScenarioInfoFinishNpcID`（Finish）；没有BranchNote、RequestRoleIDList、RequestMissionList、RewardItemIDList/Num/IsBind、宠物奖励列表或非零ActiveInfoGiveBackPetID。这11条本身没有提供领取宠物模板。中文同名与Type59不足以建立隐藏的赠宠规则。

## 原前后边与Start/Finish位置

| 前驱（唯一原入边） | 参战任务 | 唯一原后继 |
| --- | --- | --- |
| 100113 | 100189 | 100191 |
| 100212 | 100289 | 100291 |
| 100312 | 100389 | 100391 |
| 100412 | 100489 | 100491 |
| 100512 | 100589 | 100591 |
| 100612 | 100689 | 100691 |
| 100712 | 100789 | 100791 |
| 100812 | 100889 | 100891 |
| 100912 | 100989 | 100991 |
| 103213 | 103289 | 103291 |
| 101013 | 101014 | 101015 |

以上全部前驱为Type40、NPC10086、Map1006、AI8003、Animation0；都有原Start/Finish对话，Finish含赠宠提示（例如101013：“果然好身手，这只宠物就送给你吧”），Start说“你只要能凭本事抓住，我就当白给你了”。前驱lists都只有PostMissionList、DisPlayNPCID、Start文本/说话人、Finish文本/说话人六组，没有可直接当宠物授予模板的列表。前驱的战斗/捕捉/赠宠来源需要战斗与资产所属Module另证，不能在reconcile中补发小灰狗或其他任意宠物。

全部后继为Type40、NPC10493、Map1006、AI8028、Animation30045，有Start/Finish对话，原目的是找“驯宠学徒”试练宠物（需战斗）。所以参战目标完成后只能沿原边激活后继，不能当作试练战斗已经胜利，不能顺便结算后继奖励。

Type59总数为91，不同机制直接反例：100188（及其他角色对应行）目的为装备师父赠与武器；100120要求拼回画像，含Start/Finish；102050要求五次师门任务且有RequestRoleIDList；102064要求命门穴15级；102106为郭靖地图拼图。Type59不是统一的宠物、装备或“界面打开即完成”类型。建议只对这11条原配置严格识别，不能从purpose关键词对全表动态授权。

## 原生C/SSetFightPet请求与消费者

本轮直接检查原映像，不启动进程：

| 原位置 | 实际证据 |
| --- | --- |
| CSetFightPet RTTI `.?AVCSetFightPet@pet@gsp@knight@@`，虚表0x227af9c | 构造0xdbd2c0写type0xc07d8、成员+8初始化0；约束0xdbd2e0要求成员≥1 |
| marshal 0xe53780..0xe537ad | 只从bean+8取一个正i32，交0x770960写出；unmarshal0xdbd360..0xdbd3c4仅消费4字节，bswap，要求≥1。body不是task_id，也没有NPC/完成证明 |
| 原UI发送0x141ef0d..0x141ef44 | 从当前UI对象+0x184取宠物实例key，构造CSetFightPet并发送；随后走本函数返回，没有紧接构造CCommit。此前分支有等级/条件检查，本轮不从这些门禁推出服务器原资格政策 |
| CSetFightPet process虚槽6→0xdbd310 | `ret 8`，客户端方向的请求类不是任务完成消费者 |
| SSetFightPet RTTI `.?AVSSetFightPet@pet@gsp@knight@@`，虚表0x227b604 | process虚槽6→0x1131a70 |
| S handler0x1131a70..0x1131ad7 | 正常世界分支把bean+8传0x11301a0；另一状态暂存global对象+0x310；末尾通知两处宠物UI（0x13db430、0x1442f30） |
| setter0x11301a0..0x113026e | 把指定key写当前角色+0x190（0x1130222）；调用宠物/显示相关方法和事件虚槽；没有直接任务ID查表或CCommit构造 |

精确限制：这条直接发送/回包链没有发现独立CCommit或任务刷新构造，但setter会调用动态事件虚槽，本轮没有遍历整个事件系统，不能由此证明“客户端任何位置永不发CCommit”，更不能证明原服务器究竟在哪个事件判完成。可以确认**单纯CSetFightPet线包只带宠物key**；恢复服务器应以提交后的资产事实为证，不能把线包当持久参战已经成功。

原任务状态包/删除行为已有其他TASK协议证据，本轮未重跑其probe。没有把SSetFightPet应答当任务完成状态，二者应由各自所属Module生成。

## 可实施reconcile Seam与设计界限

当前公开 `Inventory.selected_fighting_pet(db)` 在调用方现有事务校验角色账号归属，读取owned、fighting=1、released=0的实例并返回冻结PetState或None；会保留旧实例的progress=None。它**不检查login_epoch**，任务调用方仍须通过当前角色租约/删除状态围栏；不应直接跨窗口读inventory_pets私表或将Session缓存宠物key当当前事实。

本地完成判定若采用“这11条之一已可信激活且当前确有自有未放生参战宠”，需明确 `designed`：本表没有模板/宠等级/HP/忠诚度门槛，不能凭任务奖励宠经验规则额外套HP>0或角色+5条件。具体参战合法性由资产Module真实变更Interface负责，任务只确认已持久的选择事实；`progress=None`不等于没有宠物，也不能据此伪造基线。

建议入口：合法参战变更的同事务precommit内，或角色重连/本任务激活后的同事务可信reconcile内，重新读公开selected_fighting_pet；满足明确本地政策才计划任务完成、加入既有唯一奖励渠道并沿原唯一边激活后继。None不自动给予宠物、不提前完成、不删任务；反复reconcile只返回既有完成结果，不再付200EXP。重连采用状态判定而非必须重放一次点击，也是需要明示的本地恢复政策。

当前资产 `fight_pet(key, *, precommit=None)` 包装自有事务，实际变更后 `_run_precommit` 位于提交前，可作为集成Seam；不得在任务Module调用它再另开事务结算，亦不得调用资产私有 `_fight_pet` 冒充公开事务Interface。实际GameRuntime/存储接线由原集成窗口集中处理，本研究未修改共享入口。若调用方已有事务，则须使用资产所属窗口提供的公开同事务变更契约/回调，不能复制私有SQL。

## 本批验证与未验范围

已做：原主表PFS长度/CRC/BXML与2460行目录全等；11条全attributes差异核对、全部原入边/后继、Start/Finish与所有列表存在性核对；91条type59的“参战”目的恰11条统计；原请求构造、marshal/unmarshal、UI发送、S handler与当前状态setter反汇编；当前公开selected_fighting_pet/fight_pet precommit静态读取。

未做：原服完成条件、全部事件回调穷举、赠宠模板/来源、服务端生产reconcile实现和事务检查、客户端原窗口显示/自动进度实测。本报告未写生产或测试脚本、未做在线操作；本地恢复判定须由主任务/主策划标design并另记实现和验收，不能由本报告的原文案替代。

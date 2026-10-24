# MissionType40 任务战斗授权：原协议与静态范围

2026-10-23。本批使用 research 技能：从原PFS直接重读任务/AI/怪物表，定位原UI比较、专用消息构造与codec，再用小型离线原指令fixture确认。当前本身为背景委派研究，没有再派代理。已读 `ARCHITECTURE.md`、`DESIGN_AUTHORITY.md`；只产出独立研究脚本、统计JSON和本文，不改任务领域、战斗Module、共享入口、在线服、原客户端或角色数据。

## 主要结论

1. **已接type40任务在原NPC菜单中直接归UI分类3；对白结束后的开战请求是专用 `CActiveScenarioQuestAIBattle=0xc4a4c`，不是普通CCommit。** 未接任务的菜单入口仍可能先发CCommit接取，必须分清两阶段。[N1、N2、P1]
2. 专用包body恰好12字节：**BE signed i32 quest_id + BE u64 npc_key**。没有AIID、选项、敌人、战斗结果或结算字段。原decode校验questID范围1001–499999；NPC合法性、距离、任务阶段、连接租约都不是该codec提供的。[N2、P1]
3. 362条type40全部有非零NPC/AIID，引用244种AIID；原客户端 `CBattleAIConfig` 是提示/表现表，2194条ID为50001–52210，而任务AIID为1428–8144，**直接关联为0条**。所查原怪物表也没有阵型、HP、攻击等数值，因此尚未获得可用于正式任务PVE的原敌阵/属性/AI逻辑。[S2、S3]
4. 本批提取出301条“额外字段均零”的静态族及61条带额外字段的任务。它只是透明的资源筛选结果，**不表示301条已能开战或完成**；它们仍没有已确认的原敌阵与正式task-PVE所有者。[S1、统计产物]
5. `AIInfoBattleResult=1` 有361条、0有1条。原字段及parser已证实；本批没有原服务端比较代码，不能仅按字段名宣称0就是“失败也完成”或把1解析成网络上报的成功位。正式结果必须绑定本次可信任务战斗实例；训练/wild胜利不能完成任务。[S1、N3]

可接线的范围是可信NPC/任务绑定的**战斗 admission / result → 任务同事务 Seam**。没有恢复正式敌阵前，普通CCommit、任意客户端战斗结束消息、训练结果都不能用来假完成这些任务。服务端结算与幂等政策由集成方设计，来源不能写为原服实测。

## 来源、产物与校验

源资源均由 `PfsArchive.read` 校验记录长度/CRC，再完整BXML解码；不是只引用旧catalog。

| 来源 | `artres/config.pfs` 内条目 | 原解压字节SHA256 |
|---|---|---|
| S1 | autoconfig/knight.gsp.task.cmainmissioninfo.xml | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |
| S2 | autoconfig/knight.gsp.battle.cbattleaiconfig.xml | 01e56fcca6af219dc36617d323710e6d379c299e74c57b82f75aeaa449f9dea3 |
| S3 | autoconfig/knight.gsp.npc.cmonsterconfig.xml | b4843cab3b217a94c2f6fefc00b68cd28bed4c4dc125d9271812769d59dd7c39 |
| S3b | autoconfig/knight.gsp.battle.cmonstertypeconfig.xml | e9cbf9c2cfd5b91c45d5281eb2d86a1c6986a705afefbdc4bd879969cf03c552 |

原映像 `evidence/native-image.bin`，base0x400000；以下均VA。SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

独立产物：

- `research_task_battle_admission.py`：全表重读、原sender/codec/菜单谓词的必要离线fixture；
- `evidence/task-battle-admission-static.json`：362条精确选定原字段、前后对白/后继列表、每条额外字段原因、301条静态族ID、完整分布、源hash与fixture结果。

## N1：菜单分类与任务状态投影必须分开

原 `0x1257b20`：

- `0x1257b2a` 查ScenarioQuest active bean；不存在时继续检查另一种任务记录，均不存在则返回菜单分类1。
- 有ScenarioQuest bean时查原任务config；`0x1257b44` 比较config+0x164是否40，命中即 `0x1257b5e` 返回3，**不先比较bean.state是否3**。
- 其他类型才在 `0x1257b4d` 比较bean.state==3，否则返回2。

本次原指令fixture：type40无bean→1；bean.state0→3；bean.state3→3；bean.state2也→3。最后一项仅证明该菜单函数不筛任务失败状态，**不代表state2是正常active或允许开战**。

主集成最新核准的tracker投影为正常0、ready3、state2为失败；本报告遵守该约束，不生成active完整bean，也不沿用早期研究把state2称为正常active的说法。菜单分类与tracker状态文字是不同消费者；战斗授权仍必须由服务端权威任务阶段判断，不能因为菜单函数返回3就放行失败/过期任务。

NPC菜单分类3点击后，`0x164d86c` 设置本地对白UI阶段2，`0x164d873 → 0x164b530` 播配置NpcConversation；没有内容或对白耗尽则进 `0x1643360`。同一外层入口适用于type10和40，**但后者在提交函数内分流到专用战斗包**。

## N2：0xc4a4c 的真实发送、布局和约束

原RTTI名：`.?AVCActiveScenarioQuestAIBattle@task@gsp@knight@@`。vtable `0x227d510`；constructor `0xdd3b30`，`0xdd3b3a`写type0xc4a4c；marshal `0xe57320`；decode `0xdd3be0`；客户端Process `0xdd3b90 ret8`，上行不在客户端消费成任务完成。

### NPC对白之后的专用分流

`0x1643360` 的type40分支：

| VA | 原行为 |
|---:|---|
| 0x164343c | 比较任务类型0x28（40） |
| 0x164344b | 调人物属性阈值谓词0x1137dc0 |
| 0x1643458–0x1643486 | ProcessBarTime(config+0xd8)>0时先进入原进度条，种类6 |
| 0x16434ad | ProcessBarTime<=0的直接路径构造vtable0x227d510 |
| 0x16434b5 | 写type0xc4a4c |
| 0x16434bd–0x16434d9 | 从对白UI+0x48取任务ID、UI+0x38/+0x3c取64位NPC key |
| 0x16434dd–0x16434ee | 经连接发送Interface发送 |

人物阈值谓词未通过时，原客户端构造确认框，回调 `0x1641e10` 仍有同样的进度条/直接发送两条路径；`0x1641e86–0x1641ec3` 发送相同0xc4a4c。该谓词 `0x1137dc0` 对人物属性键60与140×约0.8做比较；本批没有把它扩张为服务端已证实的完整开战资格规则，也没有运行确认框GUI。

原进度条完成的种类6分支 `0x16c4804–0x16c484e` 也构造同一包（taskID、npcKey），无需给ProcessBarTime任务猜另一种网络协议。没有实际运行进度条计时/取消生命周期。

### 精确body

```text
offset0: BE signed i32 quest_id
offset4: BE u64 npc_key
总长12字节
```

原marshal在 `0xe57351` 调BE i32 writer0x770960，再 `0xe57360` 调BE u64 writer0x7709b0。decode在 `0xdd3c1a` bswap后写对象+8；`0xdd3c29` 读u64写对象+0x10/+0x14。结构中的对象对齐空隙不是wire字段。

原decode末段 `0xdd3c37–0xdd3c45` 只检验 `1001<=quest_id<=499999`；未检验NPC key符号、归属、是否与任务NPC配置匹配。流decoder消费12字节，不替代恢复服外层“正文必须恰好12字节”的检查。恢复decoder可严格长度12、ID范围，再交可信NPC授权层核验；不要让合法整数范围代替任务存在/类型校验。

100107、synthetic npcKey0x1122334455667788的原wire为：

```text
00 01 87 0b 11 22 33 44 55 66 77 88
```

**CCommit的区分**：未接任务菜单分类1的通用接取仍发CCommit0xc4a44；普通type10对白交付也用CCommit。不能把它们路由成“所有type40 CCommit立即开战/完成”。本次已接type40 NPC对白收尾的真实开战声明是0xc4a4c，没有AIID或结果字段。

## S1：362条静态统计与族

### 完整分布摘要

| 原字段 | 分布 |
|---|---|
| AIInfoAIID | 非零362条，244种，范围1428–8144 |
| AIInfoBattleResult | 1:361；0:1（226102，AI2115，“样本实验”） |
| AIInfoDeathPunish | 0:362 |
| AIInfoTeamSteate | 1:288；0:74 |
| ActiveInfoTeamState | 1:288；0:74；逐条等于AIInfoTeamSteate |
| ScenarioInfoAnimationID | 0:332；10019:11；30045:11；8067/60015/60017/10023/10024/14003/11042/11043各1 |
| ScenarioInfoBranchNpcID / BranchNote | BranchNpcID全部0；BranchNote全部空 |
| BranchOptionList | 2条非空：322401、322501；它们BranchNote仍为空，不能据有选项列表就认为原菜单一定展示 |
| ProcessBarTime | 0:360；3:2（206503、206504） |
| ActiveInfoUseItemID | 0:361；110000:1（204702） |
| ActiveInfoTimeLimit | 0:350；30:12（321401至322501的十二条百位递增ID） |
| ActiveInfoIsRestartTimer | 0:362 |
| RewardMapJumpType | 0:351；1:8；3:3 |
| ActiveInfoTargetID | 0:361；50054:1（102117） |
| ActiveInfoTargetNum | 0:360；1:2（102117、229905） |
| BattleInfoMonsterNum | 0:361；20:1（210402） |
| NpcConversation非空 | 307条 |
| FinishConversation非空 | 317条 |
| NoteInfo非空 | 2条：102510、102717 |
| RewardItemIDList非空 | 151条 |

其他全为0的字段：ActiveInfoOtherType、MiniStep、MaxStep、StepProbability，BattleInfoBattleZoneID、BattleTimes、Drop、DropItemID/Num，TransMin/MaxLevel。BattleInfoBattleMapType全部1。所有ActiveInfoNpcID都非0（278种）。这些0值只表示原字段如此，不证明原服缺少计时、组队或敌人逻辑。

**team的0/1语义未在本批证明。** 例如100107原文字写“单人简单”，但两个team字段都为1；不能把1直接翻译成“必须组队”，也不把0翻译成任意模式均允许。

### 透明静态族

脚本的301条“zero_extra_metadata”谓词明确要求：BattleResult原值1；AnimationID、BranchNpcID、ProcessBarTime、UseItemID、TimeLimit、IsRestartTimer、RewardMapJumpType、TargetID/Num、MonsterNum全0；BranchNote/NoteInfo为空，BranchOptionList没有非空元素。它允许原前/后对白及奖励列表存在。

其余61条保留每条具体extra_reasons供后续能力拆分。这是客户端元数据统计，不是战斗已支持白名单；301条也仍需原AI敌阵/可信结果和正式battle所有者。尤其不以“额外字段零”授权训练战斗替代。

重复AIID族：8001/8002/8003/8005/8027/8028/8029各11条；8006/8007/8008各7条；1446/1976/2001各5条；1945/1946各4条。它说明多个任务共享原关联值，不证明可以共享一个战斗实例、跨任务认领同一次结果或套同一等级敌人。完整任务和AIID分布在统计JSON。

## 优先样本100107 / 100113

| 字段 | 100107 | 100113 |
|---|---|---|
| 地图/NPC | 1501/10908 说书人 | 1006/10086 驯宠师 |
| AIInfoAIID | 8001 | 8003 |
| BattleResult / DeathPunish | 1 / 0 | 1 / 0 |
| 两个team字段 | 1 / 1 | 0 / 0 |
| 开战前NpcConversation | 3句 | 2句 |
| FinishConversation | 2句（提到传授太祖长拳） | 3句（提到获得宠物、找驯宠学徒） |
| ScenarioInfoAnimationID | 10019 | 0 |
| PostMissionList | 100179 | 100189 |
| ExpReward / SMoney原值 | 120 / 400 | 1460 / 1800 |

两条都有明确“需战斗 / 单人简单”原文字。100113描述提到抓宠和赠宠，但字段不因此自动成为一个已确认宠物模板/实例奖励；本批没有恢复捕捉或赠宠AI，不能直接发任意训练宠。

### 完成state1的后置显示

state1的原 `0x125c020` 删除active bean后，优先本地FinishConversation（config+0x304非空 → `0x164beb0`）；空时检查NoteInfo，再走后置表现函数0x1255e70。317条有完成对白，故不能假设全部只是移除列表/刷新XP。

100107先显示其2句完成对白；其10019字段是原后续表现关联，并不等于重新开一场战斗或已证实CG播放。100113同样先显示3句完成对白，即使AnimationID0也有本地显示副作用。完成对白的CQuestDialogEnd条件依任务动画/传送等分支而异，不能作为362条统一胜利报告；CEndPlayCG也不是任务战斗结果。

可信battle result落盘后发state1，是服务端通知原客户端显示完成的方向；不能反过来用“客户端发了对话结束/播了完成对白”推断权威战斗胜利。重复state1可能重复完成表现，按既有研究需区分资产幂等和视觉去重。

## N3/S2/S3：原AI关联的实际支持强度

parser确认字段：AIInfoAIID名字VA0x226c004，`0xbb647e`存config+0x254；AIInfoBattleResult VA0x226bfdc，`0xbb64bd`存+0x258；AIInfoTeamSteate VA0x226bf94，`0xbb653b`存+0x260。字段存在和值可确定，结果比较/阵容生成不能仅靠parser推导。

原CBattleAIConfig共2194行，**全部字段集合**：id、talkinfo、tipsinfo、appearchange、playsound、changeground、changegroundeffect、playeffect。首例id50001是“这个家伙可有点不好对付，我们一起击败它吧！”与鼠标左键攻击提示，属于客户端战斗提示/表现配置。它没有敌方单位模板列表、站位、HP/攻击/防御/技能策略字段。

362条任务的244个AIID（1428–8144）与该表ID（50001–52210）集合直接交集为0，8001和8003都无记录。本批未找到两套ID间可靠换算，不能加常量或按序号硬配。此结论不宣称“原服务器没有这些AI”，而是当前客户端表没有足够的正式战斗定义。

原CMonsterConfig共5635行，完整字段是id、name、title、modelID、becatch、showhpbar、showlevel、npctype、bodytype、area1colour、area2colour；CMonsterTypeConfig共50行，只有id与monstertypename。它们可确认名字/模型/可捕捉等显示数据，不能生成正式敌阵和人物战斗属性。后续即使从战斗回放协议得到单位快照，也不能把“可显示一个敌人”当“已复原任务AI/胜负判定”。

## P1：必要基本验证

已运行：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 revival/research_task_battle_admission.py
```

退出0：

- 原4份PFS表CRC/BXML重读、362条计数、244个AIID、0直接AI表关联；
- 原constructor/marshal/decode 0xdd3b30/0xe57320/0xdd3be0执行roundtrip，12字节精确body得到任务100107与synthetic64位NPC key；
- 100107/100113分别执行原type40分支 `0x164343c–0x16434f0`，捕获真实构包0xc4a4c、正确任务/NPC key；
- 原菜单分类函数验证无bean/正常0/ready3/失败2对照，明确菜单类3本身不是授权。

fixture只适配配置lookup、网络发送、人物阈值返回，并选ProcessBarTime0的直接支路；不执行战斗、GUI、线上网络、进度条计时或确认框。原codec验证器范围来自原指令，未做大规模fuzz。stat JSON是本脚本唯一写入证据文件，没有更改任何生产模块。

## 给集成方的已证实 Interface 与未知

请求侧可按精确12字节解析0xc4a4c，再交角色所有者：当前任务真实有效且type40、NPC配置/实体key/地图/距离、当前epoch/generation/位置版本、同任务并发开战与重复请求均由可信admission校验；服务器选择原AI关联，不能信任客户端填写敌人或将CCommit当战斗结果。上述授权细节是服务端恢复设计，不是原codec隐藏提供的保证。

结果侧只接来自正式battle所有者、绑定角色/任务实例/AI关联和唯一battle/settlement身份的可信结果，经角色事务核验后同时完成任务、奖励、后继与回执。原AIInfoBattleResult数值语义、组队资格、计时/用物/特殊目标与进度条任务在未被正式能力覆盖前保持明确缺口；单独训练/wild结果不得混入。

未验证：原服务端AI脚本/敌阵/数值、真实task-PVE开战、权威战斗结果的业务枚举、逃跑/失败/捕捉与任务关系、组队共享完成、剧情显示完整时序、GUI/战斗演出、地图入战恢复、断线重试/并发容量。研究没有建立正式task-PVE owner，也没有以任意训练敌人补齐这些缺口。

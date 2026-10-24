# 序章首技能：太祖长拳节点与原技能同步

补授予规则、等级或费用前，另读 [PROLOGUE_FIRST_SKILL_GUIDE_RESEARCH.md](PROLOGUE_FIRST_SKILL_GUIDE_RESEARCH.md)：已补端游官方六条定向检索，只支持早期习得，具体 grant 契约仍待主策划补全；不由教学文案自动授技能。

本批为research Skill后台委派研究，范围限100179及十门派等价节点。只读原PFS、原映像和当前公开源码；不运行/推进AI8001或任何战斗，不操作当前客户端、在线服、真实DB，不修改实现/中央政策。

## 可以确认什么，不能确认什么

| 问题 | 证据等级 / 结论 |
|---|---|
| 玩家“其他技能”栏里的太祖长拳是哪一项 | `client_verified`：cskillitem100008、cskillshowlist第6类包含100008、cskillshowlistclient100008名称太祖长拳且skilltype1。它是可明确识别的玩家技能身份 |
| 同名500001是否等同100008 | 不能等同。原item表500001也叫太祖长拳、500067叫赵老爵爷-太祖长拳；二者未列入上述玩家其他技能列表，不能凭同名替代 |
| 100179是否直接指定授100008 | **未闭合**。任务完整属性与lists没有skillID或等级字段，只有学习太祖长拳叙事；100008身份很强，但“该任务结算必授该ID”缺直接原授予字段/调用桥 |
| 原任务应授几级 | **unknown**，没有客户端事实证明1级、人物同级或其他值。本文原decoder探针的1和7都是人工fixture，不能变成设计值 |
| 读条完成是否本地写已学技能 | 所查kind5路径只构造CCommit，不写技能map；不能以读条/任务state1/120XP代替技能授予 |
| 已学“其他技能”如何同步 | `client_verified`：SSendOtherSkills0xc36c3，compact map<i32 skillID,i32 value> + byte flag；Process写原技能管理器map+0x40，值供原查询及技能提示消费 |
| 该包能否当单项追加 | **不能**。原消费者删除本包缺失的旧key，再写新值；flag1也会删除缺失项。发送须完整当前other-skill快照，不能用一项/空包覆盖旧技能 |
| 当前是否已有普通人物技能授予Interface | 本批公开源码检查未找到通用已学人物技能持久化/授予/当前完整快照Interface。帮派修炼、宠技能、场次authorized_skills均不能代替 |

结论中的未知只限定原服事实，不批准假授技能，也不以缺证阻止主策划另行设计。若补全授予ID/等级/时点，应由技能所有者提供公开同角色事务Interface并独立标designed；本报告不发布该规则。

## 一手来源与校验

本批直接读取`artres/config.pfs`各成员，经原长度/CRC检查后BXML解码；原映像VA基址0x400000。所有地址绑定映像SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

| PFS内路径（均autoconfig/…xml） | 原字节数 | CRC32 | 原成员SHA256 |
|---|---:|---|---|
| knight.gsp.task.cmainmissioninfo | 2026233 | 3f7ab7b3 | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |
| knight.gsp.role.createroleconfig | 13107 | 0758d770 | 770da32d88784144e453c386c9cce05de03746943eb6004158d3cc53c9428132 |
| knight.gsp.role.schoolinfo | 4075 | fe9fe433 | 3ed66a6f40f615b6d89372a1775246a33c644b9d612df7794532edb656332a2d |
| knight.gsp.skill.cskillitem | 107547 | b5d9fdd8 | 2a8645ae11267eb3cbbeeab0f56f4be8f8fe9b4fa95f6c4026448f59afc07194 |
| knight.gsp.skill.cskillshowlist | 4644 | 118178bc | 67632b0dc85a979637846c3d1717bac6f75b48d93a9661a381ea92f95931c5ac |
| knight.gsp.skill.cskillshowlistclient | 11110 | 112a2193 | eda1374328a6a2574cc53b6eee53f1e81b144f5d9da44965c89a647940d8d6eb |

全文不以派生catalog代替原表。原创建路线另与现有catalog比对身份时，以本批原RequestRoleIDList/PostMissionList为准。完整10节点原字段/列表、相关同名技能行和43路线附录随本文保存。

## 十个原节点：完整字段没有授技能ID/等级

| 节点 | 原唯一入边 | 原唯一出边 |
|---|---|---|
| 100179 | 100107 | 100190 |
| 100279 | 100205 | 100290 |
| 100379 | 100305 | 100390 |
| 100479 | 100405 | 100490 |
| 100579 | 100505 | 100590 |
| 100679 | 100605 | 100690 |
| 100779 | 100705 | 100790 |
| 100879 | 100805 | 100890 |
| 100979 | 100905 | 100990 |
| 103279 | 103207 | 103290 |

10行除id、PostMissionList外属性完全相同：MissionType10、ProcessBarTime1、ProcessBarText“掌握技能”、ActiveNpc10908说书人、ActiveMap1501；ExpReward120，MoneyReward/PetExpReward/ShengWang/SMoney0；Min/Max/Trans等级和Transform全0；Jump及Map/X/Y全0；AIID、UseItemID、TargetID/Num、GiveBackMoney/PetID、OtherType、TimeLimit、MiniStep/MaxStep全0；AnimationID/BranchNpcID0。

每行仅有两个子列表：唯一PostMissionList；DisPlayNPCID=[10910,10911,10912]。**没有Start、Finish、Note、Branch、RewardItem、RequestRole或任何Skill列表**。DisPlayNPCID不能转换为skillID，也不是要求交付的技能清单。

原描述/目的/追踪均说向说书人学习太祖长拳，但没有数值授予契约。100107等前置战斗的Finish两句已经说“这套太祖长拳就传授于你，你先参悟一下吧”；随后才到100179读条节点。这进一步说明文案不能确定实际授予发生在前战结算、激活100179、读条完成还是之后。

## 43条原创建路线逐条追边

从原createroleconfig的schools列表枚举合法(role,school)，由schoolinfo.schoolmapid定位各intro后继的home map；原intro的PostMissionList逐支以RequestRoleIDList选择对应首师父任务，再逐条跟随真实Post边到ProcessBarText“掌握技能”节点。43对全部各有唯一已找到路径；没有通过100x79/103279的ID规律计算目标。

下表“首师父”列的角色ID→任务ID加上共同尾链，对应全部43条；附录另保留每对的完整路径，便于审查。

| school / 原名 | intro root | 角色ID→首师父任务 | 首师父后的原共同尾链（至掌握技能） |
|---|---|---|---|
| 11 古墓派 | 100101 | 2→100184；5→100185；9→100186；10→100187 | 100188→100104→100105→100160→100106→100107→100179 |
| 12 丐帮 | 100201 | 1→100283；3→100284；4→100285；6→100286；7→100287 | 100288→100203→100204→100260→100206→100205→100279 |
| 13 西域密宗 | 100301 | 1→100383；3→100384；5→100385；6→100386；7→100387 | 100388→100303→100304→100360→100306→100305→100379 |
| 14 白驼山庄 | 100401 | 3→100484；4→100485；7→100486；8→100487 | 100488→100403→100404→100460→100406→100405→100479 |
| 15 大理段氏 | 100501 | 2→100584；4→100585；8→100586；9→100587 | 100588→100503→100504→100560→100506→100505→100579 |
| 16 全真教 | 100601 | 1→100683；5→100685；6→100686；10→100687 | 100688→100603→100604→100660→100606→100605→100679 |
| 17 桃花岛 | 100701 | 2→100784；5→100785；6→100786；10→100787 | 100788→100703→100704→100760→100706→100705→100779 |
| 18 绝情谷 | 100801 | 1→100883；4→100885；8→100886；9→100887 | 100888→100803→100804→100860→100806→100805→100879 |
| 19 百花谷 | 100901 | 2→100984；3→100985；7→100986；8→100987 | 100988→100903→100904→100960→100906→100905→100979 |
| 111 少林 | 103201 | 4→103284；5→103285；9→103286；10→103287；1→103283 | 103288→103204→103205→103260→103206→103207→103279 |

这是原配置可达关系，**不是本次真实角色已自然走完**，也不授权跳过前面正式战斗。古墓role9明确为 `100101→100186→100188→100104→100105→100160→100106→100107→100179`。100106的实例/传送合同由主线程处理，本研究不改世界坐标或实例。

### 保留旧非自然族

原101001仍存在：type50、Npc0/Map0、Animation0，RequestMissionList原序列为`[100199,100299,100399,100499,100599,100699,100799,100899,100999]`，Post为101002。其链为`101001→101002(type10血手印)→101003(type40)→101004(type40)→101005…`；101003的Finish也含相同传太祖长拳文案，却直接去101004，**没有插入本批十个“掌握技能”读条节点**。

本批43对到首技能的自然Post路径不经过该1010xx族；保留原列表和原边，不删除、不合并、不强行将其改向100179。RequestMissionList列表的全满足/任一满足及原服务端开启条件本批未研究，不能因为“旧族”就断言永远不可达。

## 原读条完成链：只有任务提交

复读[JIAXING_MAINLINE_NEXT_AUDIT.md](JIAXING_MAINLINE_NEXT_AUDIT.md)与[TASK_NPC_PROGRESS_RESEARCH.md](TASK_NPC_PROGRESS_RESEARCH.md)的原地址：

- parser `0xbb5d19..0xbb5d45`把ProcessBarTime写config+0xd8；type10 `0x16433af..0x16433df`检查>0，将整数转float并启动本地kind5进度UI `0x8114a0→0x16c4140`。
- `0x16c416b..0x16c419b`保存阈值、kind和关联taskID，`0x16c41d4..0x16c41dc`保存NPCkey。开始路径没有专门开始ACK。
- WindowUpdate订阅 `0x16c4cb8..0x16c4cf8`，事件0x2924708原名WindowUpdate；`0x16c49c7..0x16c49f7`按float delta累计比较，到阈值调`0x16c4490`。
- kind5 `0x16c47c8..0x16c47ff`仅构造CCommitScenarioQuest0xc4a44，taskID来自控件+0x26c，NPCkey来自进度UI；`0x16c492b..0x16c4933`发送。body仍16字节`BE i32 taskID | BE u64 npcKey | BE i32 option0`。没有skillID/等级字段，也没有本段技能map写入。
- 原任务state1 handler `0x125c020`按Finish→Note→fallback处理；本十行没有Finish/Note/Animation/Jump，走`0x125c1c5..0x125c1c8→0x1255e70`。这个本地任务表现分支不能当作持久技能授权或技能等级刷新。

原值1仅证明本地float阈值1，绝对秒单位沿前报告尚未闭合；不为授技能节点补造1秒原服门槛。本批没有跑任何AI8001/原战斗或读取在线角色已学技能。

## 原技能身份：100008有三份互相支持的玩家资源

- cskillitem100008：skillname太祖长拳；sType多体伤害招式；normalIcon327；targettype480；effectid10011；bCanUseInBattle1；描述攻击2个敌人；原消耗文案为“消耗真气随人物等级提升”。这不提供原服耗蓝/伤害/等级公式。
- cskillshowlist第6行classify“其他技能”的skillnumber列表明确含100008；同列表没有500001或500067。
- cskillshowlistclient100008：skillname太祖长拳、skilltype1，玩家显示行明确存在。

所以100008作为**玩家该名称技能身份**可标client_verified；“100179完成时以某等级授100008”仍不是被该列表直接证明的原服事实。不能沿用训练baseline的10耗蓝/最多2敌公式冒充正式技能数值，也不能将effect10011当skillID。

## SSendOtherSkills：下行驱动原已学map与值刷新

原RTTI `.?AVSSendOtherSkills@skill@gsp@knight@@`；vtable `0x22852e8`：marshal `0xf30ef0`、decode `0xf30e50`、Process `0x12d6810`；ctor `0xf30da0`在`0xf30e00`写type **0xc36c3**，+0x14尾byte默认0。

wire：`compact_uint count | count×(BE i32 key, BE i32 value) | byte flag`。例1项共10字节。map不是SkillInfo bean列表，不要因为另有RTTI SkillInfo的两个int，就在此包每条加多余bean头或taskID。

Process `0x12d6811..0x12d683c`要求原技能manager global`0x29448a4`存在；`0x12d681c`把flag是否恰好等于1转为bool，复制packet+8的map，调用manager方法`0x12d60f0`。它没有在包内按任务ID识别100179，不是任务完成回执。

原消费者行为：

1. `0x12d6117..0x12d6127`定位manager+0x40旧map；`0x12d6150..0x12d6221`逐旧key查本次map并对缺失项走`0x4eac10`删除，同时可能移除快捷栏项。**不是只遍历传入项的增量追加**。
2. `0x12d623b..0x12d62c7`遍历新map；若key此前没有且尾bool为0，`0x12d62cc..0x12d6329`可能尝试原快捷栏默认位置设置；bool1跳过这一部分。本文不给尾byte擅自命名为append/replace。
3. `0x12d6344..0x12d6353`将输入value原样写入旧map的对应key；不是无条件改成1。
4. 原值查询 `0x12d1d50` 从manager+0x40按key查找，`0x12d1d97`返回node+0x10的value，缺失返回0。`0x1071a82..0x1071b06`及`0x12d7dc2..0x12d7e00`在分类1/8调用该查询，把值作为技能提示构造参数；所查消费与技能级别显示关联，但原任务实际应授的数值仍未出现。
5. 原已学/存在检查`0x12d55f0`先经`0x1070ea0`按ID范围分类。100008原分类为1，经switch `0x12d5864[0]→0x12d56e6`查询manager+0x40是否有key。代码另有`0x12d5725`硬编码100008的true分支，但位于分类2 arm，**不能跳过分类就据此声称100008永远已学或无需同步**。离线probe亦验证空map检查100008=0。

原客户端的数据模型有单独的下行学习状态更新；本任务本地读条不能代替它。原包存在并不证明恢复项目已实现持久化角色技能账本。若未来下发必须发**当前完整other map**；一项包会删掉未包含的原其他技能，空map会清该集合，flag1不保护旧项。

### 少量隔离原指令验证

内联Python `-B`复用`research_battle.NativeBattleDecoder`的原映像harness；未执行其会写索引的main。原ctor0xf30da0和decode0xf30e50执行；创建隔离的空manager+0x40，随后直接执行原消费者0x12d60f0，原值查询0x12d1d50和存在检查0x12d55f0。Process本身本批只静态读取，未将此说成完整GUI链。

| 人工输入map / flag | body_hex | 原存在检查100008 | 原查询值 | 原map大小 |
|---|---|---:|---:|---:|
| {100008:1} / 1 | 01000186a80000000101 | 1 | 1 | 1 |
| {100008:7} / 1 | 01000186a80000000701 | 1 | 7 | 1 |
| {} / 1 | 0001 | 0 | 0 | 0 |

初始空map时检查为0。只适配分配器、CRT/内存等系统边界，快捷栏UI单例设不存在，未发送网络/创建角色/改变存档。样本1和7仅确认value保留和更新，不证明原任务初始技能等级或可升等级。此次验证闭合了空map删除效果，仍未验真实客户端图标、快捷栏、提示和战斗可用性。

## 当前公开Interface审查

| 已有源码契约 | 可用范围 / 与本节点缺口 |
|---|---|
| `battle_owner.Participant.authorized_skills: tuple` | 场次创建的冻结输入；只承接已经可信授权的技能，不是持久已学集合或授予API |
| `training_battle.TrainingBattle(... authorized_skills=())` | 按训练白名单校验并构建场次技能；训练规则不证明原正式太祖长拳或任务授予 |
| `role_practice.load_rules/read/initialize/plan` | 帮派修炼，技能范围360001..360007及政策/材料/帮派许可；不应把100008塞进该白名单或借它完成普通授技能 |
| `pet_skills`、`Inventory.grant_pet_timed_skill` | 宠物实例技能；主体/状态/协议不同，不能授予人物100008 |
| 已有任务调用方事务与奖励/链Interface | 可以承接有授权的参与方，但没有技能owner的公开同事务grant/read-current-others契约时，不能用120XP或task completed伪造技能已落盘 |

本批对工作区非runtime/生成目录的公开源码做定向检索和读取，未发现普通人物已学技能账本/通用grant/完整other快照契约。结论为本次可见源码范围；不改任何owner接口、不调用私有SQL、不对另一个技能窗口未交付的接口作承诺。后续技能owner若提供接口，应以明确授予来源、实例/任务幂等、原等级规则、当前完整快照和当前租约事务为契约，另记录实施与验证。

## 精确未闭合事实

- 100179及十等价节点应授的原skillID字段/调用桥、原初始等级、重复已学时规则、升级上限与原服数值公式，均未取得。玩家技能身份100008不自动等于已证授予recipe。
- 实际授予时点是100107等前战完成、100179激活、读条完成还是后战入场，本客户端任务行未说明；不能仅凭对白位置决定。
- 43条图可达不等于真实角色已走到该节点；AI8001/其他原正式PVE仍由战斗owner单独恢复/授权，本批不运行、不推进、不注入胜利。
- SSendOtherSkills的完整集合范围、恢复服原存档基线与尾byte全部业务语义另验；本批已证它会删缺失项，不能安全单项追加。
- 正式角色技能存储、原生技能显示/快捷栏更新与战斗使用、重连及并发事务未实现/未实测，不把本文的原codec/consumer探针当部署或可玩性验收。

## 方法、产物与未验范围

本批重新读取research Skill、ARCHITECTURE、DESIGN_AUTHORITY；research用于逐项回到原PFS/native、只围绕序章10节点、用43原边替代ID猜测。当前窗口已是后台委派，不再递归开agent。技能身份、任务授予recipe、技能存储Interface、客户端显示与正式战斗分开记录，符合单一所有者与同角色调用方事务约束。

完成验证：六原表长度/CRC/SHA、10任务全属性/lists、43合法组合与原学校列表一致且各有唯一到目标路径、原kind5/技能下行静态链、上表少量原decoder/消费者/查询执行。未执行生产玩法、真实DB、GUI、在线服或战斗，未修改.py、catalog、policy或shared。

唯一产物 `revival/evidence/PROLOGUE_FIRST_SKILL_RESEARCH.md`，写入时间2026-10-23T19:28:58+08:00。现有公开源码仅读取，未创造授技能实现或政策；用户序章主线和100106合同保持由主线程推进。

## 附录A：十节点完整原BXML字段/列表

### 100179

```json
{"node":"record","attrs":{"id":"100179","MissionName":"[主线]序章缘起","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"120","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"1","ProcessBarText":"掌握技能","MissionType":"10","ActiveInfoNpcID":"10908","ActiveInfoMapID":"1501","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"哎呀，你虽有慧根，打得却毫无章法，看来门派武功还尚未入门，实在不符合我的美学！这套太祖长拳就传授于你，你先参悟一下吧！\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳。\"></T>","TaskInfoTraceListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"100190"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10910"},{"node":"int","attrs":{},"text":"10911"},{"node":"int","attrs":{},"text":"10912"}]}]}
```

### 100279

```json
{"node":"record","attrs":{"id":"100279","MissionName":"[主线]序章缘起","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"120","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"1","ProcessBarText":"掌握技能","MissionType":"10","ActiveInfoNpcID":"10908","ActiveInfoMapID":"1501","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"哎呀，你虽有慧根，打得却毫无章法，看来门派武功还尚未入门，实在不符合我的美学！这套太祖长拳就传授于你，你先参悟一下吧！\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳。\"></T>","TaskInfoTraceListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"100290"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10910"},{"node":"int","attrs":{},"text":"10911"},{"node":"int","attrs":{},"text":"10912"}]}]}
```

### 100379

```json
{"node":"record","attrs":{"id":"100379","MissionName":"[主线]序章缘起","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"120","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"1","ProcessBarText":"掌握技能","MissionType":"10","ActiveInfoNpcID":"10908","ActiveInfoMapID":"1501","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"哎呀，你虽有慧根，打得却毫无章法，看来门派武功还尚未入门，实在不符合我的美学！这套太祖长拳就传授于你，你先参悟一下吧！\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳。\"></T>","TaskInfoTraceListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"100390"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10910"},{"node":"int","attrs":{},"text":"10911"},{"node":"int","attrs":{},"text":"10912"}]}]}
```

### 100479

```json
{"node":"record","attrs":{"id":"100479","MissionName":"[主线]序章缘起","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"120","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"1","ProcessBarText":"掌握技能","MissionType":"10","ActiveInfoNpcID":"10908","ActiveInfoMapID":"1501","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"哎呀，你虽有慧根，打得却毫无章法，看来门派武功还尚未入门，实在不符合我的美学！这套太祖长拳就传授于你，你先参悟一下吧！\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳。\"></T>","TaskInfoTraceListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"100490"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10910"},{"node":"int","attrs":{},"text":"10911"},{"node":"int","attrs":{},"text":"10912"}]}]}
```

### 100579

```json
{"node":"record","attrs":{"id":"100579","MissionName":"[主线]序章缘起","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"120","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"1","ProcessBarText":"掌握技能","MissionType":"10","ActiveInfoNpcID":"10908","ActiveInfoMapID":"1501","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"哎呀，你虽有慧根，打得却毫无章法，看来门派武功还尚未入门，实在不符合我的美学！这套太祖长拳就传授于你，你先参悟一下吧！\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳。\"></T>","TaskInfoTraceListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"100590"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10910"},{"node":"int","attrs":{},"text":"10911"},{"node":"int","attrs":{},"text":"10912"}]}]}
```

### 100679

```json
{"node":"record","attrs":{"id":"100679","MissionName":"[主线]序章缘起","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"120","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"1","ProcessBarText":"掌握技能","MissionType":"10","ActiveInfoNpcID":"10908","ActiveInfoMapID":"1501","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"哎呀，你虽有慧根，打得却毫无章法，看来门派武功还尚未入门，实在不符合我的美学！这套太祖长拳就传授于你，你先参悟一下吧！\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳。\"></T>","TaskInfoTraceListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"100690"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10910"},{"node":"int","attrs":{},"text":"10911"},{"node":"int","attrs":{},"text":"10912"}]}]}
```

### 100779

```json
{"node":"record","attrs":{"id":"100779","MissionName":"[主线]序章缘起","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"120","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"1","ProcessBarText":"掌握技能","MissionType":"10","ActiveInfoNpcID":"10908","ActiveInfoMapID":"1501","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"哎呀，你虽有慧根，打得却毫无章法，看来门派武功还尚未入门，实在不符合我的美学！这套太祖长拳就传授于你，你先参悟一下吧！\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳。\"></T>","TaskInfoTraceListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"100790"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10910"},{"node":"int","attrs":{},"text":"10911"},{"node":"int","attrs":{},"text":"10912"}]}]}
```

### 100879

```json
{"node":"record","attrs":{"id":"100879","MissionName":"[主线]序章缘起","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"120","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"1","ProcessBarText":"掌握技能","MissionType":"10","ActiveInfoNpcID":"10908","ActiveInfoMapID":"1501","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"哎呀，你虽有慧根，打得却毫无章法，看来门派武功还尚未入门，实在不符合我的美学！这套太祖长拳就传授于你，你先参悟一下吧！\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳。\"></T>","TaskInfoTraceListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"100890"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10910"},{"node":"int","attrs":{},"text":"10911"},{"node":"int","attrs":{},"text":"10912"}]}]}
```

### 100979

```json
{"node":"record","attrs":{"id":"100979","MissionName":"[主线]序章缘起","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"120","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"1","ProcessBarText":"掌握技能","MissionType":"10","ActiveInfoNpcID":"10908","ActiveInfoMapID":"1501","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"哎呀，你虽有慧根，打得却毫无章法，看来门派武功还尚未入门，实在不符合我的美学！这套太祖长拳就传授于你，你先参悟一下吧！\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳。\"></T>","TaskInfoTraceListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"100990"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10910"},{"node":"int","attrs":{},"text":"10911"},{"node":"int","attrs":{},"text":"10912"}]}]}
```

### 103279

```json
{"node":"record","attrs":{"id":"103279","MissionName":"[主线]序章缘起","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"120","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"1","ProcessBarText":"掌握技能","MissionType":"10","ActiveInfoNpcID":"10908","ActiveInfoMapID":"1501","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"哎呀，你虽有慧根，打得却毫无章法，看来门派武功还尚未入门，实在不符合我的美学！这套太祖长拳就传授于你，你先参悟一下吧！\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳。\"></T>","TaskInfoTraceListA":"<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳\"></T>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"103290"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10910"},{"node":"int","attrs":{},"text":"10911"},{"node":"int","attrs":{},"text":"10912"}]}]}
```

## 附录B：原技能相关行

### cskillitem 100008

```json
{"node":"record","attrs":{"id":"100008","skillname":"太祖长拳","sType":"多体伤害招式","paramA":"0.0","paramB":"0.0","costA":"消耗：消耗真气随人物等级提升","paramC":"0.0","paramD":"0.0","costTypeA":"70","costTypeB":"-1","normalIcon":"327","skilldescribe":"<T t=\"虽然初入江湖，却也有着不俗的精气神。使用自身力量，攻击2个敌人。\" c=\"ffffff99\"></T>","targettype":"480","bCanUseInBattle":"1","effectid":"10011"}}
```

### cskillitem 500001

```json
{"node":"record","attrs":{"id":"500001","skillname":"太祖长拳","sType":" 多体法术攻击","paramA":"0.0","paramB":"15.0","costA":"消耗：$parameter1$真气","paramC":"0.0","paramD":"0.0","costTypeA":"70","costTypeB":"-1","normalIcon":"23","skilldescribe":"虽然初入江湖，却也有着不俗的精气神。使用自身力量，攻击2个敌人。","targettype":"480","bCanUseInBattle":"1","effectid":"10011"}}
```

### cskillitem 500067

```json
{"node":"record","attrs":{"id":"500067","skillname":"赵老爵爷-太祖长拳","sType":" 多体法术攻击","paramA":"0.0","paramB":"1.0","costA":"消耗：$parameter1$真气","paramC":"0.0","paramD":"0.0","costTypeA":"70","costTypeB":"-1","normalIcon":"23","skilldescribe":"虽然初入江湖，却也有着不俗的精气神。使用自身力量，攻击2个敌人。","targettype":"480","bCanUseInBattle":"1","effectid":"10011"}}
```

### cskillshowlist 6

```json
{"node":"record","attrs":{"id":"6","classify":"其他技能"},"children":[{"node":"skillnumber","attrs":{},"children":[{"node":"int","attrs":{},"text":"100008"},{"node":"int","attrs":{},"text":"100007"},{"node":"int","attrs":{},"text":"100009"},{"node":"int","attrs":{},"text":"310202"},{"node":"int","attrs":{},"text":"350001"},{"node":"int","attrs":{},"text":"700001"},{"node":"int","attrs":{},"text":"700002"},{"node":"int","attrs":{},"text":"700003"},{"node":"int","attrs":{},"text":"360001"},{"node":"int","attrs":{},"text":"360002"},{"node":"int","attrs":{},"text":"360003"},{"node":"int","attrs":{},"text":"360004"},{"node":"int","attrs":{},"text":"360005"},{"node":"int","attrs":{},"text":"360006"},{"node":"int","attrs":{},"text":"360007"},{"node":"int","attrs":{},"text":"600018"},{"node":"int","attrs":{},"text":"700004"},{"node":"int","attrs":{},"text":"380001"},{"node":"int","attrs":{},"text":"380002"},{"node":"int","attrs":{},"text":"380003"},{"node":"int","attrs":{},"text":"380004"},{"node":"int","attrs":{},"text":"380005"},{"node":"int","attrs":{},"text":"380006"},{"node":"int","attrs":{},"text":"380007"},{"node":"int","attrs":{},"text":"380008"},{"node":"int","attrs":{},"text":"380009"}]}]}
```

### cskillshowlistclient 100008

```json
{"node":"record","attrs":{"id":"100008","skillname":"太祖长拳","skilltype":"1"}}
```

## 附录C：43对完整原后继路径

```json
[{"role_id":2,"role_name":"秦少游","school_id":11,"intro_root":100101,"path":[100101,100184,100188,100104,100105,100160,100106,100107,100179]},{"role_id":5,"role_name":"杨空岳","school_id":11,"intro_root":100101,"path":[100101,100185,100188,100104,100105,100160,100106,100107,100179]},{"role_id":9,"role_name":"云夕","school_id":11,"intro_root":100101,"path":[100101,100186,100188,100104,100105,100160,100106,100107,100179]},{"role_id":10,"role_name":"韩忆","school_id":11,"intro_root":100101,"path":[100101,100187,100188,100104,100105,100160,100106,100107,100179]},{"role_id":1,"role_name":"楚天河","school_id":12,"intro_root":100201,"path":[100201,100283,100288,100203,100204,100260,100206,100205,100279]},{"role_id":3,"role_name":"燕重光","school_id":12,"intro_root":100201,"path":[100201,100284,100288,100203,100204,100260,100206,100205,100279]},{"role_id":4,"role_name":"司马长风","school_id":12,"intro_root":100201,"path":[100201,100285,100288,100203,100204,100260,100206,100205,100279]},{"role_id":6,"role_name":"唐七七","school_id":12,"intro_root":100201,"path":[100201,100286,100288,100203,100204,100260,100206,100205,100279]},{"role_id":7,"role_name":"独孤月","school_id":12,"intro_root":100201,"path":[100201,100287,100288,100203,100204,100260,100206,100205,100279]},{"role_id":1,"role_name":"楚天河","school_id":13,"intro_root":100301,"path":[100301,100383,100388,100303,100304,100360,100306,100305,100379]},{"role_id":3,"role_name":"燕重光","school_id":13,"intro_root":100301,"path":[100301,100384,100388,100303,100304,100360,100306,100305,100379]},{"role_id":5,"role_name":"杨空岳","school_id":13,"intro_root":100301,"path":[100301,100385,100388,100303,100304,100360,100306,100305,100379]},{"role_id":6,"role_name":"唐七七","school_id":13,"intro_root":100301,"path":[100301,100386,100388,100303,100304,100360,100306,100305,100379]},{"role_id":7,"role_name":"独孤月","school_id":13,"intro_root":100301,"path":[100301,100387,100388,100303,100304,100360,100306,100305,100379]},{"role_id":3,"role_name":"燕重光","school_id":14,"intro_root":100401,"path":[100401,100484,100488,100403,100404,100460,100406,100405,100479]},{"role_id":4,"role_name":"司马长风","school_id":14,"intro_root":100401,"path":[100401,100485,100488,100403,100404,100460,100406,100405,100479]},{"role_id":7,"role_name":"独孤月","school_id":14,"intro_root":100401,"path":[100401,100486,100488,100403,100404,100460,100406,100405,100479]},{"role_id":8,"role_name":"铃小雨","school_id":14,"intro_root":100401,"path":[100401,100487,100488,100403,100404,100460,100406,100405,100479]},{"role_id":2,"role_name":"秦少游","school_id":15,"intro_root":100501,"path":[100501,100584,100588,100503,100504,100560,100506,100505,100579]},{"role_id":4,"role_name":"司马长风","school_id":15,"intro_root":100501,"path":[100501,100585,100588,100503,100504,100560,100506,100505,100579]},{"role_id":8,"role_name":"铃小雨","school_id":15,"intro_root":100501,"path":[100501,100586,100588,100503,100504,100560,100506,100505,100579]},{"role_id":9,"role_name":"云夕","school_id":15,"intro_root":100501,"path":[100501,100587,100588,100503,100504,100560,100506,100505,100579]},{"role_id":1,"role_name":"楚天河","school_id":16,"intro_root":100601,"path":[100601,100683,100688,100603,100604,100660,100606,100605,100679]},{"role_id":5,"role_name":"杨空岳","school_id":16,"intro_root":100601,"path":[100601,100685,100688,100603,100604,100660,100606,100605,100679]},{"role_id":6,"role_name":"唐七七","school_id":16,"intro_root":100601,"path":[100601,100686,100688,100603,100604,100660,100606,100605,100679]},{"role_id":10,"role_name":"韩忆","school_id":16,"intro_root":100601,"path":[100601,100687,100688,100603,100604,100660,100606,100605,100679]},{"role_id":2,"role_name":"秦少游","school_id":17,"intro_root":100701,"path":[100701,100784,100788,100703,100704,100760,100706,100705,100779]},{"role_id":5,"role_name":"杨空岳","school_id":17,"intro_root":100701,"path":[100701,100785,100788,100703,100704,100760,100706,100705,100779]},{"role_id":6,"role_name":"唐七七","school_id":17,"intro_root":100701,"path":[100701,100786,100788,100703,100704,100760,100706,100705,100779]},{"role_id":10,"role_name":"韩忆","school_id":17,"intro_root":100701,"path":[100701,100787,100788,100703,100704,100760,100706,100705,100779]},{"role_id":1,"role_name":"楚天河","school_id":18,"intro_root":100801,"path":[100801,100883,100888,100803,100804,100860,100806,100805,100879]},{"role_id":4,"role_name":"司马长风","school_id":18,"intro_root":100801,"path":[100801,100885,100888,100803,100804,100860,100806,100805,100879]},{"role_id":8,"role_name":"铃小雨","school_id":18,"intro_root":100801,"path":[100801,100886,100888,100803,100804,100860,100806,100805,100879]},{"role_id":9,"role_name":"云夕","school_id":18,"intro_root":100801,"path":[100801,100887,100888,100803,100804,100860,100806,100805,100879]},{"role_id":2,"role_name":"秦少游","school_id":19,"intro_root":100901,"path":[100901,100984,100988,100903,100904,100960,100906,100905,100979]},{"role_id":3,"role_name":"燕重光","school_id":19,"intro_root":100901,"path":[100901,100985,100988,100903,100904,100960,100906,100905,100979]},{"role_id":7,"role_name":"独孤月","school_id":19,"intro_root":100901,"path":[100901,100986,100988,100903,100904,100960,100906,100905,100979]},{"role_id":8,"role_name":"铃小雨","school_id":19,"intro_root":100901,"path":[100901,100987,100988,100903,100904,100960,100906,100905,100979]},{"role_id":4,"role_name":"司马长风","school_id":111,"intro_root":103201,"path":[103201,103284,103288,103204,103205,103260,103206,103207,103279]},{"role_id":5,"role_name":"杨空岳","school_id":111,"intro_root":103201,"path":[103201,103285,103288,103204,103205,103260,103206,103207,103279]},{"role_id":9,"role_name":"云夕","school_id":111,"intro_root":103201,"path":[103201,103286,103288,103204,103205,103260,103206,103207,103279]},{"role_id":10,"role_name":"韩忆","school_id":111,"intro_root":103201,"path":[103201,103287,103288,103204,103205,103260,103206,103207,103279]},{"role_id":1,"role_name":"楚天河","school_id":111,"intro_root":103201,"path":[103201,103283,103288,103204,103205,103260,103206,103207,103279]}]
```

## 附录D：保留101001–101004旧族完整原行

### 101001

```json
{"node":"record","attrs":{"id":"101001","MissionName":"[主线]序章缘起","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"50","ActiveInfoNpcID":"0","ActiveInfoMapID":"0","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"老头子虽然不知道，但那边有一个神神秘秘的说书人，去问问他好了。\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"询问陆家庄外的\"></T><G t=\"说书人\" npcid=\"10083\"></G><T t=\"。\"></T>","TaskInfoTraceListA":"<T t=\"询问陆家庄外的\"></T><G t=\"说书人\" npcid=\"10083\"></G>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"RequestMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"100199"},{"node":"int","attrs":{},"text":"100299"},{"node":"int","attrs":{},"text":"100399"},{"node":"int","attrs":{},"text":"100499"},{"node":"int","attrs":{},"text":"100599"},{"node":"int","attrs":{},"text":"100699"},{"node":"int","attrs":{},"text":"100799"},{"node":"int","attrs":{},"text":"100899"},{"node":"int","attrs":{},"text":"100999"}]},{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"101002"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10212"}]},{"node":"ScenarioInfoNpcConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"<T t=\"这位少侠，我看你天庭饱满，骨骼精奇，眉宇间透露出一股王霸之气，将来一定会成为号令天下，万人景仰的武林盟主。\" ></T><T t=\"怎么样，要我给你算一卦么？\" c=\"ffffff33\" ></T>"},{"node":"string","attrs":{},"text":"<T t=\"前辈说笑了，我其实是想来\"></T><T t=\"向你打听一下桃花岛主黄药师的下落\" c=\"ffffff33\"></T><T t=\"的，不知前辈可否告知呢？\"></T>"},{"node":"string","attrs":{},"text":"<T t=\"哈哈哈，所谓前辈，都是死得早的那一辈。不如叫我先生更好些。至于黄药师嘛……我正好知道一点，\"></T><T t=\"你去前面不远的陆家庄看看，他也许就在那里。\" c=\"ffffff33\"></T>"}]},{"node":"ScenarioInfoNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10083"},{"node":"int","attrs":{},"text":"1"},{"node":"int","attrs":{},"text":"10083"}]}]}
```

### 101002

```json
{"node":"record","attrs":{"id":"101002","MissionName":"[主线]序章缘起","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","NoteInfo":"触摸血手印后，周围的世界仿佛发生了变化。神秘的说书人正站在你面前……","ExpReward":"0","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"0","RewardMapJumpType":"3","RewardMapID":"1501","RewardMapXPos":"63","RewardMapYPos":"79","ProcessBarTime":"3","ProcessBarText":"触摸血手印","MissionType":"10","ActiveInfoNpcID":"10498","ActiveInfoMapID":"1006","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"少侠如果想要知晓真相，就去看看前面墙上的血手印，一定会有所发现。\" c=\"ff12c4ff\" ></T>","TaskInfoPurposeListA":"<T t=\"调查陆家庄的\"></T><G t=\"血手印\" npcid=\"10498\"></G><T t=\"。\"></T>","TaskInfoTraceListA":"<T t=\"调查陆家庄的\"></T><G t=\"血手印\" npcid=\"10498\"></G>","AIInfoAIID":"0","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"101003"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10083"}]}]}
```

### 101003

```json
{"node":"record","attrs":{"id":"101003","MissionName":"[主线]序章缘起","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"240","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"400","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"40","ActiveInfoNpcID":"10908","ActiveInfoMapID":"1501","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"触摸血手印后，周围的世界仿佛发生了变化。神秘的说书人在旁边向你招手。\" c=\"ff12c4ff\" ></T><T t=\"【战斗难度：单人简单难度，与任务等级接近的玩家可以单人轻松完成的战斗】\" c=\"ffe9f231\"></T>","TaskInfoPurposeListA":"<T t=\"询问陆家庄外的\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"（需战斗）。\"></T>","TaskInfoTraceListA":"<T t=\"询问陆家庄外的\"></T><G t=\"说书人\" npcid=\"10908\"></G><I s=\"MainControl\" i=\"zhan\"></I>","AIInfoAIID":"8001","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","AIInfoBattleLevel":"【战斗难度：单人简单】","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"10019","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"101004"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10909"}]},{"node":"ScenarioInfoNpcConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"<T t=\"少年人，你终于来了。我等了你好久了。\" ></T>"},{"node":"string","attrs":{},"text":"<T t=\"前……先生，这里发生了什么事？为什么这里的气氛变得这么诡异？\" ></T>"},{"node":"string","attrs":{},"text":"<T t=\"我知道你有很多疑问，有时间我会慢慢向你解释的，现在\"></T><T t=\"先解决掉眼前这些麻烦的家伙吧！\"  c=\"ffffff33\"></T>"}]},{"node":"ScenarioInfoNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10908"},{"node":"int","attrs":{},"text":"1"},{"node":"int","attrs":{},"text":"10908"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"<T t=\"哎呀，你虽有慧根，打得却毫无章法，看来门派武功还尚未入门，实在不符合我的美学！\"></T>"},{"node":"string","attrs":{},"text":"<T t=\"这套太祖长拳\" c=\"ffffff33\" ></T><T t=\"就传授于你，你先参悟一下吧！\"></T>"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10908"},{"node":"int","attrs":{},"text":"10908"}]}]}
```

### 101004

```json
{"node":"record","attrs":{"id":"101004","MissionName":"[主线]序章缘起","MissionTypeString":"主线剧情","MinLevel":"0","MaxLevel":"0","TransMinLevel":"0","TransMaxLevel":"0","TransformID":"0","ExpReward":"255","MoneyReward":"0","PetExpReward":"0","ShengWang":"0","SMoney":"600","RewardMapJumpType":"0","RewardMapID":"0","RewardMapXPos":"0","RewardMapYPos":"0","ProcessBarTime":"0","MissionType":"40","ActiveInfoNpcID":"10908","ActiveInfoMapID":"1501","ActiveInfoLeftPos":"0","ActiveInfoTopPos":"0","ActiveInfoRightPos":"0","ActiveInfoBottomPos":"0","ActiveInfoTargetID":"0","ActiveInfoTargetNum":"0","ActiveInfoMiniStep":"0","ActiveInfoStepProbability":"0","ActiveInfoMaxStep":"0","ActiveInfoTeamState":"1","ActiveInfoTimeLimit":"0","ActiveInfoIsRestartTimer":"0","ActiveInfoGiveBackMoney":"0","ActiveInfoGiveBackPetID":"0","ActiveInfoUseItemID":"0","ActiveInfoOtherType":"0","QuestionInfoNpcID":"0","TaskInfoDescriptionListA":"<T t=\"这些家伙看不见也不会说话，全靠本能攻击。杀了一个全都聚集过来了，真是麻烦啊……准备好，它们又来了。\" c=\"ff12c4ff\" ></T><T t=\"【战斗难度：单人简单难度，与任务等级接近的玩家可以单人轻松完成的战斗】\" c=\"ffe9f231\"></T>","TaskInfoPurposeListA":"<T t=\"与\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"击退梦魇邪兽（需战斗）。\"></T>","TaskInfoTraceListA":"<T t=\"与\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"击退梦魇邪兽\"></T><I s=\"MainControl\" i=\"zhan\"></I>","AIInfoAIID":"8027","AIInfoBattleResult":"1","AIInfoDeathPunish":"0","AIInfoTeamSteate":"1","AIInfoBattleLevel":"【战斗难度：单人简单】","BattleInfoBattleMapType":"1","BattleInfoBattleZoneID":"0","BattleInfoDrop":"0","BattleInfoBattleTimes":"0","BattleInfoMonsterNum":"0","BattleInfoDropItemID":"0","BattleInfoDropItemNum":"0","ScenarioInfoAnimationID":"0","ScenarioInfoBranchNpcID":"0"},"children":[{"node":"PostMissionList","attrs":{},"children":[{"node":"int","attrs":{},"text":"101005"}]},{"node":"DisPlayNPCID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10910"},{"node":"int","attrs":{},"text":"10911"},{"node":"int","attrs":{},"text":"10912"}]},{"node":"ScenarioInfoNpcConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"<T t=\"这些家伙看不见也不会说话，全靠本能攻击。杀了一个全都聚集过来了，真是麻烦啊……\"></T><T t=\"准备好，它们又来了\" c=\"ffffff33\"></T><T t=\"！\"></T>"},{"node":"string","attrs":{},"text":"先生你对这些怪物很熟悉……"},{"node":"string","attrs":{},"text":"<T t=\"其实，这些怪物\"></T><T t=\"都是你内心的梦魇\" c=\"ffffff33\"></T><T t=\"。你能看到他们，就\"></T><T t=\"说明你对于未来还有很多的恐惧\" c=\"ffffff33\"></T><T t=\"。不过别担心，只要你有击败它们的勇气，那它们以后就不会再来烦你了。\"></T>"}]},{"node":"ScenarioInfoNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10908"},{"node":"int","attrs":{},"text":"1"},{"node":"int","attrs":{},"text":"10908"}]},{"node":"ScenarioInfoFinishConversationList","attrs":{},"children":[{"node":"string","attrs":{},"text":"<T t=\"不错不错，你果然就是我要找的人了。\"></T><T t=\"黄药师就在陆家庄内\" c=\"ffffff33\"></T><T t=\"，你快去找他吧。\"></T><T t=\"不过里面似乎有其他人需要你的帮助呢\" c=\"ffffff33\"></T><T t=\"，行侠仗义的时间到了，$NAME$！\"></T>"}]},{"node":"ScenarioInfoFinishNpcID","attrs":{},"children":[{"node":"int","attrs":{},"text":"10908"}]}]}
```

# 首技能后的梦境战斗：原始来源与下一配方输入

2026-10-24；本地神雕侠侣1.6.1端游 / 网络版本601。仅新增本研究Markdown，不改Task、main的engine/storage/shared、政策或冻结副本；不运行战斗、GUI、真人DB、socket或服务。Battle聊天长期goal保持paused，本调查不唤醒它。

本批作为root后台代理沿用已完整读取的research/codebase-design，重新读取当前AGENTS、ARCHITECTURE、DESIGN_AUTHORITY、GLOSSARY。research实际用于原PFS成员头/目录、解压长度/CRC与BXML记录重读、已存native证据定位、两篇官方原页及三条定向查询；codebase-design实际用于把“原任务族”“正式战斗配方”“玩家技能状态”“原生表现”“旧终态恢复”分成已有权威的Interface，不因相同AI或名称跨越权限。未再委派其他聊天或重复长native模拟。

## 一、精确任务族与原边

本批直接读原 `autoconfig/knight.gsp.task.cmainmissioninfo.xml` 2460记录。对已裁定十个学习节点逐条读原PostMissionList及全表incoming；每个学习节点恰有一个AI8001前驱和一个type40/AI8027后继。以下是**供下一独立配方采用的精确候选族**，不是本文件开启战斗的权限；原43创建路线依据见[首技能研究](D:/神雕侠侣/revival/evidence/PROLOGUE_FIRST_SKILL_RESEARCH.md:60)。

| 唯一AI8001前驱 | 学习节点type10 | 唯一AI8027后继type40 | 后继的唯一CG节点type10 | CG节点的下一原任务 |
| ---: | ---: | ---: | ---: | ---: |
| 100107 | 100179 | 100190 | 100161 | 100110 |
| 100205 | 100279 | 100290 | 100261 | 100209 |
| 100305 | 100379 | 100390 | 100361 | 100309 |
| 100405 | 100479 | 100490 | 100461 | 100409 |
| 100505 | 100579 | 100590 | 100561 | 100509 |
| 100605 | 100679 | 100690 | 100661 | 100609 |
| 100705 | 100779 | 100790 | 100761 | 100709 |
| 100805 | 100879 | 100890 | 100861 | 100809 |
| 100905 | 100979 | 100990 | 100961 | 100909 |
| 103207 | 103279 | 103290 | 103261 | 103210 |

十学习节点的全部属性/子列表，除id及PostMissionList外完全相同；十AI8027后继亦如此。本批按实际记录比较，不以100x79/100x90的编号规律造边。原全部AI8027引用共11条，除上表十条外还有 **101004→101005**，同为type40/NPC10908/Map1501；所以“AI相同+NPC相同+地图相同”仍不足以授权。101003/101004及1010xx族保持原边，不插入本批学习节点，也不因旧族标签删除它；当前首场AI8001政策精确十任务仍见[已定政策](D:/神雕侠侣/revival/design/task-pve-ai8001-v1.json:16)。

十学习节点：原ExpReward120，MoneyReward/PetExpReward/ShengWang/SMoney0，ProcessBarTime1/掌握技能，NPC10908/Map1501；MissionType10、AI0、ScenarioAnimation0。其DisPlayNPCID=[10910,10911,10912]，没有显式SkillID/授予等级。授100008/value1、计时、免费及兼容基线都来自各自designed政策，不能由本表补证为原服事实。

十AI8027后继的关键原字段如下，完整属性和全部子列表在附录A，没有省略未理解字段：

| 原字段 | 十行共同原值 | 能说明什么 / 不能说明什么 |
| --- | --- | --- |
| MissionType / AIInfoAIID | 40 / 8027 | 原战斗任务身份；AI编号不含敌阵配方 |
| ActiveInfoNpcID / ActiveInfoMapID | 10908 / 1501 | 原NPC与地图模板；本人私有实例资格是现恢复设计，不能只凭模板授权 |
| ActiveInfoTargetID / TargetNum | 0 / 0 | 原字段为0，不能据此设计0个目标或自动获胜 |
| AIInfoBattleResult / DeathPunish / TeamSteate | 1 / 0 / 1 | 原字面；死亡复活、掉落和组队规则仍须独立采用 |
| BattleInfoBattleMapType / BattleZoneID | 1 / 0 | 原字段，不是已恢复的背景/站位/阵型选择 |
| MonsterNum / BattleTimes / Drop / DropItemID / DropItemNum | 全0 | 没有在此提供敌人数、模板、掉落或行动循环 |
| ExpReward / SMoney | 255 / 600 | 原奖励；币种映射按现货币政策，战斗producer不直接再发一份 |
| MoneyReward / PetExpReward / ShengWang | 全0 | 保留原零值，无RewardItem子列表 |
| ProcessBarTime | 0 | 该战斗任务不是前一学习读条 |
| RewardMapJumpType / MapID / XPos / YPos | 全0 | 本行没有完成即传送指令 |
| ScenarioInfoAnimationID / BranchNpcID | 0 / 0 | **100190本行不带10001或10019电影** |
| DisPlayNPCID | [10910,10911,10912] | 原场景列表，不等于战斗三个Fighter、生成指令或敌数 |
| 原Start / speaker列表 | 3句 / [10908,1,10908] | 保留原顺序与原speaker字段，不把中间1猜成静态NPC1 |
| 原Finish / speaker列表 | 1句 / [10908] | 成功后的原任务对白，不是客户端胜利证明 |

战后唯一CG节点（如100161）的原type10、NPC10084陆立鼎、Map1501、Animation10001、人物经验/SMoney0，这十行对应字段相同；与AI8027本行Animation0要分清。第一战AI8001的原10019又是另一字段/电影；[10019原生研究](D:/神雕侠侣/revival/evidence/PROLOGUE_FIRST_BATTLE_10019_NATIVE_RESEARCH.md:5)已说明Finish/DialogEnd到CG启动存在未闭合桥，不能把学习、第二战与后续CG混成一次假完成。

### 100190原Start/Finish中文全文

直接从原ScenarioInfoNpcConversationList按顺序提取T的文字，样式原文另保存在附录A的完整列表：

1. 这些家伙看不见也不会说话，全靠本能攻击。杀了一个全都聚集过来了，真是麻烦啊……准备好，它们又来了！
2. 先生你对这些怪物很熟悉……
3. 其实，这些怪物都是你内心的梦魇。你能看到他们，就说明你对于未来还有很多的恐惧。不过别担心，只要你有击败它们的勇气，那它们以后就不会再来烦你了。

Finish（ScenarioInfoFinishConversationList唯一项，原speaker10908）：

> 不错不错，你果然就是我要找的人了。黄药师就在陆家庄内，你快去找他吧。不过里面似乎有其他人需要你的帮助呢，行侠仗义的时间到了，$NAME$！

本段全文与十AI8027行原字段相同，保留$NAME$占位符，未替换成真人名字。

## 二、邪兽场景NPC与monster候选

本批原NPC表4127行、monster表5635行重读后得下列明确行。**场景实体名、相同模型或相邻monsterID均不能证明AI8027阵型**，也不能拿DisplayNPC列表长度当敌人数。

| NPC原id | name | modelID | npctype/bodytype | mapid | 原xPos,yPos | hide |
| ---: | --- | ---: | --- | ---: | --- | ---: |
| 10910 | 梦魇邪兽 | 6070 | 4/0 | 1501 | 53,108 | 1 |
| 10911 | 梦魇邪兽 | 6070 | 4/0 | 1501 | 53,97 | 1 |
| 10912 | 梦魇邪兽 | 6070 | 4/0 | 1501 | 67,108 | 1 |

三NPC还共同具有minimapquery/minimapshow“梦魇邪兽”、leaveservice“离开”、area1colour7/area2colour0、zaxueid-1、actionname0；pinyin=[mengyanxieshou]，chitchatidlist=[524,525,526]。这些是CNpcConfig原字段坐标，不替代当前地图真实摆放/位置权威；hide1也不应在本研究被解释成允许/禁止生成的布尔政策。

| monster原id | name | modelID | npctype/bodytype | becatch | showhpbar/showlevel | area1colour/area2colour |
| ---: | --- | ---: | --- | ---: | --- | --- |
| 29061 | 梦魇邪兽 | 6070 | 4/0 | 0 | 1/0 | 7/0 |
| 29062 | 梦魇邪兽 | 6070 | 4/0 | 0 | 1/0 | 7/0 |
| 29105 | 梦魇邪兽 | 6070 | 4/0 | 0 | 1/0 | 7/0 |
| 29113 | 梦魇邪兽 | 6070 | 4/0 | 0 | 1/0 | 7/0 |
| 29130 | 梦魇邪兽 | 6070 | 1/0 | 0 | 1/0 | 7/0 |

五monster行均没有level、HP/MP、攻击、防御、速度、技能、阵位或AI8027字段。29130的npctype1与其余4不同，不能只按同名随机挑。原modelID6070字段存在是client_verified，不表示本批验证了模型资源渲染或战斗画面。

另核battle.cbattleaiconfig2194行：没有id8001/8027，也未在本次该表属性/子项文本中检得8027。该表可见talkinfo/tipsinfo等表现记录，如50002提到太祖长拳，不能把表现提示表当服务端敌阵表；本结论仅限定这张表，不宣称全客户端不存在任何AI资料。

## 三、玩家技能100008完整原记录与namespace

以下cskillitem100008全部属性，原记录没有子列表；原skilldescribe去样式后的中文全文为：

> 虽然初入江湖，却也有着不俗的精气神。使用自身力量，攻击2个敌人。

原字段与原富文本如下：

| 原字段 | 原值 |
| --- | --- |
| id | 100008 |
| skillname | 太祖长拳 |
| sType | 多体伤害招式 |
| paramA | 0.0 |
| paramB | 0.0 |
| costA | 消耗：消耗真气随人物等级提升 |
| paramC | 0.0 |
| paramD | 0.0 |
| costTypeA | 70 |
| costTypeB | -1 |
| normalIcon | 327 |
| skilldescribe | `<T t="虽然初入江湖，却也有着不俗的精气神。使用自身力量，攻击2个敌人。" c="ffffff99"></T>` |
| targettype | 480 |
| bCanUseInBattle | 1 |
| effectid | 10011 |

同一skill.cskillitem表还有500001“太祖长拳”（paramB15）和500067“赵老爵爷-太祖长拳”（paramB1），它们也用effect10011/targettype480，但**不等于玩家100008**；不能借它们的paramB作为本技能耗蓝。

三种表/分类的数值不可混同：

| 来源 | 原100008定位 | 限制 |
| --- | --- | --- |
| cskillshowlist | id6“其他技能”列表含100008，列表共26个显示项 | 显示分组混有多种已学容器，不能据此发26项完整OtherSkills |
| cskillshowlistclient | id100008，skillname太祖长拳，skilltype1 | 原显示行身份；此skilltype不是下一行同名字段的已证同枚举 |
| cskilltypeconfig | id100008，skilltype4 | 原值client_verified；语义本批未闭合，不能叫“管理器class4” |
| 原技能管理器分类链 | 既有原1070ea0/12d55f0对100008走manager+0x40 | 与cskilltypeconfig的4和showlist的6分别举证，不能混用 |

本批源中cskillshowlist第6行完整skillnumber：
`100008,100007,100009,310202,350001,700001,700002,700003,360001,360002,360003,360004,360005,360006,360007,600018,700004,380001,380002,380003,380004,380005,380006,380007,380008,380009`。
当前已审r3 [role_skills.py](D:/神雕侠侣/revival/evidence/reviews/task-first-skill-20261024-r3/source/role_skills.py:18)仅将100007/100008/100009/310202/700004作为该原OtherSkills容器支持身份；缺历史账本不推空，后续合法等级和值必须保存，不能每次开战重授value1。

### 耗蓝/等级/公式候选核对

client_verified资源事实：100008文案说真气消耗随人物等级提升，costTypeA70/B-1，paramA/B/C/D全部0；文字说明“攻击2个敌人”，targettype原整数480（0x1e0）。本批没有闭合targettype480的位意义或param在正式技能耗蓝函数中的单位/公式，不能以0参数推免费，亦不能把480当目标数。

原cskillconsume仅15行，全部id为110201、130202、130602、140201、150302、170302、180101、190302、200272、200282、200292、200302、200312、200472、1110201；**无100008**，也没有100008子项引用。numberrand不能借其它技能项套用。cskillbase70行是含心法coefficient/依赖/skills的候选表，未见100008行或精确引用；cskillcost160行是ExpCost/MoneyCost随行id的数据（如id1=16/6），不是已证100008战斗MP表；cskilleffectextra60行也无本id/精确引用。未命中这些表只表明本次可用消费链未闭合，不等于服务器无公式。

effectid10011是本技能原效果资源引用；本次effect.ceffectconfig195行没有10011条目，未闭合它与某个效果执行器/脚本的完整关联。它不是玩家已学skillID，也不是下一段CSendAction要发送的替代operation_id。

## 四、已证原生消息与实际目标集合的边界

本批只读原source与已有报告，未重复运行native。地址均绑定原image SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

- [research_battle_commands.py:10](D:/神雕侠侣/revival/research_battle_commands.py:10)、[battle-command-native.json](D:/神雕侠侣/revival/evidence/battle-command-native.json)：原人物分支0x11962bf..0x11962e7写字段，原marshal0xe41550；CSendAction0xc1b5c为**三个BE i32操作类型/主目标/operation_id + isRole/isAuto两byte**，共14字节。已证普通攻击1、防御4、逃跑9来自原按钮/字段设置；不是猜按钮顺序。
- 既有[verify_battle_loadout.py:45](D:/神雕侠侣/revival/verify_battle_loadout.py:45)向该原sender注入(2,21,100008)，原SSendRoundScript解码读回DemoExecute的operatetype2、operationid100008和一次MP消耗；这些是明确训练fixture/原codec能力，**没有证明原技能菜单点击自动选择100008或正式耗蓝10**。操作ID沿选择的技能ID供应，不能换为effect10011。
- CSendAction只有一个主目标字段，**没有两个敌人的列表**。原文“攻击2个敌人”可以支持下一政策采用最多2目标，但另一个目标如何选、同一目标是否去重、死目标/宠物/阵营/手动与自动优先级，都没有由本包给出。
- [BATTLE_DESIGN_GAPS:26](D:/神雕侠侣/revival/evidence/BATTLE_DESIGN_GAPS.md:26)及[伤害表现修复](D:/神雕侠侣/revival/evidence/BATTLE_DAMAGE_PRESENTATION_FIX.md:5)闭合NewResultItem/DemoExecute与NewDemoResult目标结果：多目标可有独立结果，实际HP表现消费者读目标结果map的hpchange，不能仅塞DemoAttr列表。既有明确fixture向目标22/21供-11/-7分别被原consumer读取，证明结果集合可表达；这不是原AI或玩家选择器自主选出的集合。
- 原SSendOtherSkills0xc36c3为完整compact map<i32 skillID,i32 value>+尾byte，原消费者先删缺失旧key；[快照原生研究](D:/神雕侠侣/revival/evidence/OTHER_SKILL_SNAPSHOT_NATIVE_RESEARCH.md:7)给真实decoder/consumer证据。它与CSendAction战斗行动不同，不能用训练临时菜单注入替代真实已学状态。
- 原任务开战请求另是CActiveScenarioQuestAIBattle0xc4a4c、BE i32 taskID+BE u64 NPCkey、精确12字节；[task_battle_protocol.py](D:/神雕侠侣/revival/task_battle_protocol.py:1)及既有research_task_battle_admission原sender/codec已举证。它没有AI模板/敌数/获胜字段，不能客户端自报配方或结算。

## 五、本批官方端游核对

实际重新打开[2013-08-14万兽山庄官方攻略148481.shtml](https://sdxl.wanmei.com/news/gamenews/20130814/148481.shtml)：原第4步将初期学到的太祖长拳推荐为需要固定伤害时的选择。因此“早期习得、可作固定伤害用途”是guide_supported的定性线索；该后期副本没有给100008的伤害/MP/等级/目标公式，也没有证明本地1.6.1完全同版，不能据此搬副本怪物或直接宣称无视防御的定量实现已恢复。

实际重新打开[2012-07-28官方剧情任务页](https://sdxl.wanmei.com/info/renwu/script/20120728/133491.shtml)：支持0级序章、师父→车夫→嘉兴及说书人/血手印等NPC顺序，但不列梦魇邪兽敌阵与255/600精确任务ID。该页后部“净化梦魇”是25级支线，不能移植到当前序章；免费10级生活技能也是30级后另一剧情，不是此技能授予规则。

本批另外执行三条定向官方域搜索：`site:sdxl.wanmei.com "梦魇邪兽"`、`site:sdxl.wanmei.com "太祖长拳" "消耗"`、`site:sdxl.wanmei.com "序章" "梦魇"`。未取得能补AI8027敌阵、MP或伤害公式的新官方原页；只记录该有界结果，不声称所有历史资料都不存在。未用手游/神雕2、转载、25级支线或万兽山庄阵型填空。

## 六、下一正式recipe/技能模型的最小待设计集合

以下是unknown与inferred接入要求，不拟数值、不授权开关：

1. AI8027的精确十任务采用范围、敌模板/数量/阵位/等级/HP/MP/攻防速、可捕捉性、敌行动与目标规则、背景/音乐；原三个NPC与monster同名同模型不能替代这个决定。
2. 100008的正式MP公式（随人物等级/技能值哪一项）、伤害类型与公式、固定伤害线索如何采用、是否受防御/防御行动影响、取整/上下界/溢出；2目标上限、主目标与次目标选择、重复/死亡/敌我/自动操作条件；一次耗蓝与分目标结果如何原生表达。
3. 当前学会状态及其value/revision/完整来源怎样进入本场不可变参战快照；授予动作不等于战斗授权。下一战应消费已完成学习的真实状态/原唯一任务，而不是临时注入100008、把缺记录当已学或每战赋值1。
4. 新recipe的胜负/逃跑/平局/断线中止、资源扣损、角色raw HP0恢复、宠物死亡/忠诚/寿命、任务奖励与后续原对白/CG时序；**当前AI8001的专用梦境复活/单敌/普通攻击规则只覆盖其政策白名单**，不能无版本地自动扩到新AI。
5. 同角色独立BattleOwner及Task/Map/Connection/存储所有权，受控等待、已付款当前只读、完整最终编码、终态和资源CAS/outbox同事务，保留另一角色/地图/战斗独立推进；这不需全世界锁，也不能用一个“正式”标签替代真实producer。

### 跨recipe版本与旧outbox恢复的真实契约

这里读的是固定已交Task源码 `reviews/task-battle-terminal-recovery-20261024-r2/source/task_battle.py`（SHA见末表），不是把main正在编辑的storage/engine当成已发布。

- [84–104](D:/神雕侠侣/revival/evidence/reviews/task-battle-terminal-recovery-20261024-r2/source/task_battle.py:84)：每个TaskBattleResources对象仅有一个engine_revision及显式enabled_task_ids。原任务定义fingerprint来自全部原任务字典；相同AI不放行。
- [300](D:/神雕侠侣/revival/evidence/reviews/task-battle-terminal-recovery-20261024-r2/source/task_battle.py:300)：admission.plan持久绑定engine_revision、definition_fingerprint、Task/AI、原epoch、Participant与唯一battle/settlement身份；同battle_id不同intent拒绝。
- [372–400](D:/神雕侠侣/revival/evidence/reviews/task-battle-terminal-recovery-20261024-r2/source/task_battle.py:372)：终态验证要求plan.engine_revision==finished.revision、属性版本、原角色/epoch、Task原定义及AI完全匹配。不能把旧finished.revision或login_epoch改成当前值。
- [476–502](D:/神雕侠侣/revival/evidence/reviews/task-battle-terminal-recovery-20261024-r2/source/task_battle.py:476)：旧租约**pending终态恢复**还要求registry当前显式支持该任务，且registry.engine_revision==原admission.plan.engine_revision，并需要main核真实producer/source CAS后给RecoveryWitness。若把唯一registry直接替换成AI8027新版本，原AI8001 pending outbox会因版本不匹配而不能消费；不能通过删校验或假重建赢局“修复”。
- [456–474](D:/神雕侠侣/revival/evidence/reviews/task-battle-terminal-recovery-20261024-r2/source/task_battle.py:456)：已settled纯读取是另一条Interface，只要求原terminal/receipt与定义仍一致，**不要求这个registry的engine_revision等于原plan，也不重新核enabled集合**。因此不能误称新recipe必然阻断已付当前读取，亦不能为了读取旧凭据重新开放旧战斗准入。
- 由此可推的接入要求：新准入按精确任务/新approved recipe选能力；旧pending恢复按已存admission的原recipe身份/版本解析仍受支持的不可变旧规则与定义，保留跨epoch producer/source原件和唯一consumer标记。可以沿用engine_revision作不可变recipe版本或显式扩字段，方案由main/root选；不能只有一个被覆盖的全局“当前配方”，也不能由客户端指定版本。下一版本同样须验证原AI8001已有terminal/outbox可恢复且不重奖，新AI不能误读旧outbox。

这些是固定Task公开契约导出的inferred影响；本批未读取真人outbox、未运行迁移/恢复、未验证main当前实现或承诺已经部署。

## 附录A：二十原任务记录的完整重建数据

以下common_attributes/common_lists按十学习行、十后继行分别取**所有共同键值**；rows列出每行剩余字段。两者合并即本次原record的完整attributes及所有子列表，不丢0值、中文富文本或空缺的区别。不存在的列表不补[]。前驱/后继关系已在正文逐条列出。

```json
{
  "learning": {
    "common_attributes": {
      "MissionName": "[主线]序章缘起",
      "MissionTypeString": "主线剧情",
      "MinLevel": "0",
      "MaxLevel": "0",
      "TransMinLevel": "0",
      "TransMaxLevel": "0",
      "TransformID": "0",
      "ExpReward": "120",
      "MoneyReward": "0",
      "PetExpReward": "0",
      "ShengWang": "0",
      "SMoney": "0",
      "RewardMapJumpType": "0",
      "RewardMapID": "0",
      "RewardMapXPos": "0",
      "RewardMapYPos": "0",
      "ProcessBarTime": "1",
      "ProcessBarText": "掌握技能",
      "MissionType": "10",
      "ActiveInfoNpcID": "10908",
      "ActiveInfoMapID": "1501",
      "ActiveInfoLeftPos": "0",
      "ActiveInfoTopPos": "0",
      "ActiveInfoRightPos": "0",
      "ActiveInfoBottomPos": "0",
      "ActiveInfoTargetID": "0",
      "ActiveInfoTargetNum": "0",
      "ActiveInfoMiniStep": "0",
      "ActiveInfoStepProbability": "0",
      "ActiveInfoMaxStep": "0",
      "ActiveInfoTeamState": "1",
      "ActiveInfoTimeLimit": "0",
      "ActiveInfoIsRestartTimer": "0",
      "ActiveInfoGiveBackMoney": "0",
      "ActiveInfoGiveBackPetID": "0",
      "ActiveInfoUseItemID": "0",
      "ActiveInfoOtherType": "0",
      "QuestionInfoNpcID": "0",
      "TaskInfoDescriptionListA": "<T t=\"哎呀，你虽有慧根，打得却毫无章法，看来门派武功还尚未入门，实在不符合我的美学！这套太祖长拳就传授于你，你先参悟一下吧！\" c=\"ff12c4ff\" ></T>",
      "TaskInfoPurposeListA": "<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳。\"></T>",
      "TaskInfoTraceListA": "<T t=\"向\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"学习太祖长拳\"></T>",
      "AIInfoAIID": "0",
      "AIInfoBattleResult": "1",
      "AIInfoDeathPunish": "0",
      "AIInfoTeamSteate": "1",
      "BattleInfoBattleMapType": "1",
      "BattleInfoBattleZoneID": "0",
      "BattleInfoDrop": "0",
      "BattleInfoBattleTimes": "0",
      "BattleInfoMonsterNum": "0",
      "BattleInfoDropItemID": "0",
      "BattleInfoDropItemNum": "0",
      "ScenarioInfoAnimationID": "0",
      "ScenarioInfoBranchNpcID": "0"
    },
    "common_lists": {
      "DisPlayNPCID": [
        "10910",
        "10911",
        "10912"
      ]
    },
    "rows": [
      {
        "attributes": {
          "id": "100179"
        },
        "lists": {
          "PostMissionList": [
            "100190"
          ]
        }
      },
      {
        "attributes": {
          "id": "100279"
        },
        "lists": {
          "PostMissionList": [
            "100290"
          ]
        }
      },
      {
        "attributes": {
          "id": "100379"
        },
        "lists": {
          "PostMissionList": [
            "100390"
          ]
        }
      },
      {
        "attributes": {
          "id": "100479"
        },
        "lists": {
          "PostMissionList": [
            "100490"
          ]
        }
      },
      {
        "attributes": {
          "id": "100579"
        },
        "lists": {
          "PostMissionList": [
            "100590"
          ]
        }
      },
      {
        "attributes": {
          "id": "100679"
        },
        "lists": {
          "PostMissionList": [
            "100690"
          ]
        }
      },
      {
        "attributes": {
          "id": "100779"
        },
        "lists": {
          "PostMissionList": [
            "100790"
          ]
        }
      },
      {
        "attributes": {
          "id": "100879"
        },
        "lists": {
          "PostMissionList": [
            "100890"
          ]
        }
      },
      {
        "attributes": {
          "id": "100979"
        },
        "lists": {
          "PostMissionList": [
            "100990"
          ]
        }
      },
      {
        "attributes": {
          "id": "103279"
        },
        "lists": {
          "PostMissionList": [
            "103290"
          ]
        }
      }
    ]
  },
  "next_battle": {
    "common_attributes": {
      "MissionName": "[主线]序章缘起",
      "MissionTypeString": "主线剧情",
      "MinLevel": "0",
      "MaxLevel": "0",
      "TransMinLevel": "0",
      "TransMaxLevel": "0",
      "TransformID": "0",
      "ExpReward": "255",
      "MoneyReward": "0",
      "PetExpReward": "0",
      "ShengWang": "0",
      "SMoney": "600",
      "RewardMapJumpType": "0",
      "RewardMapID": "0",
      "RewardMapXPos": "0",
      "RewardMapYPos": "0",
      "ProcessBarTime": "0",
      "MissionType": "40",
      "ActiveInfoNpcID": "10908",
      "ActiveInfoMapID": "1501",
      "ActiveInfoLeftPos": "0",
      "ActiveInfoTopPos": "0",
      "ActiveInfoRightPos": "0",
      "ActiveInfoBottomPos": "0",
      "ActiveInfoTargetID": "0",
      "ActiveInfoTargetNum": "0",
      "ActiveInfoMiniStep": "0",
      "ActiveInfoStepProbability": "0",
      "ActiveInfoMaxStep": "0",
      "ActiveInfoTeamState": "1",
      "ActiveInfoTimeLimit": "0",
      "ActiveInfoIsRestartTimer": "0",
      "ActiveInfoGiveBackMoney": "0",
      "ActiveInfoGiveBackPetID": "0",
      "ActiveInfoUseItemID": "0",
      "ActiveInfoOtherType": "0",
      "QuestionInfoNpcID": "0",
      "TaskInfoDescriptionListA": "<T t=\"这些家伙看不见也不会说话，全靠本能攻击。杀了一个全都聚集过来了，真是麻烦啊……准备好，它们又来了。\" c=\"ff12c4ff\" ></T><T t=\"【战斗难度：单人简单难度，与任务等级接近的玩家可以单人轻松完成的战斗】\" c=\"ffe9f231\"></T>",
      "TaskInfoPurposeListA": "<T t=\"与\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"击退梦魇邪兽（需战斗）。\"></T>",
      "TaskInfoTraceListA": "<T t=\"与\"></T><G t=\"说书人\" npcid=\"10908\"></G><T t=\"击退梦魇邪兽\"></T><I s=\"MainControl\" i=\"zhan\"></I>",
      "AIInfoAIID": "8027",
      "AIInfoBattleResult": "1",
      "AIInfoDeathPunish": "0",
      "AIInfoTeamSteate": "1",
      "AIInfoBattleLevel": "【战斗难度：单人简单】",
      "BattleInfoBattleMapType": "1",
      "BattleInfoBattleZoneID": "0",
      "BattleInfoDrop": "0",
      "BattleInfoBattleTimes": "0",
      "BattleInfoMonsterNum": "0",
      "BattleInfoDropItemID": "0",
      "BattleInfoDropItemNum": "0",
      "ScenarioInfoAnimationID": "0",
      "ScenarioInfoBranchNpcID": "0"
    },
    "common_lists": {
      "DisPlayNPCID": [
        "10910",
        "10911",
        "10912"
      ],
      "ScenarioInfoNpcConversationList": [
        "<T t=\"这些家伙看不见也不会说话，全靠本能攻击。杀了一个全都聚集过来了，真是麻烦啊……\"></T><T t=\"准备好，它们又来了\" c=\"ffffff33\"></T><T t=\"！\"></T>",
        "先生你对这些怪物很熟悉……",
        "<T t=\"其实，这些怪物\"></T><T t=\"都是你内心的梦魇\" c=\"ffffff33\"></T><T t=\"。你能看到他们，就\"></T><T t=\"说明你对于未来还有很多的恐惧\" c=\"ffffff33\"></T><T t=\"。不过别担心，只要你有击败它们的勇气，那它们以后就不会再来烦你了。\"></T>"
      ],
      "ScenarioInfoNpcID": [
        "10908",
        "1",
        "10908"
      ],
      "ScenarioInfoFinishConversationList": [
        "<T t=\"不错不错，你果然就是我要找的人了。\"></T><T t=\"黄药师就在陆家庄内\" c=\"ffffff33\"></T><T t=\"，你快去找他吧。\"></T><T t=\"不过里面似乎有其他人需要你的帮助呢\" c=\"ffffff33\"></T><T t=\"，行侠仗义的时间到了，$NAME$！\"></T>"
      ],
      "ScenarioInfoFinishNpcID": [
        "10908"
      ]
    },
    "rows": [
      {
        "attributes": {
          "id": "100190"
        },
        "lists": {
          "PostMissionList": [
            "100161"
          ]
        }
      },
      {
        "attributes": {
          "id": "100290"
        },
        "lists": {
          "PostMissionList": [
            "100261"
          ]
        }
      },
      {
        "attributes": {
          "id": "100390"
        },
        "lists": {
          "PostMissionList": [
            "100361"
          ]
        }
      },
      {
        "attributes": {
          "id": "100490"
        },
        "lists": {
          "PostMissionList": [
            "100461"
          ]
        }
      },
      {
        "attributes": {
          "id": "100590"
        },
        "lists": {
          "PostMissionList": [
            "100561"
          ]
        }
      },
      {
        "attributes": {
          "id": "100690"
        },
        "lists": {
          "PostMissionList": [
            "100661"
          ]
        }
      },
      {
        "attributes": {
          "id": "100790"
        },
        "lists": {
          "PostMissionList": [
            "100761"
          ]
        }
      },
      {
        "attributes": {
          "id": "100890"
        },
        "lists": {
          "PostMissionList": [
            "100861"
          ]
        }
      },
      {
        "attributes": {
          "id": "100990"
        },
        "lists": {
          "PostMissionList": [
            "100961"
          ]
        }
      },
      {
        "attributes": {
          "id": "103290"
        },
        "lists": {
          "PostMissionList": [
            "103261"
          ]
        }
      }
    ]
  }
}
```

## 附录B：原PFS成员与本批输入SHA

以下成员均在 `D:/神雕侠侣/artres/config.pfs`，完整名为 `autoconfig/knight.gsp.`+下表名+`.xml`。PfsArchive.read实际核目录/本地头、解压完整性、原长度/CRC；BXML完整消费。BXML记录没有可声称的文本行号，以表名及record id精确定位。

| 原成员 | 记录数 | 展开字节 | CRC32 | 展开字节SHA256 |
| --- | ---: | ---: | --- | --- |
| task.cmainmissioninfo | 2460 | 2026233 | 3f7ab7b3 | `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706` |
| npc.cnpcconfig | 4127 | 619832 | cc437e13 | `b4fc5d440380fb535a36b8e5315c5a1bf10a99f550f5bfde55bd156fca864f85` |
| npc.cmonsterconfig | 5635 | 360729 | 95939be9 | `b4843cab3b217a94c2f6fefc00b68cd28bed4c4dc125d9271812769d59dd7c39` |
| skill.cskillitem | 652 | 107547 | b5d9fdd8 | `2a8645ae11267eb3cbbeeab0f56f4be8f8fe9b4fa95f6c4026448f59afc07194` |
| skill.cskillconsume | 15 | 2229 | 1ac3874e | `ece2760d4f01b4b100f4f8105c382a41641bcb1296b06de902171d30ca65fa3a` |
| skill.cskillshowlist | 6 | 4644 | 118178bc | `67632b0dc85a979637846c3d1717bac6f75b48d93a9661a381ea92f95931c5ac` |
| skill.cskillshowlistclient | 239 | 11110 | 112a2193 | `eda1374328a6a2574cc53b6eee53f1e81b144f5d9da44965c89a647940d8d6eb` |
| skill.cskillbase | 70 | 12938 | 26013e23 | `06b7342f3becec4e8c4227168536aecf9a83caa3c3cd82b17fbd07b2b6017b2a` |
| skill.cskillcost | 160 | 8857 | c56c975e | `a7a8321616a3f0cc0e8349e7d311e6a7bf89d771d757136cbbe29ea3bd65ee8f` |
| skill.cskilleffectextra | 60 | 1607 | d989ce1c | `03abef3e8d50b898f8be736848d290262ad5ebc742c6d60b94d60a0da856513e` |
| skill.cskilltypeconfig | 1308 | 42614 | 388ccdb8 | `ea99ab5cf95d1d9e571bb2841cbd7c99457e46a26891cc5cf2dafc63fed3699e` |
| effect.ceffectconfig | 195 | 7990 | 52d4cb99 | `af8a63e7b49e24e43a414db3234a156fba621369ee9c213e095d8cb91eee97de` |
| battle.cbattleaiconfig | 2194 | 179370 | 5df0f95e | `01e56fcca6af219dc36617d323710e6d379c299e74c57b82f75aeaa449f9dea3` |

本批引用的本地输入固定在下列SHA。正文以原PFS为事实来源，现政策及固定Task接口仅解释现有设计/接入约束；工作区后续更新不应替换这些值冒充同一审计。

| 输入 | SHA256 |
| --- | --- |
| AGENTS.md | `8c47404ca7b4d8cc4eef07afb4ca242b9d6a006f2b20db00817e4bbb562d4630` |
| GLOSSARY.md | `cc1fe0dc7ec653b87935881e5b958aead7d1367270745712e5ff28c29c86db80` |
| revival/ARCHITECTURE.md | `0b98c5d027f33cf99071c2a316b77dbcd6a2a785b6658987209321bbadfc1d7d` |
| revival/DESIGN_AUTHORITY.md | `820829778bcd632f2963eebc5f3106600c873481212fa8542cdd144a2e0ecf5f` |
| revival/pfs.py | `d4c9a5f6080276ab51886fdd4f1d7e7c1618715f870cbce84c916cf03b163352` |
| revival/bxml.py | `ba61810a10fede4305075efd7120429fb165af90fdbb4fb94697862a30c8b66d` |
| revival/design/newbie-first-skill-v1.json | `4429b4312903ae6cbcd2cbb646152b637aa03841d4fe21926abd30e7f0c18988` |
| revival/design/task-pve-ai8001-v1.json | `2cbbe2cafe3151e49f21a4ec35dab0dd9d4aa9dca82b4b28016dfcb3c13a3c56` |
| revival/evidence/PROLOGUE_FIRST_SKILL_RESEARCH.md | `309ae17df1b8ca85cc23c04049425b240a1a87c5b0434eabc6406594ef2b418e` |
| revival/evidence/PROLOGUE_FIRST_SKILL_GUIDE_RESEARCH.md | `c8795063e3887f2363b7621f6a5304b32922f4e72f24000915f3412488776e91` |
| revival/evidence/OTHER_SKILL_SNAPSHOT_NATIVE_RESEARCH.md | `2d5178473a34297ea89a2cb13d0b6b5e9b9c934f20974e79c0494cd2854c9e5d` |
| revival/evidence/PROLOGUE_FIRST_BATTLE_10019_NATIVE_RESEARCH.md | `4e8c5b02ce6141efceb8280e8135ed2bc29d10f49c20da82dacd15f8300c44c1` |
| revival/evidence/TASK_BATTLE_TERMINAL_RECOVERY_INTEGRATION.md | `185caacd5206492bea18c4e70ede486e106837af5de627d3ef65572810a350b2` |
| revival/evidence/BATTLE_DESIGN_GAPS.md | `6251872a04d344a5c4c546ae48cc8a9b1615a930dc0b882512a9e7de984b695c` |
| revival/evidence/BATTLE_LOADOUT_HANDOFF.md | `a931f47b436d425f233f1c303b431d826625d8654ffb139b0b10b15ba4708e6e` |
| revival/evidence/BATTLE_DAMAGE_PRESENTATION_FIX.md | `6b3fa1beb4a318a9ad813f4ad37041c3d1ba097abb36ca24e58be68fc1230581` |
| revival/research_battle_commands.py | `ced33492c33b33c43763a2eb9a7f8da3f47b7ba0e427272cd5d97103b5b582c7` |
| revival/research_task_battle_admission.py | `a6223f9321c69f7f3b703a1173c0fe5cc38fff223e04d2b052ec7ac0f3c5697a` |
| revival/battle_protocol.py | `1a472edf4f1a9db20d8c08ba05eb5516b56b723b87b2b2c80ca0c0a60c75cd22` |
| revival/task_battle_protocol.py | `8223d4a609a464faf1fd05f24d45defe2081da3d152fb9839a8e85d38fb366ba` |
| revival/evidence/battle-command-native.json | `c6bedd510a4b4ab091249f82c7c399f38174fce19a69c53dd21502c3eb022dfc` |
| revival/evidence/reviews/task-battle-terminal-recovery-20261024-r2/source/task_battle.py | `8a78b9da2ce1cd144035c0b176c5485ef561d75afaa0ddf1bb033bdb6740d3f8` |
| revival/evidence/reviews/task-first-skill-20261024-r3/source/role_skills.py | `7985e132239bffcda1c19fce63b3af724d3b48e1e92395f590a530b7e6038daf` |

结束前再次解码十三原PFS成员并重算SHA，与首次全部一致；从本Markdown的JSON附录反向合并二十条完整record，逐项与原attributes/所有子列表比较，20/20一致。上列23项本地输入采集后及交付前两次SHA也全部一致。

验证范围：十三原PFS表重读、二十节点完整字段相等性/每条边/全表AI8027十一条扫描、后续十CG字段、NPC三行/monster五行/100008全字段及相关表精确引用、两官方原页和三定向搜索。本批没有新跑native sender/consumer，相关结论明确沿用固定旧研究；没有真实开战/技能使用、客户端画面、任何DB/socket、策略实现、持久化/恢复或发布验证。产物只此Markdown；未知交root设计，main的当前第一战/恢复/cohort工作不等待本调查。


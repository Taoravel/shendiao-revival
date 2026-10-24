# 首技之后第二战AI8027：43路线与敌阵证据边界

2026-10-24。本批使用research原始来源方法，后台代理直接重读原PFS；ARCHITECTURE/DESIGN_AUTHORITY及research完整内容沿用当前批上下文。只新增本文及独立source audit脚本；不改正在发布的P0、Task/engine/shared/政策或原资源，不操作真人DB、GUI、服务或战斗。未扩展轻功、10019或远端任务。

## 结论

`client_verified`：43个原建角角色/门派组合，经真实PostMissionList各自到达十个首技教学节点，之后唯一第二战为type40/AI8027，再唯一进入type10/Animation10001节点。第二战本行Animation是0；**不能跳过CG10001节点，也不能把第一战10019当它的替代。**

`client_verified`：教学与第二战均DisplayNPC10910/10911/10912；这些场景NPC名为梦魇邪兽、模型6070。原monster同名候选五条，model6070全表却有25条；没有取得AI8027→monster/阵位/人数/属性的原映射。原DisPlayNPC三项不证明三敌；BattleInfoMonsterNum0也不证明零敌或可自动获胜。

第二战需要根主策独立配方设计/批准。AI8001现有“单敌29104、HP40等”是首战designed参数，不是AI8027的原证；第二战不能只扩AI白名单、沿用第一战敌阵或把新学技能100008直接变成已实现的战斗能力。

## 一手来源与复现

直接由 `artres/config.pfs` 按原成员头/长度/CRC读取并BXML解码；下表SHA为解包后的原字节。脚本：[inspect_prologue_second_battle_sources.py](../staging/inspect_prologue_second_battle_sources.py)，SHA256 `6660161d4120427bcee7ab97232f8ee0f399555fe9fca4a654f7525881b5555a`；只输出stdout，不写派生catalog或DB。

| 原成员 autoconfig/knight.gsp.… | 行数 / bytes / CRC32 | SHA256 |
|---|---|---|
| role.createroleconfig.xml | 10 / 13107 / 0758d770 | `770da32d88784144e453c386c9cce05de03746943eb6004158d3cc53c9428132` |
| role.schoolinfo.xml | 10 / 4075 / fe9fe433 | `3ed66a6f40f615b6d89372a1775246a33c644b9d612df7794532edb656332a2d` |
| task.cmainmissioninfo.xml | 2460 / 2026233 / 3f7ab7b3 | `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706` |
| npc.cnpcconfig.xml | 4127 / 619832 / cc437e13 | `b4fc5d440380fb535a36b8e5315c5a1bf10a99f550f5bfde55bd156fca864f85` |
| npc.cmonsterconfig.xml | 5635 / 360729 / 95939be9 | `b4843cab3b217a94c2f6fefc00b68cd28bed4c4dc125d9271812769d59dd7c39` |
| battle.cbattleaiconfig.xml | 2194 / 179370 / 5df0f95e | `01e56fcca6af219dc36617d323710e6d379c299e74c57b82f75aeaa449f9dea3` |
| gm.cbattlelist.xml | 1872 / 46722 / 0fc5fef9 | `4cfa4713d6e773081c159b1406f9ce5d694ec5fd6bbfe91a45955818025eb118` |
| movie/10001.txt（不在autoconfig目录） | 9004 bytes / 424d12bc | `c539ab40e437da8d2a8bd5efc5dd914a54a1b719427bb7c2b991a657df207c67` |

脚本从原createroleconfig的schools得到43合法组合；按原type50根的角色专属首边RequestRoleIDList、学校home map选择十根，再沿原唯一Post追到AI8027。对每组合核匹配角色/门派、教学前驱AI8001、第二战唯一incoming为教学、唯一后继CG10001及其下一原边。**未以缓存newbie-routes.json作最终依据，也未用任务或电影ID加减推根/边。**

## 十族精确边与43组合

| school / 原root | 原角色配置ID | AI8001前驱 | 教学type10 | 第二战type40/AI8027 | 唯一CG10001/type10 | CG的下一原任务 |
|---|---|---:|---:|---:|---:|---:|
| 11 / 100101 | 2,5,9,10 | 100107 | 100179 | 100190 | 100161 | 100110 |
| 12 / 100201 | 1,3,4,6,7 | 100205 | 100279 | 100290 | 100261 | 100209 |
| 13 / 100301 | 1,3,5,6,7 | 100305 | 100379 | 100390 | 100361 | 100309 |
| 14 / 100401 | 3,4,7,8 | 100405 | 100479 | 100490 | 100461 | 100409 |
| 15 / 100501 | 2,4,8,9 | 100505 | 100579 | 100590 | 100561 | 100509 |
| 16 / 100601 | 1,5,6,10 | 100605 | 100679 | 100690 | 100661 | 100609 |
| 17 / 100701 | 2,5,6,10 | 100705 | 100779 | 100790 | 100761 | 100709 |
| 18 / 100801 | 1,4,8,9 | 100805 | 100879 | 100890 | 100861 | 100809 |
| 19 / 100901 | 2,3,7,8 | 100905 | 100979 | 100990 | 100961 | 100909 |
| 111 / 103201 | 1,4,5,9,10 | 103207 | 103279 | 103290 | 103261 | 103210 |

原表AI8027共11条，额外旧族是 `101003→101004→101005`；不属于这43路线。相同AI/NPC/map不能把它自动纳入新族授权。脚本逐行比较十个第二战全部属性及lists，除id与PostMissionList外完全相同；全表incoming也分别只有表列教学节点。

## 第二战原行共同事实

| 字段 | 十行实际原值 | 限制 |
|---|---|---|
| MissionType / AIInfoAIID | 40 / 8027 | 正式任务身份，不是敌阵表 |
| ActiveInfoNpcID / ActiveInfoMapID | 10908 / 1501 | 说书人/梦境嘉兴模板，不证明私有实例或当前NPCkey |
| AIInfoBattleResult / DeathPunish / TeamSteate | 1 / 0 / 1 | 原字面，不自行补死亡复活/组队玩法 |
| BattleInfoBattleMapType / BattleZoneID | 1 / 0 | 不等于已知背景、阵位、阵型 |
| BattleInfoMonsterNum / Times / Drop / DropItemID / DropItemNum | 全0 | 不提供实际敌人数/模板/行动或掉落配方 |
| ActiveInfoTargetID / TargetNum | 0 / 0 | 不提供敌阵，不自动完成 |
| ProcessBarTime / Animation / BranchNpcID | 0 / 0 / 0 | 不是首技读条；本行没有10001电影 |
| RewardMapJumpType / Map / X / Y | 全0 | 本行没有完成传送 |
| ExpReward / SMoney | 255 / 600 | 任务原奖励，仅由任务事务结一份 |
| MoneyReward / PetExpReward / ShengWang | 全0 | 保留零；无RewardItem列表 |
| DisPlayNPCID | 10910,10911,10912 | 场景显示数据，不是Fighter列表 |
| Start / speaker | 3句 / 10908,1,10908 | 中间1是原speaker标识，不当静态交互NPC1 |
| Finish / speaker | 1句 / 10908 | 对白不是胜利报告或奖励凭据 |

Start叙述这些梦魇邪兽全靠本能攻击、杀一只全聚来，并说它们来自角色内心恐惧；Finish让角色到陆家庄找黄药师、帮助他人。教学前驱本行原ProcessBarTime1/掌握技能、120人物XP、其他奖励0、DisPlay相同三NPC；其授100008/value1与计时防重依现有独立designed政策，原行无grant ID/等级字段。

## 场景NPC与monster候选

| CNpcConfig原ID / name | modelID / npctype / bodytype | 原map / xPos / yPos / hide |
|---|---|---|
| 10908 说书人 | 6080 / 4 / 0 | 1501 / 65 / 97 / 1 |
| 10910 梦魇邪兽 | 6070 / 4 / 0 | 1501 / 53 / 108 / 1 |
| 10911 梦魇邪兽 | 6070 / 4 / 0 | 1501 / 53 / 97 / 1 |
| 10912 梦魇邪兽 | 6070 / 4 / 0 | 1501 / 67 / 108 / 1 |
| 10084 陆立鼎（CG节点交互NPC） | 6097 / 4 / 0 | 1501 / 137 / 50 / 1 |

坐标为原字段，不在本报告转服务器像素或当前权威placement；hide1也不作为生成授权。三梦魇邪兽还有area1colour7/area2colour0、chitchatidlist524/525/526，仍属于场景表现。

| CMonsterConfig同名候选 | modelID | npctype / bodytype | becatch / showhpbar / showlevel |
|---|---:|---|---|
| 29061、29062、29105、29113 | 6070 | 4 / 0 | 0 / 1 / 0 |
| 29130 | 6070 | 1 / 0 | 0 / 1 / 0 |

这五行没有子列表，其完整属性仅id/name/modelID/becatch/showhpbar/showlevel/npctype/bodytype/area1colour/area2colour；**没有level、HP/MP、攻防速、技能、阵位、AI8027或引用三NPC的字段**。同模型6070在monster全表有25行，不能仅模型相等绑定。29105紧邻首战候选29104、29113紧邻29112，也不是AI连续性/配方证据。

battle.cbattleaiconfig的2194行属性/子项中没有8027；该表的客户端AI表现提示不能当服务端roster。另查gm.cbattlelist确有id8027，但该行仅 `{id:8027}`，无其他属性或子列表；它是编号存在证据，不能提供开战配方。上述是本批七表的证据边界，不宣称穷尽全客户端所有潜在资料。

## CG10001与尚需根设计的参数

第二战唯一后继十节点均type10、NPC10084、Map1501、Animation10001、Start/Finish空、Process0、五奖励0；CG节点后才是表列下一任务。movie10001原资源存在。其pending/显式播放/CEnd未闭合的原服桥沿用 [PROLOGUE_STORY_EFFECT_RESEARCH.md](./PROLOGUE_STORY_EFFECT_RESEARCH.md) 和 [PROLOGUE_DREAM_RETURN_RESEARCH.md](./PROLOGUE_DREAM_RETURN_RESEARCH.md)，本批不重做native研究、不把state1叫自动CG成功、不授权跳过节点。

根配方需要明确标designed并冻结：实际monster选择、敌人数/阵位/等级/完整HP/MP/攻防速及行为、技能100008允许与否和已批准执行能力、目标选择/耗蓝/伤害规则、背景/音乐、失败/逃跑/断线/死亡恢复及宠物处理、版本快照、唯一终态与任务结算、CG10001授权和重登恢复接线。若选择三敌，这是设计，不是DisPlay长度实证；若复用8001底层回合Module，仍需AI8027独立配方与能力门控，不能继承单敌或首战奖励。

第二战前须保留本路线真实教学结算与当前完整技能快照的权限；后续BattleOwner产生真实终态，角色/任务Owner同事务结255XP/SMoney600与原唯一后继，不能由客户端结束/CG确认生成胜利或重复任务奖。这里只列待设计/接入事项，不批准数值或扩大战斗能力。

## 本批验证与未验证

独立audit最终通过：七原表+movie长度/CRC/SHA，43原组合与十根、43真实路径、十教学→AI8027→CG10001→下一原边，全表incoming/旧101004排除，十第二战完整字段一致，五同名monster与25同模型区分，GM仅id/客户端AI表无8027。没有native执行或运行时测试；没有敌阵/公式、真实100008战斗能力、CG播放、人物/宠物资产结算、部署或GUI验收。产物仅本文与source audit，当前发布P0保持独立。

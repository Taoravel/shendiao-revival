# “触摸血手印”全族与43条自然路线批审

2026-10-23；本地端游1.6.1、网络601。沿用本轮完整research/codebase-design技能、ARCHITECTURE/DESIGN_AUTHORITY。仅新增本文；不改源码/政策/配置，不开真实库、GUI、服务或战斗。原请求/时间/Note消费者细节沿 [JIAXING_MAINLINE_NEXT_AUDIT.md](JIAXING_MAINLINE_NEXT_AUDIT.md) 与 [TASK_NPC_PROGRESS_RESEARCH.md](TASK_NPC_PROGRESS_RESEARCH.md)，本页只补同族全量和差异。

## 结果与推荐政策范围

原任务表精确筛 `ProcessBarText="触摸血手印"` 得到 **11条**。其中 **10条覆盖现43条newbie角色×门派路线**，对应十门派分支，不能说“十人物每人固定一个任务”。另101002同样具有该文本/机制，但不在现43路线的实际原边路径内，须单独保留，不自动授予。[S1、S2、S3]

可以共用一份政策的10条候选精确集合：

`100106,100206,100306,100406,100506,100606,100706,100806,100906,103206`。

它们共同拥有原type10、时量3、源NPC10498/1006、Jump3→1501原坐标63/79、全部奖励0、无原开始/完成对白、相同Note，且唯一后继均为NPC10908/1501的type40、AI8001。**共同数据足以采用一个受显式ID/原字段/路线约束的Interface，不支持把所有type10读条或所有Jump3自动纳入。** 坐标×16仍inferred，服务端至少3000ms及每角色私有梦境仍待root设计；不在本报告发布政策或启用后继战斗。

## 来源与校验方法

直接 `PfsArchive.read` 校验目录/本地头、解压长度与CRC，再BXML解码；没有重跑会覆盖目录的恢复程序。原11条属性/所有lists与当前 `catalogs/tasks.json` 全等。用该目录建立纯不可变 `TaskResources` 对象（未调用prepare_task_store、无DDL/DB），验证消费者接收的字段同源。

| 来源 | 原包成员/文件 | 字节 / CRC32 |
|---|---|---|
| S1 | config.pfs/autoconfig/knight.gsp.task.cmainmissioninfo.xml，2460行 | 2026233 / 3f7ab7b3 |
| S2 | config.pfs/autoconfig/knight.gsp.role.createroleconfig.xml，10行 | 13107 / 0758d770 |
| S3 | config.pfs/autoconfig/knight.gsp.role.schoolinfo.xml | 4075 / fe9fe433 |
| S4 | config.pfs/autoconfig/knight.gsp.npc.cnpcconfig.xml | 619832 / cc437e13 |
| S5 | config.pfs/autoconfig/knight.gsp.map.cmapconfig.xml | 91110 / 3325016f |
| S6 | map.pfs/map_1006_jiaxing/npc.xml | 3571 / 51217023 |
| S7 | map.pfs/fubenjiaxing/npc.xml | 888 / 06370594 |
| S8 | map.pfs/fubenjiaxing/maze.dat | 113676 / cda771b4 |
| S9 | 当前catalogs/newbie-routes.json，43条 | SHA256 0e04f85f83fd539c2a4072de1d3ea1fc2dc1d481e04dee918a3fc38a1249da62 |

S1 SHA256 `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706`；S2 `770da32d88784144e453c386c9cce05de03746943eb6004158d3cc53c9428132`；S3 `3ed66a6f40f615b6d89372a1775246a33c644b9d612df7794532edb656332a2d`；S8 `6f81a7407738d6ce9b7ca167c82c28849dea1db12e7f2aa7fe1285e747698351`。S4–S7详细SHA与现有报告一致，本轮均直接read重新核CRC。

角色关联步骤：逐条S9取**显式successor_task_id**，先核该ID确在原intro.PostMissionList、原first.RequestRoleIDList包含该route.role_id、原CreateRoleConfig.schools包含route.school_id；再沿每个原唯一PostMissionList直到首个血手印节点，检测环/多边而不猜ID算式。43条全部通过该交叉核验并各命中一次。全表逆向建incoming以确认唯一前驱；本页前驱不是只在某条路线局部找出的结果。

## 十门派自然分支与一条未关联节点

行号是 `decoded/config/autoconfig/knight.gsp.task.cmainmissioninfo.xml` 的record首行；身份以原S1 ID为准。表中每一条的 `ProcessBarTime=3、ProcessBarText=触摸血手印、type10、ActiveNpc10498/Map1006、Jump3/Map1501/X63/Y79、五项奖励全0`，共用字段在下节完整说明。

| 血手印ID / 行 | 全表唯一前驱 | 唯一后继 | 实际school / 门派 | 43路线中的角色配置ID | ProcessBarColor原字段 | 原DisPlayNPCID |
|---|---|---|---|---|---|---|
| 100106 / 42 | 100160 | 100107 | 11 古墓派 | 2,5,9,10（4条） | ffffff33 | [10083] |
| 100206 / 709 | 100260 | 100205 | 12 丐帮 | 1,3,4,6,7（5条） | **缺字段** | [10491] |
| 100306 / 1365 | 100360 | 100305 | 13 西域密宗 | 1,3,5,6,7（5条） | 缺字段 | [10491] |
| 100406 / 2020 | 100460 | 100405 | 14 白驼山庄 | 3,4,7,8（4条） | 缺字段 | [10083] |
| 100506 / 2657 | 100560 | 100505 | 15 大理段氏 | 2,4,8,9（4条） | 缺字段 | [10491] |
| 100606 / 3294 | 100660 | 100605 | 16 全真教 | 1,5,6,10（4条） | 缺字段 | [10083] |
| 100706 / 3937 | 100760 | 100705 | 17 桃花岛 | 2,5,6,10（4条） | 缺字段 | [10491] |
| 100806 / 4571 | 100860 | 100805 | 18 绝情谷 | 1,4,8,9（4条） | 缺字段 | [10083] |
| 100906 / 5205 | 100960 | 100905 | 19 百花谷 | 2,3,7,8（4条） | 缺字段 | [10083] |
| 103206 / 16113 | 103260 | 103207 | 111 少林 | 1,4,5,9,10（5条） | ffffff33 | [10083] |
| **101002 / 5806** | **101001** | **101003** | **未在43路线命中** | **无** | 缺字段 | [10083] |

S2角色ID名：1楚天河、2秦少游、3燕重光、4司马长风、5杨空岳、6唐七七、7独孤月、8铃小雨、9云夕、10韩忆。相同人物可选不同门派，所以不能由人物ID直接推某个100x06任务；可信已建章路线中的school与角色资格必须一起保留。

### 实际原边路径，避免ID减法映射

下表首师父分支按上表角色ID顺序一一对应；后面每列都是逐任务读取PostMissionList得到，未以数字规律生成。

| school | 原intro | 首师父原分支（对应上表角色顺序） | 装备门槛→车夫→60001标题→说书人→血手印 |
|---|---|---|---|
| 11 | 100101 | 100184,100185,100186,100187 | 100188→100104→100105→100160→100106 |
| 12 | 100201 | 100283,100284,100285,100286,100287 | 100288→100203→100204→100260→100206 |
| 13 | 100301 | 100383,100384,100385,100386,100387 | 100388→100303→100304→100360→100306 |
| 14 | 100401 | 100484,100485,100486,100487 | 100488→100403→100404→100460→100406 |
| 15 | 100501 | 100584,100585,100586,100587 | 100588→100503→100504→100560→100506 |
| 16 | 100601 | 100683,100685,100686,100687 | 100688→100603→100604→100660→100606 |
| 17 | 100701 | 100784,100785,100786,100787 | 100788→100703→100704→100760→100706 |
| 18 | 100801 | 100883,100885,100886,100887 | 100888→100803→100804→100860→100806 |
| 19 | 100901 | 100984,100985,100986,100987 | 100988→100903→100904→100960→100906 |
| 111 | 103201 | 103283,103284,103285,103286,103287 | 103288→103204→103205→103260→103206 |

101002的全表前驱只有101001、后继只有101003；它没有从上述43个首分支命中，**不推断为坏表、无效或应删除**。本族政策可先显式只覆盖十条自然节点，101002保留资料/未授权状态，后续若有真实入口证据再纳入。

## 全族共用字段与差异

11条原属性与100106比较，除id外只差ProcessBarColor是否存在；其余原属性逐字段完全相同。列表差别只有PostMissionList及DisPlayNPCID；不把缺Color填成“原显式ffffff33”。

- `MissionName=[主线]序章缘起，MissionTypeString=主线剧情，MissionType=10`；MinLevel/MaxLevel、TransMinLevel/TransMaxLevel全0，TransformID0。
- `ProcessBarTime=3，ProcessBarText=触摸血手印`；Color仅100106/103206原有ffffff33，其余9条属性不存在。显示缺省色另属客户端parser/UI行为，不影响服务器将原时量保存为3。
- **全部奖励**：`ExpReward=0、MoneyReward=0、PetExpReward=0、ShengWang=0、SMoney=0`；全部无RewardItem列表。明确0不能换成任务缺失奖励比例，也不产生宠物经验接收者/货币到账设计。
- `RewardMapJumpType=3、RewardMapID=1501、RewardMapXPos=63、RewardMapYPos=79`；任务目标地图仍是源1006、NPC10498。**奖励目标不是领取时已在1501的证明。**
- ActiveInfoTargetID/Num、L/T/R/B、MiniStep/MaxStep、StepProbability、TimeLimit、IsRestartTimer、GiveBackMoney/GiveBackPetID、UseItemID、OtherType和QuestionInfoNpcID均0；ActiveInfoTeamState1。
- AIInfoAIID0、AIInfoBattleResult1、AIInfoDeathPunish0、AIInfoTeamSteate1；BattleInfoBattleMapType1，其余BattleInfoBattleZoneID/Drop/Times/MonsterNum/DropItemID/DropItemNum0。**这个节点自身不是AI8001战斗。**
- ScenarioInfoAnimationID/BranchNpcID0，没有Start/Finish对白、BranchNote/Option、RequestMissionList或RequestRoleIDList。角色资格来自前述可信自然章节/原路线，不是血手印行自己写了限定十角色。
- 全部相同NoteInfo：`触摸血手印后，周围的世界仿佛发生了变化。神秘的说书人正站在你面前……`；描述/目的/追踪原文均指调查陆家庄血手印，不含技能授予承诺。

DisPlayNPCID两组差异应原样进入后置元数据；10083与10491是不同源嘉兴说书人实体，不能因为文本相同就替换成一个ID，也不能仅凭列表名就断言生成/删除动作。[S1、S4、S6]

## 真实NPC、目标坐标与mask

原场景placement按原npc.xml顺序加1，不是NPC模板ID：

| 用途 | 地图/资源 | 原placement / NPC | 原posx,posy | NPC配置另有xPos,yPos |
|---|---|---|---|---|
| 本族统一交互 | 1006 / map_1006_jiaxing | 13 / 10498血手印 | **1668,970**，dir4 | 104,60；hide1 |
| 后继统一目标 | 1501 / fubenjiaxing | 10 / 10908说书人 | **1049,1559**，dir5 | 65,97；hide1 |
| 前驱/后置列表一组 | 1006 | 3 / 10083说书人 | 348,2244，dir3 | 21,140；hide5 |
| 前驱/后置列表另一组 | 1006 | 11 / 10491说书人 | 1538,2368，dir5 | 96,148；hide5 |

NPC配置xPos/yPos与场景posx/posy并非同一字段，不能混用。当前世界恢复通过真实NpcInteraction校验当前实例key/地图/位置版本/距离；不以客户端填NPC模板ID替代实体证明。

原1501配置资源存在，dream=1、findpathin=false、dynamic=0；这些字段不能证明原官方服务器按角色私有实例化。可用原图和原NPC，不等于已有可信私有梦境归属/恢复政策。

本轮重新CRC读取S8，执行现已由原生证明的逻辑像素→maze cell(mask)纯查询：

| 解释/位置 | 原maze cell | cell byte | mask1可通行 | mask8可通行 | 证据等级 |
|---|---|---:|---|---|---|
| raw63/79直接当逻辑像素 | 3,4 | 11 | 否 | 否 | 实际原格查询；不支持该落点解释 |
| **raw×16候选1008/1264** | **63,79** | **8** | **是** | **否** | 单位转换仍**inferred** |
| 后继NPC原pos1049/1559 | 65,97 | 8 | 是 | 否 | NPC原场景位置+格查询 |

由raw×16候选到目标说书人差(41,295)，不是当前位置已在32交互半径内；仍需真实梦境移动/实例交互，不允许传入后立即伪造NPC接触。格查询不证明全路径可达、UI寻路或目标边界正确，不用mask8结果猜飞行规则。

**全十条共用63/79**与同一合法mask1候选，为root采用统一×16解释提供一致性旁证；仍未找到任务RewardMap字段自己的原消费者证明单位。旧官方端游剧情资料仅支持嘉兴血手印→梦境叙事大纲，前两份报告已经记录其没有此坐标/单位；本轮未重复泛搜，也不把其他portal或车夫已有×16政策自动移植为client_verified。

## 可共用Interface与必须单独裁定

原完成通路沿已核实kind5本地读条→`CCommitScenarioQuest0xc4a44`：BEi32taskID、BEu64真实NPCkey、BEi32option0；没有elapsed、开始确认、取消上行、地图/坐标或私有实例字段。WindowUpdate float delta与阈值3同单位，但其全局绝对秒单位仍未闭合。root拟采用服务器最短**3000ms**须标designed，不能写成原生已证3秒；菜单授权时刻也不是客户端开始读条ACK。

建议可集中检查的原族不变量：显式十ID、可信role×school章节route、对应唯一前驱已完成/该任务active、真实10498/1006交互、原时量3/Jump3/1501/63/79和原全0奖励保持、关联位置/任务版本及世代。各Module继续用一份冻结intent和调用方租约事务组合世界目标commit、任务完成及明确后继处置，不在shared复制十份数值/凭据逻辑。此为Interface建议，未发布实现或政策。

需要root独立设计的精确缺口：

1. ×16是否正式采用，以及正常状态mask1目标落点和候选失败处理。
2. 服务端3000ms、移动/交互/断线失效规则；无专用开始或取消包，不能等一个不存在的ACK。
3. 私有梦境实例的所有者键/实例身份、重连恢复、返回世界时机；原MapID1501不能直接代替私有实例ID。
4. 十条后继均是type40/AI8001：是只恢复active显示且拒绝入战，还是明确pending，由root定；**不开放正式AI、不伪造胜利、不跳到后续“掌握技能”节点**。血手印0奖励本身也不会授技能。
5. 101002未在43自然路径内命中，是否另有合法入口；没有证据前不以同文案授予。

## 方法、验证与未验证

research实际用于全表精确文本筛选→原字段/list与TaskResources一致→全表逆边→43条显式route、RequestRoleIDList和学校资格交叉核验→源/目标原NPC placement→原maze候选查询；结果由“预期十条”修正为“11条文本、10条自然族”，未删除多出的原记录。codebase-design用于将十分支公共不变量收在一个小Interface，保留角色路线、实例、事务和原wire的独立责任，不新造全局锁或影子任务账本。

验证完成：11条原属性/lists一致、全部唯一前驱/后继、43角色×门派实际路径覆盖（4+5+5+4+4+4+4+4+4+5=43）、两个颜色显式字段/九个缺省、奖励0、NPC和mask原数据。产物仅本文，未改其他窗口文件。

未验证：自然端到端、实际走路/GUI/读条计时、完整寻路、原NPC隐藏阶段、私有梦境、服务器原时间/坐标规则、战斗、技能、真实库/真人角色、部署或现场修复。当前结果是批量原资源/静态研究，不是十路线都已可玩或已实测通过。

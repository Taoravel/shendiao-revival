# 嘉兴60001后八节点：原表与当前接线审计

日期：2026-10-23。范围：本地《神雕侠侣》端游1.6.1、网络601；古墓角色路线 `(role_config=9, school=11)`，当前自然验证脚本到任务100105完成、原120XP使人物到L2/XP31。只读研究，未运行该脚本、战斗、GUI、服务、认证现场或真实角色。战斗聊天继续暂停。

## 结论与下一纵切

原唯一链为：

`100105（60001标题） → 100160 → 100106 → 100107 → 100179 → 100190 → 100161 → 100110 → 100111 → 100112`。

前八个后继是 **100160、100106、100107、100179、100190、100161、100110、100111**。100160可走现有纯对白Interface；当前首个实际缺口是100160结算后，TaskChain不能激活带读条/传送的100106。100106是血手印本地进度种类5，完成仍发送CCommit；它需要专门的任务资格、计时政策和同事务世界传送组合，不能空对白完成。**第三个后继100107/type40/AI8001是首个真正战斗依赖，保持暂停，不创建或运行战斗。** [S1、C1–C5、N1–N3]

这是古墓链的精确ID，不能推广为十门派共用ID。其他60001节点的后继分别为100204→100260、100304→100360、100404→100460、100504→100560、100604→100660、100704→100760、100804→100860、100904→100960、103205→103260；本批未审计它们后八条的等价性。[S1]

## 一手资源核验与来源

本轮用 `PfsArchive.read` 直接核验目录/本地头、长度、CRC，再BXML解码；未重跑会覆盖目录的提取程序。9条含100105的原属性、全部列表均与 `catalogs/tasks.json` 和 `catalogs/knight.gsp.task.cmainmissioninfo.json` 完全一致。TaskResources启动读取的就是这些mission对象，见 [tasks.py](../tasks.py:33)、`prepare_task_store`第45–51行；没有借运行库或现有角色推断原任务。下列短路径均相对 `D:/神雕侠侣`。

| 来源 | 原包条目 | 解压字节/CRC32 | SHA-256 |
|---|---|---|---|
| S1 | artres/config.pfs → autoconfig/knight.gsp.task.cmainmissioninfo.xml | 2026233 / 3f7ab7b3；2460行 | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |
| S2 | 同包 → autoconfig/knight.gsp.npc.cnpcconfig.xml | 619832 / cc437e13 | b4fc5d440380fb535a36b8e5315c5a1bf10a99f550f5bfde55bd156fca864f85 |
| S3 | 同包 → autoconfig/knight.gsp.map.cmapconfig.xml | 91110 / 3325016f | 374d400f933a74e83d402c8da948fef47823e7f92344ccb660414edfb87a1814 |
| S4 | artres/map.pfs → map_1006_jiaxing/npc.xml | 3571 / 51217023 | 72b66cc70e41d78997fb8369c74c5f21a69f500e790797718a41d56ff857752c |
| S5 | artres/map.pfs → fubenjiaxing/npc.xml | 888 / 06370594 | 3e96b678f8213459052fcf8c9fccc9c1eb7222ac33672d2a966600513f7b32fa |
| S6 | artres/config.pfs → movie/10019.txt | 8836 / e4d20b75 | bc8206989585938d8b411d3bfd635178553f92aaddfc0f79a1cbcefc5563a5bc |
| S7 | 同包 → movie/10001.txt | 9004 / 424d12bc | c539ab40e437da8d2a8bd5efc5dd914a54a1b719427bb7c2b991a657df207c67 |
| S8 | artres/map.pfs → fubenjiaxing/maze.dat | 113676 / cda771b4 | 6f81a7407738d6ce9b7ca167c82c28849dea1db12e7f2aa7fe1285e747698351 |

S4/S5逐条去除目录附加的definition_name后，与 `catalogs/world.json` 完全一致。原NPC配置的xPos/yPos与场景npc.xml的posx/posy是不同字段，本报告交互坐标一律使用后者，不拿前者直接代入世界逻辑像素。

## 八节点逐条原字段

下表行号为 `decoded/config/autoconfig/knight.gsp.task.cmainmissioninfo.xml` 的record首行；原包S1的ID是身份依据。八条均名“[主线]序章缘起”，MinLevel/MaxLevel=0/0，无RequestMissionList/RequestRoleIDList，无RewardItem列表，`ActiveInfoTargetID/Num=0/0`。**没有道具收集目标**；血手印是NPC实体，不是背包物品。全部MoneyReward/PetExpReward/ShengWang=0；表中未写出的SMoney也为0，明确0不启用缺失奖励兜底。

| 序号 / ID / 原行 | 前置边→后继 | type；目标NPC / 地图 | 原开始/完成对白句数 | 关键原字段 | ExpReward / SMoney |
|---|---|---|---|---|---|
| 1 / 100160 / 301 | 100105→100106 | 10；10083说书人 / 1006嘉兴 | 3 / 0 | Animation=0，ProcessBarTime=0，Jump=0 | 0 / 0 |
| 2 / 100106 / 42 | 100160→100107 | 10；10498血手印 / 1006 | 0 / 0 | ProcessBarTime=3，ProcessBarText=触摸血手印，Color=ffffff33；Jump=3、Map=1501、X/Y=63/79；NoteInfo非空 | 0 / 0 |
| 3 / 100107 / 50 | 100106→100179 | 40；10908说书人 / 1501梦境嘉兴 | 3 / 2 | AIInfoAIID=8001；Animation=10019；Jump=0 | 120 / 400 |
| 4 / 100179 / 328 | 100107→100190 | 10；10908说书人 / 1501 | 0 / 0 | ProcessBarTime=1，ProcessBarText=掌握技能；目的“学习太祖长拳”；Animation/Jump=0 | 120 / 0 |
| 5 / 100190 / 440 | 100179→100161 | 40；10908说书人 / 1501 | 3 / 1 | AIInfoAIID=8027；Animation/Jump=0；目的“击退梦魇邪兽（需战斗）” | 255 / 600 |
| 6 / 100161 / 319 | 100190→100110 | 10；10084陆立鼎 / 1501 | 0 / 0 | Animation=10001；ProcessBarTime/Jump=0 | 0 / 0 |
| 7 / 100110 / 76 | 100161→100111 | 40；10084陆立鼎 / 1501 | 3 / 1 | AIInfoAIID=8002；Animation/Jump=0；目的对抗李莫愁 | 400 / 1000 |
| 8 / 100111 / 102 | 100110→100112 | 10；10085黄药师 / 1501 | 4 / 0 | Jump=3、Map=1006、X/Y=170/70；ProcessBarTime/Animation=0 | 125 / 0 |

三个type40均原 `AIInfoBattleResult=1`、DeathPunish=0、TeamSteate=1、BattleMapType=1；AI数字不能单独恢复正式敌阵/战斗算法，沿既有正式PVE能力门禁。100179的正文证明叙事为传授太祖长拳，但原任务没有本次授技能ID、等级、习得下行或服务端授予时点字段，不能只完成1单位读条就宣称技能已实现。[S1]

`DisPlayNPCID` 原列表（只保留字面，不直接解释为生成/删除指令）：100160=[10212]；100106=[10083]；100107=[10909]；100179/100190=[10910,10911,10912]；100161=[10596,10597]；100110=[10006,10596,10597]；100111=[10084,10596,10597]。隐藏NPC可见阶段仍需原消费者/世界政策，不凭列表名决定含义。[S1、S2]

### NPC实体与地图

placement编号来自原npc.xml顺序加1，与 `load_placements` 当前Interface一致；key为当前Adapter的 `(map_id<<32)|placement_id`，不是原服务端固定NPC ID。[S4/S5、world_npcs.py:35、game_runtime.py:85]

| 使用任务 | map / placement / NPC ID | 场景原posx,posy | 当前Adapter的entity key构造 |
|---|---|---|---|
| 100160 | 1006 / 3 / 10083说书人 | 348,2244 | (1006<<32)\|3 |
| 100106 | 1006 / 13 / 10498血手印 | 1668,970 | (1006<<32)\|13 |
| 100107/179/190 | 1501 / 10 / 10908说书人 | 1049,1559 | (1501<<32)\|10 |
| 100161/110 | 1501 / 1 / 10084陆立鼎 | 2201,814 | (1501<<32)\|1 |
| 100111 | 1501 / 2 / 10085黄药师 | 2426,640 | (1501<<32)\|2 |

1501附带梦魇杀手10909：(placement11,919,1613)，邪兽10910/10911/10912：(12,860,1735)/(13,858,1556)/(14,1075,1733)；李莫愁10006：(7,2261,616)，武三娘10596：(8,2134,518)，陆二娘10597：(9,2210,468)。这些只是场景实体，不作为正式battle Fighter或AI敌阵替代物。

地图1006与1501均原资源存在，resdir分别map_1006_jiaxing/fubenjiaxing；1501 dream=1、findpathin=false，1006 dream=0、findpathin=true。`GameRuntime.MapOwner`目前按定义/边界构建全部placement的spawn，不等于已复原cnpcconfig.hide=1/5或DisPlayNPCID的阶段可见规则。自然移动可达性、NPC遮罩与真实呈现本批没有验证。

## 100106：四种证据必须分开

### N1：原任务类型、菜单和本地读条开始

普通可提交任务NPC菜单来源沿 [TASK_DIALOG_PROTOCOL.md](TASK_DIALOG_PROTOCOL.md)、[TASK_JIAXING_SCENARIO_RESEARCH.md](TASK_JIAXING_SCENARIO_RESEARCH.md)。原 `0x1257b20` 把已接且state3分类为可交付；UI `0x164d780 → 0x164b530` 消费原对白，空列表转 `0x1643360`。100106既不是type50自动剧情，也不是物品使用type22。

本轮只读原native-image.bin反汇编直接确认：

- `0x16433a0–0x16433a9` 判断CMainMissionInfo `+0x164==10`。
- parser `0xbb5d19–0xbb5d45`：UTF16字段名ProcessBarTime在`0x226c460`，整数保存config`+0xd8`；ProcessBarText在`0x226c440`，parser `0xbb5d58–0xbb5d8c`保存string到`+0xdc`。
- `0x16433af–0x16433bd`检查该时间>0；`0x16433bf–0x16433df`将整数转float，传**kind5、文本、当前NPC u64、taskID**给本地UI `0x8114a0 → 0x16c4140`。原时间3不经服务器下行生成。
- `0x16c416b–0x16c419b`保存总量到UI`+0x4c`、kind到`+0x5c`、NPCkey到`+0x60/+0x64`，关联taskID交进度UI控件。**所查开始路径没有发另一个“开始读条”网络包，也没有要求新的SProgress消息。**

通常称此处“3秒读条”；精确已证实的是原整数3→本地float阈值3、按帧delta累计。本轮没有追溯帧事件delta的全局时间单位或真人计时，服务端最短时长/取消政策仍须root明确设计，不能把wire当可信已耗时证据。

### N2：本地读完后的完成请求

`0x16c49c0`读帧事件`+0xc`，`0x16c49db–0x16c49f7`累计UI`+0x44`并与总量`+0x4c`比较，到阈值经`0x16c4a6e`调用完成函数`0x16c4490`。其kind5分支`0x16c47c8–0x16c47ff`调用`0xdd4780`构造**CCommitScenarioQuest 0xc4a44**，从进度控件`+0x26c`取关联taskID，写当前NPCkey，发送经`0x16c492b–0x16c4933`。

构造`0xdd4780–0xdd479d`把option初始化0；marshal`0xe57530`/unmarshal`0xdd4840`沿既有 [TASK_PROTOCOL.md](TASK_PROTOCOL.md) 已证实16字节BE：`i32 taskID | u64 npcKey | i32 option0`。没有elapsed、读条开始序号、目标地图或坐标，也没有CEndPlayCG/独立“完成进度”包。原kind6是战斗请求0xc4a4c，**不是100106的kind5**。

客户端可伪造相同CCommit；允许提交必须由当前角色/任务/真实NPC交互阶段、位置/任务版本、连接世代与期限约束。因为开始没有上报，服务器无法从该包恢复精确的实际点击开始时刻。是否采用菜单授权时刻作保守最早提交时刻、取消/移动如何失效，是需要root裁定的服务端政策。

### N3：RewardJump3、目标与单位

原100106字段确为`RewardMapJumpType=3, MapID=1501, XPos=63, YPos=79`。字段parser保存Jump至config`+0xc8`、Map至`+0xcc`、X/Y至`+0xd0/+0xd4`（`0xbb5c1d–0xbb5d06`，已见 [TASK_CART_BRANCH_RESEARCH.md](TASK_CART_BRANCH_RESEARCH.md) N4），只存整数。

本轮复读`0x1255e70`完成fallback：`0x1255e75–0x1255ea3`用AnimationID与Jump是否为0决定立即表现或暂存，只证明Jump参与后置分流，**没有证明“3”是某个SRoleEnterScene.reason或客户端主动传送命令**。对白结束`0x1644c1d`仅UI阶段3，Jump>0可进入`0x1644cb6–0x1644cf2`发送CQuestDialogEnd(taskID)；100106没有Finish对白，本批没有闭合Note显示→该UI阶段3的必经调用，不能把此包强设本任务首次完成或跨图ready。

已查本地完成/对白/后置函数没有消费Map/X/Y形成传送坐标；CCommit没有这些字段。服务端合法目标与提交时点须单独决定。现世界真正下行是 `SRoleEnterScene=0xc0fa9`，既有原handler`0x11e3140`； [SCENE_READY_RESEARCH.md](SCENE_READY_RESEARCH.md)保留“普通地图无通用客户端加载ACK”的限制。`CAfterEnterWorld`或本地timer不能冒充100106普通换图确认。

S8离线格数据只提供候选过滤：直接当逻辑像素(63,79)时mask1/mask8均阻挡；乘16候选(1008,1264)时mask1可走、mask8阻挡。**可走不证明坐标单位**；×16最多inferred，采用须root另记designed，不能自动继承只覆盖十条车夫任务的政策。旧 [NEW_CHARACTER_OPENING_RESEARCH.md](NEW_CHARACTER_OPENING_RESEARCH.md)将这里称“格”的措辞超出已闭合消费者，本报告以原整数、单位未确认修正其证据等级，未修改旧报告。

### C1：当前代码是否已经支持组合

没有。`task_domain.py:10/17`的普通对白谓词显式拒绝ProcessBarTime及RewardMapJumpType；`TaskConversation.open:78`在暴露ready3前调用该领域验证，因此不会获得合法100106票据。`task_chains.plan_task_chain:54`也只激活已支持能力，故100160完成后原边应记录`pending/successor_gameplay_unimplemented`，不是自动active100106。[task_chains.py](../task_chains.py:23)

通用 `complete_task_transaction`只在调用方事务里完成任务/奖励/已支持后继，保留传送等未执行字段，不调用世界提交。[task_workflow.py](../task_workflow.py:41)、[task_domain.py](../task_domain.py:259)

世界已有 `prepare_transfer/reserve/freeze/activate/finalize/ready` Interface与 `commit_transfer_transaction`（加入调用方现有事务），但不授权某个任务。当前原子模板是**仅车夫专用** `complete_cart_transfer_transaction:175`：特定原route/章节/选择武器资格、自己的表/政策及`newbie_cart_transfer_committed`证据，不能直接拿100106去调用。共享 `RoleOwner.handoff:695`当前只有普通位置提交或cart_intent分支，无一般任务读条intent。[world_owner.py](../world_owner.py:412)、[world_transfer_storage.py](../world_transfer_storage.py:111)、[task_cart_transfer.py](../task_cart_transfer.py:175)、[game_runtime.py](../game_runtime.py:695)

还存在第二处真实门槛：即使未来完成100106，普通TaskChain仍不会激活type40的100107；应明确设计“建立并恢复active任务、但战斗入场禁用”的呈现/续接能力，或者如实保留pending。不能为了让链继续而开启正式战斗注册、注入胜利或跳100107到100179。

## 各任务所需协议与实现现状

| 节点 | 需要的原交互/后置表现 | 当前可复用Interface / 尚缺 |
|---|---|---|
| 100160 | CVisitNpc0xc2329；ready3+SVisitNpc0xc232a本地3句→CCommit0xc4a44；成功state1、当前XP/属性 | TaskConversation.open/menu_messages/plan_finish及complete_task_transaction已支持纯type10；0奖励保留。下一100106仍pending。未验证本次自然走路/真人对白 |
| 100106 | 原kind5本地读条→CCommit；0XP；Note/Jump3/1501目标 | 现无领域完成证据/读条票据/与世界同事务组合；详N1–N3/C1 |
| 100107 | 本地3句→CActiveScenarioQuestAIBattle0xc4a4c，BEi32task+BEu64NPCkey（12字节）；正式战斗胜利后原2句Finish/Animation10019 | task_battle.open_task_battle_dialogue/admit/settle已有独立Interface，load_task_battle_resources默认enabled空；共享game_runtime未导入接线，正式AI8001未在本批授权。保持暂停 |
| 100179 | 同type10的kind5读条→CCommit；传授技能事实需额外持久状态/下行 | 当前ProcessBarTime阻断。不能只凭“掌握技能”文案/原XP120伪造已习得技能 |
| 100190 | 3句→0xc4a4c，正式AI8027，1句Finish | 同正式战斗门禁；暂停；不把梦魇场景NPC直接作为敌阵 |
| 100161 | 空start的type10普通CCommit；后置Animation10001 | 仅60001有明确特殊能力白名单，此动画使普通谓词拒绝。不是type50 Start/Finish族；电影启动/结束与任务时点待单独恢复 |
| 100110 | 3句→0xc4a4c，正式AI8002，1句Finish | 同正式战斗门禁；暂停 |
| 100111 | 本地4句→普通CCommit；随后Jump3回1006原(170,70) | 被RewardJump阻断；应复用将来100106任务传送Seam，不套车夫scope或擅定坐标单位 |

任务状态既有type为SAccept0xc4a45、SRefreshState0xc4a47；活动0、移除1、失败2、可交3，以 [TASK_TRACKER_FAILURE_RESEARCH.md](TASK_TRACKER_FAILURE_RESEARCH.md)及当前task_protocol为准，不能沿旧报告的state2进行中表述。普通XP刷新0xc000d是当前余额；SMoney字段到bound_silver的业务映射仍是主策划designed，不能因本表原金额已确认提升为原版货币语义。[task_protocol.py](../task_protocol.py:11)、[task_dialog_protocol.py](../task_dialog_protocol.py:1)、[CURRENCY_DECISION.md](CURRENCY_DECISION.md)

### 原Animation资源只证明存在，不等同完成授权

100107的10019和100161的10001确有原movie文本（S6/S7）。10019首行原文同时串着两个Setmap：`Setmap id=1501 pos=65,98 ... Setmap id=1501 pos=99,40`，Return第125行、End第126行；本批未证明同一行第二命令的解析。10001首行是`Setmap id=1006 pos=132,33`，Return第177行、End第178行，而100161任务交互图是1501。电影临时地图/镜头不自动改持久角色位置，也不能据此覆盖原ActiveMap。

既有完成fallback `0x1255e70`对小于20000的Animation没有走60001立即效果分支，所以不能把60001已恢复的完成规则套给10019/10001，更不能发送CEndPlayCG(10001)就完成type10。具体SStartPlayCG授权时点、客户端自然结束上行是否参与这些节点原服推进，本批未闭合，保持独立缺口。

## 建议下一必要纵切（交root裁定，不是已发布政策）

1. 先延伸现有古墓自然脚本到100160：同原角色/地图/移动与NPCkey，3句对白匹配CCommit，验证0奖励、一次完成及100106 pending理由；需要世界窗口补实路可达，不靠测试offer跳过前置。
2. 单独支持100106：从已完成100160的原唯一边授权active；在角色Module维护一个受版本/世代约束的读条/交互intent；CCommit只提交该intent。root先定实际最短时长、取消/移动/断线规则，以及目标坐标单位/合法落点。新的Interface应隐藏这些细节，避免共享入口复制任务字段和凭据校验。
3. 世界Module预留/冻结/激活目标，在角色同一租约事务里组合世界commit、100106完成/原0奖励/唯一后继处置/回执；任何失败回滚，不先移除任务再独立传送。发送屏障/迟到旧输入隔离、断线恢复沿现有世界契约；不等待不存在的通用ACK。
4. 可在不战斗前提验收到梦境目标loading→send-barrier→active、NPC10908可交互，以及100107正确active但拒绝入战（或明确pending，须root选定）。**以此作为本批非战斗停止点。** 后五节点只做原表与静态能力准备，不伪造战斗胜利，不恢复暂停战斗聊天。

100160/106能力范围、100107未启用时是否进入journal、授技能规则、Animation10019/10001后置时点、DisPlayNPCID可见阶段、100111返回坐标均是精确待裁定项；本报告没有自行创设原版事实。

## 定向官方旁证

本轮查官方端游域名sdxl.wanmei.com，关键词“血手印 说书人”“序章缘起 太祖长拳”“梦境嘉兴”。可用一手页面为2012-07-28 [官方资料站：剧情任务](https://sdxl.wanmei.com/info/renwu/script/20120728/133491.shtml)：序章由师父赠武器、车夫赴嘉兴，列柯镇恶、说书人、血手印、陆立鼎、黄药师等NPC。它支持剧情大纲；未给本八ID、3单位读条协议、63/79单位、技能授予时点或本版原奖励，不能补这些缺口。没有使用手游/神雕2或后期攻略覆盖本地原字段。

## 方法、验证与未验证

- **research**：本代理已是后台研究者；本批重读技能，优先追原PFS→解码→实际TaskResources数据→原生UI提交→当前领域/世界Interface。只在精确未知项出现后定向官方查找，原文未给即保留unknown；产物仅本Markdown。
- **codebase-design**：实际决定是区分通用完成Interface、专用车夫Adapter、世界持久化Seam，不因底层transfer可用而声称100106已接。建议把读条/传送复杂度放入同一小Interface，保留实体所有者和调用方事务，未引入世界锁/双账本或改生产实现。
- **验证完成**：原PFS长度/CRC、上述9任务属性与全部lists双目录一致、1006/1501原placement与world目录一致、8条唯一后继、原movie存在/指定行、1501两个坐标候选mask离线查询；定向只读原生反汇编验证kind5开始/完成和Jump消费范围；源码逐函数静态审计。
- **未验证**：本批不执行任何玩法/自然链/战斗检查，未实际等待进度、GUI点击、发送/注入、部署/服务/真实库/真实角色。原帧delta绝对时间单位、取消全过程、原服务端传送/技能/正式AI算法、剧情显示/隐藏NPC呈现及全部十门派等价性仍未确认。现有verify脚本通过范围只据脚本断言和root已提供结果说明，不能把本次只读审计称为新增运行时验收。

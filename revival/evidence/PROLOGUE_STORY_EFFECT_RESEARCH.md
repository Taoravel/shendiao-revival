# 序章10001/10002任务后置表现原证

跨CG1/CG2与两次梦醒的完整原任务链、四族奖励/传送字段及消费语义，统一查[PROLOGUE_DREAM_RETURN_RESEARCH.md](PROLOGUE_DREAM_RETURN_RESEARCH.md)的2026-10-24收敛节；本页保留各原指令与probe的详细记录。新政策采用和实际部署仍分别验收。

2026-10-23。范围：43条原角色门派开场路线中，陆立鼎100161同族十条与破窑100114同族十条。方法采用 research：直接重读原config.pfs的CRC/BXML与电影文本，沿PostMissionList实边确定范围，使用原映射x86指令及离线Unicorn执行局部分支。已读ARCHITECTURE.md、DESIGN_AUTHORITY.md；不修改服务器/共享入口/政策，不运行客户端、线上库或战斗。

## 可供下一批实现采用的结论

- `client_verified`：两族均为type10。10001族无Start/Finish对白且ProcessBarTime=0，原phase2走普通CCommit；10002族两句Start后启动kind5、原数值1的本地读条，读条完成再发CCommit。请求均为0xc4a44，taskID、NPCkey、option0，没有解算电影或战斗结果。
- `client_verified`：完成刷新state1、无Finish/Note时会调用0x1255e70，把10001/10002存入任务manager+0x70。此路径没有进入CG播放；原暂存消费函数0x12550c0对小于20000直接返回，连暂存值也不清。**不能将state1称为“原客户端已自行启动这两部CG”。**
- `client_verified`：原包确有movie/10001.txt与movie/10002.txt；CQuestEffect表中无这两个ID。显式SStartPlayCG进入原0x12c43b0可将任一ID传给CG入口0x12c4140；自然电影结束通道可发送当前movieID的CEndPlayCG。**资源存在、显式包可播放、原服何时发包是三项不同事实。**
- `inferred/未证`：未找到manager+0x70到这两部CG的调用桥，未取得原服SStartPlayCG发送时点或任务完成与CG确认的顺序。不能凭本报告把“等待CEndPlayCG才完成任务”描述为原版机制。
- 最小可信任务输入是经当前任务/NPC/角色状态授权的CCommit；其代表客户端提交请求，不是电影成功或战斗胜利。若本地恢复选择服务端显式启动CG、持久化播放授权及等待匹配CEnd，该连接策略须由主策划标为`designed`，不能作为本批原证发布。10002的Jump字段同样不能由客户端临时电影Setmap替代地图所有者的正式交接。

## 原包审计与范围

原件为项目artres/config.pfs；以下为从PFS读取的解包字节长度/CRC32，不是缓存JSON的散列。BXML任务表2460行。

| 包内路径 | bytes | CRC32 | SHA256 |
|---|---:|---|---|
| autoconfig/knight.gsp.task.cmainmissioninfo.xml | 2026233 | 3f7ab7b3 | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |
| autoconfig/knight.gsp.task.cquesteffect.xml | 2476 | 81ba986b | 8fbbda8366389fe8da2635a4f4160717a6c30b25f3d969f163906366243c9e45 |
| movie/10001.txt | 9004 | 424d12bc | c539ab40e437da8d2a8bd5efc5dd914a54a1b719427bb7c2b991a657df207c67 |
| movie/10002.txt | 13442 | 0407b9da | 0ec9a682c885389c7ca392db6f44f2494398e619b923e22e232a85839cdf114e |

原映像[evidence/native-image.bin](native-image.bin)：50675712字节，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。本文地址均为该映像VA，BASE=0x400000。

从[catalogs/newbie-routes.json](../catalogs/newbie-routes.json)的43个intro_task_id逐一遍历**原表**PostMissionList。每条路线恰好命中10001、10002各一条，去重后各十条。并非按ID规律扩出任务。

| 门派/root | 角色ID | 10001节点 | 10002节点 |
|---|---|---:|---:|
| 11/100101 | 2,5,9,10 | 100161 | 100114 |
| 12/100201 | 1,3,4,6,7 | 100261 | 100213 |
| 13/100301 | 1,3,5,6,7 | 100361 | 100313 |
| 14/100401 | 3,4,7,8 | 100461 | 100413 |
| 15/100501 | 2,4,8,9 | 100561 | 100513 |
| 16/100601 | 1,5,6,10 | 100661 | 100613 |
| 17/100701 | 2,5,6,10 | 100761 | 100713 |
| 18/100801 | 1,4,8,9 | 100861 | 100813 |
| 19/100901 | 2,3,7,8 | 100961 | 100913 |
| 111/103201 | 1,4,5,9,10 | 103261 | 103214 |

原表实边：

| 10001的前驱→本节点→后继 | 10002的前驱→本节点→后继 |
|---|---|
| 100190→100161→100110 | 100191→100114→100117 |
| 100290→100261→100209 | 100291→100213→100216 |
| 100390→100361→100309 | 100391→100313→100316 |
| 100490→100461→100409 | 100491→100413→100416 |
| 100590→100561→100509 | 100591→100513→100516 |
| 100690→100661→100609 | 100691→100613→100616 |
| 100790→100761→100709 | 100791→100713→100716 |
| 100890→100861→100809 | 100891→100813→100816 |
| 100990→100961→100909 | 100991→100913→100916 |
| 103290→103261→103210 | 103291→103214→103217 |

10001的前驱、后继均type40；10002前驱type40、后继type10。示例100190原AI8027、100110原AI8002、100191原AI8028；本文不执行或跳过这些节点，也不将前驱当成普通对白。全表另有旧线101004→101005→101006与101015→101016→101017，对应10001/10002，但不属于上述43路线。尤其旧101016的ProcessBarTime=3、Jump坐标333,56与当前十条不同，不纳入恢复域。

## 原任务字段

| 字段 | 10001十条 | 10002十条 |
|---|---|---|
| MissionType | 10 | 10 |
| ActiveInfoNpcID/MapID | 10084 / 1501 | 10088 / 1006 |
| ScenarioInfoAnimationID | 10001 | 10002 |
| Start/Finish对白条数 | 0 / 0 | 2 / 0 |
| ProcessBarTime | 0 | 1 |
| ProcessBarText | 无 | 查看破窑 |
| RewardMapJumpType/ID/X/Y | 0/0/0/0 | 3/1501/335/50 |
| ExpReward/MoneyReward/PetExpReward/ShengWang/SMoney | 全0 | 全0 |
| ActiveInfoTargetID/Num、AIInfoAIID、ScenarioInfoBranchNpcID | 全0 | 全0 |
| NoteInfo/ScenarioInfoBranchNote | 无 | 无 |
| RewardItemIDList/RewardItemNumList | 无 | 无 |

重要非同一字段：100161、103261有DisPlayNPCID=[10596,10597]，其余八个10001节点没有该list；100114、103214的ProcessBarColor=ffffff33，其余八个10002节点未写该属性。不能为了共用实现把缺省字段补成完全相同。两族其余上述机制字段、对白列表已逐条比较原行。

100114 Start原文两句为破窑石刻“问世间情为何物，直教生死相许……”及人物触摸后眩晕；两条ScenarioInfoNpcID均1。文案说明内容，触发依据仍以原函数为准。

## 提交与读条的实际顺序

原任务UI分类/Start链沿既有[TASK_SCENARIO_START_RESEARCH.md](TASK_SCENARIO_START_RESEARCH.md)、[FIRST_MASTER_CARD_TRIGGER_AUDIT.md](FIRST_MASTER_CARD_TRIGGER_AUDIT.md)的phase2证据，本批补执行上述任务配置：

1. 原Start耗尽判断返回后，phase2继续函数0x164c3d6..0x164c584进入0x1643360。10001空Start直接走此路；10002两句结束后走此路。
2. 0x16433a0确认type10；0x16433af读config+0xd8的ProcessBarTime。0或负数在0x16433bd进入直接提交0x16433e9..0x164342a，构造0xc4a44，保存当前taskID/NPCkey/option0。
3. 正值原整数转float，0x16433bf..0x16433df传text(config+0xdc)、kind5、duration、NPCkey指针、taskID给0x16c4140。0x8114a0只是取得进度UI对象，不是开始网络包。
4. 0x16c416b..0x16c419b保存duration至UI+0x4c、清累计+0x44、置active+0x2c、kind+0x5c；0x16c41d4..0x16c41dc保存NPCkey两半。taskID在控件+0x26c。
5. 0x16c49c0逐次加event+0xc浮点delta；累计达到阈值转0x16c4a6e→0x16c4490。kind5分支0x16c47c8..0x16c47ff使用原CCommit构造0xdd4780、取上述taskID/key，最终0x16c492b..0x16c4933发送。

因此10002的顺序为Start→本地读条→CCommit；不是先CCommit后读条，也未证明“CG结束才发此CCommit”。原数值1和浮点阈值已证；本次不将delta单位、服务端最短等待/超时换算成原服规则。请求无elapsed或开始/取消标志。phase3专属CQuestDialogEnd条件0x1644c1d..0x1644cf2不能套用本族Start phase2。

离线原指令反馈（UI显示/资源/网络捕获边界，NPCkey取测试64位值）：

```text
Start_exhausted 100161:
  sent_type=0xc4a44, task=100161, npc=0x1122334455667788, option=0
  ui_close_phase=2
Start_exhausted 100114:
  progress_start_kind=5, duration_float=1.0,
  npc=0x1122334455667788, task=100114
  ui_close_phase=2
  (没有发送包)
progress_complete_kind5 100114:
  sent_type=0xc4a44, task=100114, npc=0x1122334455667788, option=0
```

此反馈运行原0x164c3d6..0x164c584，以及进度完成原0x16c47c8..0x16c4935；后者从kind5已到完成条件的边界开始，不冒称完整计时/UI渲染实测。工厂0x8114a0仅返回隔离UI，0x16c4140在提交阶段捕获参数并模拟UI边界返回；提交分支、原CCommit构造与网络发送对象未被替代。计时达到阈值由静态原指令支持。

## state1后置、暂存读写与CG桥

原scenario刷新0x125c020在state1路径移除已有任务bean后，0x125c168检查Finish vector(config+0x304)，否则检查NoteInfo(config+0x94)，两者皆空于0x125c1c8调用0x1255e70。两族均满足fallback；不存在用Finish对白phase3补播的原配置依据。相关完整状态布局见[TASK_PROTOCOL.md](TASK_PROTOCOL.md)与[TASK_NEWBIE_COMPLETION_DISPLAY.md](TASK_NEWBIE_COMPLETION_DISPLAY.md)。

原0x1255e70关键指令：

```text
1255e75 mov eax,[esi+2ac]       ; AnimationID
1255e7b cmp eax,20000
1255e80 jle 1255e98
...                            ; >20000且Jump=0可直接dispatcher
1255e98 jl 1255ea3             ; 10001、10002必走暂存
...
1255ea3 mov [ecx+70],eax       ; task manager pending effect
1255ea6 mov eax,[esi+168]      ; NPC config ID
1255eb3 call 11d1870           ; 查NPC，存在时后续11fcc50
```

所以并非无副作用：会保存pending并可能调用NPC清理/标记。不能把“无CG调用”写成“什么都没发生”。

暂存消费函数0x12550c0：参数非0用参数，参数0从manager+0x70取值；**0x12550d2 cmp eax,20000 / 0x12550d7 jl 0x125511c**，小于20000在ret4前直接返回。30000..59999走0x1749260后清+0x70；其他>=20000走Scene0x11ca790后清。10001/10002均不会进入这两个分支，不会清pending，也不会调用CG。

本批小范围xref：0x12550c0的直接E8调用仅0x1255e8c与0x11e2b46。后一处是场景事件0x7dfb2分支，push ebx后取任务manager调用，随后发送0xc4a54；即使参数为0取pending，仍受到上述<20000早退。不能把此场景完成请求当成电影结束0xc0018。manager附近0x1254000..0x125ffff中+0x70的读写为上述fallback写、dispatcher读与两个清零，以及构造0x125e146初始清零；0x125c1f5的[esi+0x70]属于任务config奖励vector，0x1250xxx的+0x70属于UI控件，不应混作pending消费者。对全映像243处manager全局0x2945584引用做邻近指令筛查，也未发现新的直接pending消费桥。此为有界静态查找，未排除未识别间接调用、动态代码或原服显式消息。

原CG入口0x12c4140的可见直接调用有：SStartPlayCG::Process 0x12c43c0、无已找到调用者的硬编码10001 helper 0x12c43d0→0x12c43d5、另一UI硬编码10000调用0x16bb38b。硬编码helper存在不证明任务调用；本批未发现指向0x12c43d0的直接E8或绝对地址引用，也没有10002的对应自动桥。

原生离线对照输出：

```text
state1_fallback 100161 pending=10001 calls=[]
pending_dispatch_zero 100161 pending=10001 calls=[]
explicit_SStartPlayCG 100161 calls=[cg_start=10001]
state1_fallback 100114 pending=10002 calls=[]
pending_dispatch_zero 100114 pending=10002 calls=[]
explicit_SStartPlayCG 100114 calls=[cg_start=10002]
```

运行的是原state1显示决策块0x125c168..0x125c1cd（无Finish/Note的原表配置字段），完整原0x12550c0(0)与完整原SStartPlayCG::Process0x12c43b0。不是完整任务刷新包：移除bean等之前阶段沿已确认原指令，不在这段反馈里重复模拟。只hook配置外查找、NPC查找返回空及CG资源入口0x12c4140记录参数；测试分支/暂存读取/早退均为原指令。对照显式SStart只证明可进入播放入口，不宣称GPU或客户端现场播放成功。

## 电影资源与结束消息

原UTF16 movie/10001.txt第1行`Setmap id=1006 pos=132,33`，第16行Start，第177行Return time=100、第178行End；10002第1行`Setmap id=1006 pos=290,120`，第7行Start，第236行Return time=100、第237行End。其后为动作枚举注释。脚本内容为NPC/主角、镜头、对白、动作、声音等电影表现命令；未出现任务提交或战斗结果命令。脚本存在与加载路径可支持“这两部是可播放的电影资源”，不支持“完成任务必然自动调用”。

显式SStartPlayCG::Process0x12c43b0：manager全局0x2945620存在时，读取packet+8 movieID，在0x12c43c0调用0x12c4140。后者0x12c4336保存movieID至manager+0x38、播放位+0x3c、原场景+0x40；0x12c437a→0x12c3f10→0x12c3be0按movieID加载/config/movie文件。故网络消息ID与字段桥是明确的，但未在原任务刷新代码中找到发出该消息的服务器端来源。

通用电影结束已由原指令确认：[NEW_CHARACTER_OPENING_RESEARCH.md](NEW_CHARACTER_OPENING_RESEARCH.md)。0x12c0b00 tick在当前section完成且队列为空时于0x12c0b52调用0x12c0970；后者仅播放位+0x3c非0才构造CEndPlayCG(type0xc0018)，0x12c09b2..0x12c09b9取当前movieID+0x38，0x12c0a24..0x12c0a3e发送，随后清播放/movie状态。Return section0x12b99d0→0x12c0bf0恢复先前场景+0x40。结束请求没有“战斗胜利/奖励已结算”字段，同一共用结束函数还可能用于其他结束/清理路径。

电影临时Setmap1006与任务10001的ActiveMap1501、10002的Jump1501并不相等。它们属于不同层：电影临时布景与恢复位置，不应将其当作服务器权威传送、私有实例交接或任务已完成。

## 决定、验证及未验证范围

- 决定：本批只交付证据，不在未知movieID桥处补造原版时序。十条/43路线保留实际原域，旧101005/101016仅记录资料；原战斗前后边保留，未跳过战斗。
- 产物：本文。使用现有native_inspect.py、PfsArchive/bxml.decode、research_task_jiaxing_scenario.Probe与research_first_master_dialogue_end.MasterProbe，执行一次性离线原函数反馈；未新增或修改生产代码。
- 已验证：原四份资源长度/CRC/SHA、原表实边43路线各唯一命中、两族字段与差异、Start提交/读条完成局部输出、state1 fallback暂存、dispatcher小ID早退、显式SStart入口参数。
- 未验证：原服务端何时发SStartPlayCG、是否等待CEnd后才完成/发后继、pending是否有未识别消费者、计时delta外部单位与原服防重/超时、完整GPU电影加载/渲染、正式地图/战斗/奖励/在线客户端现场。未运行客户端、线上数据库、服务端或AI战斗。此报告不等同服务端实现、部署或实机验收。

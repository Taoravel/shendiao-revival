# 到区任务：原版规则、独立实现与接线 Interface

2026-10-23。冻结期间先完成原资料审计；收到主策划明确解除源码冻结后，实现 `task_region.py` 和领域到区证据。**独立 Module 支持158条静态type56目标，另25条保留额外机制；共享运行时尚未接线，未部署、未操作当前客户端或在线数据库。** 原判定、地址和14例离线原指令结果的单一来源为 [TASK_REGION_OBJECTIVES_RESEARCH.md](TASK_REGION_OBJECTIVES_RESEARCH.md)。

## 本批覆盖与范围

直接读取 `artres/config.pfs` 的 `autoconfig/knight.gsp.task.cmainmissioninfo.xml`，PFS读取完成长度/CRC检查，BXML完整解码。183条type56的原attributes及全部lists与现有任务目录逐条相等；条目SHA256见 [task-region-catalog.json](task-region-catalog.json)。该JSON逐条保留原四边字符串、×16半开矩形、额外字段、后继、完成对白数量、显示NPC和地图格候选。

| 审计集合 | 条数 | 含义 |
|---|---:|---|
| 原type56 | 183 | 全量资料，非可玩验收数 |
| 非零AnimationID | 13 | 动画后续语义需分别恢复 |
| 所选额外数值字段为0的元数据候选 | 158 | 过滤口径见下文，不是支持判定 |
| 上述候选中普通mask1有可走格 | 136 | 仅证明目标矩形内存在格，不证明路径 |
| 普通mask1无可走格，mask8有候选 | 22 | 不能授予移动模式、改碰撞或搬移角色 |
| 全零空矩形 | 1 | 102626，不能作为全图目标 |

全183条中160条有mask1候选；其中24条同时带待恢复的额外机制，故不能把160当作本轮普通目标支持数。158条元数据候选中134条原名称含“轻功”，20条有完成对白，15条有DisPlayNPCID。22条普通格受阻的任务里21条原名称含“轻功”，另1条220205的原目标文字明确要求跳上房顶。即使矩形存在mask1格，也不能仅凭该点省略原轻功、任务激活、对白和前后继流程。

元数据过滤仅检查这些数值字段为0：ScenarioInfoAnimationID、ScenarioInfoBranchNpcID、ProcessBarTime、RewardMapJumpType、ActiveInfoNpcID、ActiveInfoTargetID、ActiveInfoTargetNum、ActiveInfoTimeLimit、ActiveInfoGiveBackMoney、ActiveInfoGiveBackPetID、ActiveInfoUseItemID、ActiveInfoOtherType、AIInfoAIID、TransformID、ActiveInfoMaxStep、ActiveInfoMiniStep、QuestionInfoNpcID、TransMinLevel、TransMaxLevel。25条被排除；非零字段分别出现Animation13、Transform5、Jump12、Process1、AI1，集合有重叠。过滤没有把原文本、团队条件或原列表判成可忽略机制。

## 地图格证据的计算口径

只读使用 `world_catalog.maps()` 的当前资源地图尺寸、`maze_grids()` 读取原map.pfs/maze.dat、`world_collision.maze_clear(..., mask=1或8)` 的公开谓词。目标矩形使用原四边各×16；与当前可用地图逻辑范围及移动signed-short上限32768取交集。对177组唯一map/矩形遍历相交格，每个找到的候选均检查 `valid_position`、半开矩形及显式mask谓词。没有mask1候选的22条完成整个交集遍历，而非只检查中心点。

可走格只证明当前资源/地图目录口径下该点满足指定掩码。没有从角色当前位置寻路，没有验证进入目标区的导航、轻功权限、速度、状态生命周期或真实客户端走到该点。mask1/8沿用世界模块已核验的状态选择；本报告不再给状态添加玩法名称。离线审计会读取配置和地图，此操作不能进入网络或每次任务请求路径。

普通mask1受阻的完整ID：220205、221205、221402、221406、221604、221903、222204、222303、222705、222706、222806、222902、222905、222906、223003、223004、223007、223008、223102、223103、223107、223108。逐条位置见JSON，不将候选位置写回角色存档。

## 已实现的 Seam 与调用约束

沿用角色所有者控制任务和资产、地图所有者提供权威位置的架构。任务 Module 集中隐藏矩形单位、类型能力分类、来源指纹、重复意图和完成事务；调用方只提供已经解码的提交意图、可信世界事实、角色身份及既有依赖。共享入口由原始集成窗口接线。

| Interface | 调用阶段与行为 |
|---|---|
| `load_region_resources(task_resources)` | 启动；不可变158定义/25排除、原字段×16矩形及完整原定义指纹；不读取文件 |
| `prepare_region_storage(db)` | 启动；建立task_region_receipts；不放入请求路径 |
| `RegionCommand` | 冻结信封；原TaskIntent、可信Location、generation、task_revision、request/source ID、deadline及定义指纹 |
| `plan_region_completion(actor,snapshot,command,current,resources,regions, generation=...,now_ms=...)` | 纯领域计划；真实当前Location必须与捕获事实完整相等；只完成请求的一条任务 |
| `complete_region_transaction(db,account_id,role_id,epoch,command,current,resources,regions,inventory,...)` | 调用方已有事务；读真实Inventory租约，完成/原奖励/公共后继/effects/来源凭据和消息编码一起成功或回滚 |
| `acknowledge_region_transaction(db,...,intent,resources,regions,inventory,...)` | 当前租约重连确认；必须存在本 Module 的原定义匹配凭据和一致task_effects来源，不能凭历史completed补造到区 |
| 既有 `TaskConversation.resume_messages` | 已加入受支持区域目标；仅恢复已有active bean，state0/value0/key0，不发奖或移动 |

1. 连接所有者沿用已有decoder解析CCommit。仅 `taskID/npcKey0/option0` 可进入本 Module；`CQuestReachScene`、NPC key非0、option非0均拒绝。区域任务不借NPC对白票据。TaskIntent只是意图，不能自己生成权威位置。
2. 角色/地图Adapter在有界所有者流程中取得可信Location，身份包含role、epoch、map实例/分区、位置版本及active状态。构造RegionCommand时任务版本/定义指纹取服务器快照，request/source ID与deadline由服务器信封提供；不从客户端填写。角色/地图须保证命令受理与后续位置变化的先后顺序，不持有对方可变对象，也不加全局锁。
3. 本地时序策略标为designed：受理时捕获Location必须等于传入的当前权威Location；变更版本、实例、loading/frozen、过期deadline、旧generation/epoch、任务版本或定义变化均拒绝。受理事实冻结后，已排队事务按角色顺序兑现；后续移动不反向撤销既已受理的事实。Module不会再次跨所有者同步查询或假称在提交瞬间检查了世界实时坐标。`current`必须是Adapter有来源保证的事实，手工构造dataclass本身不是证明。
4. 在调用方事务中用 `region_reached` 证据进入TaskDomain。证据保存坐标和位置版本，领域重新检查原矩形；region_receipts额外保存完整信封与原定义指纹。继续复用公共奖励渠道，保留原零值、绑定、后继、完成对白、显示NPC；本族额外保留NoteInfo为pending原字段。Task Module不自开连接、不提交、不发送、不改变角色位置或移动模式。原奖励渠道有未确认项仍保留pending，不能把目标已完成称为所有后置效果都已兑现。
5. 编码当前背包及公共完成消息也在事务提交前完成；需要显式钱包和对应奖励规则，编码/资产失败由调用方整体回滚。提交成功后才交连接所有者发送。原生客户端会重复提交首个命中任务：已落盘的同任务重复只确认现有结算，不重新生成来源；request ID改变意图拒绝。过期位置/deadline不阻止确认已付结果，旧租约/代次回调仍拒绝。重连通过专门ack入口读取当前余额，不重发state1，避免重复完成对白/表现。

`supports_static_region`保留25条额外机制的拒绝；在上述数值过滤之外，还拒绝重启计时、步数概率和分支文案/选项。当前原表的158集合与审计候选一致。单边0合法，全零/反向/超出signed32乘16范围拒绝。世界合法位置、碰撞和轻功权限归地图/角色所有者，Module不以离线格候选替代这些检查。

`TaskDomain._completion` 已新增 `region_reached` 分支，TaskEvidence新增region_position/region_version（均有缺省值，不改变旧族字段）。普通对白、battle和scenario完成能力保持原判定。既有 `TaskChain` 已加入静态区域后继：仍只取唯一原边、原等级/角色要求、无未知前置、非周期自环；不跳过不支持节点。已检查原102342→102391的纯续接决策，既有对白链仍在战斗100113前保持pending。循环实例仍待恢复，不用一次性角色+任务凭据重置周期领奖。

## 交给共享集成窗口的具体接线

当前工作区的 `runtime_storage.prepare` 负责任务资源/启动DDL，加入load_region_resources与prepare_region_storage，并将不可变RegionResources交给角色所有者。`runtime_storage` 新Adapter应在原调用方角色事务中调用complete/ack，沿用现有growth/attributes/currency/pet-experience规则和提交后固定宠物key刷新契约；本 Module不重复实现公共奖励渠道。

`game_runtime` 角色命令中现有 `TASK_INTENT_TYPES` 分支先解码CCommit，然后进入师父卡/NPC对白。应在普通NPC票据路径之前识别受支持区域ID与key0/option0；从角色/地图所有者取得并冻结当前Location及任务版本后构造RegionCommand，交有界存储Adapter。历史区域completed用有来源凭据的ack，不重新offer/accept。现有登录 `TaskConversation.resume_messages` 已恢复静态区域，无需再创建平行任务同步器。

**下一次部署应把区域路由/可信世界受理与本批链/恢复源码一起集成**，不能只部署自动续接变化而遗漏完成入口。共享文件本窗口未修改。本批也没有重启已运行的不可变063445Z发布；PID/端口由集成窗口管理，不以本页缓存运行状态。

## 方法、验证与冻结记录

- research：原PFS/原指令为一手来源，区分实际区域CCommit与特定场景空确认，14例原指令探针通过；细节及夹具省略的全局门槛见研究报告。
- codebase-design：将可信世界事实与任务结算放在角色/地图Seam，复用已有公共奖励事务；暂不为每次位置变动引入新数据库连接或全服任务扫描。
- writing-for-agents：上文按启动、意图、事实、事务、发送列出完成条件，候选/实现/部署分开，来源细节通过研究报告披露。
- 冻结阶段仅研究与证据；明确解除后修改task_domain.py/task_chains.py/task_conversation.py、新建task_region.py/verify_task_region.py及本批证据。未写game_runtime.py或其他shared入口、世界/库存模块、policy/catalog。当前运行服由不可变发布副本启动，本批源码不会自动进入该发布。
- `verify_task_region.py`通过：158条原字段/格候选/目标计划，原半开四边；原102391实际公共MapOwner Location和Inventory/AccountStore租约的临时库调用方事务；7500XP；晚期编码失败回滚任务/奖励/效果/区域凭据；重复/过期已付确认不再奖励和state1；旧租约/代次拒绝，新租约ack读取后续已增7XP的当前7507；重叠222609/232803只完成所请求的一条。结果见 [task-region-check.json](task-region-check.json)。
- 旧 `verify_task_transitions.py`、`verify_task_workflow.py`、`verify_task_chains.py`必要兼容检查通过。没有扩展全面回归。未验证：共享受理/路由接线、真实导航和轻功权限、多所有者并发/故障时序、动画/传送后续、真实GUI和在线服。静态158计划并非158条完整实服流程；临时库完整事务本批为原102391一条。

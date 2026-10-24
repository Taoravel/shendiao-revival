# 地图大世界：当前实现、证据与缺口

2026-10-24后续状态入口：所属同址恢复Domain、SQL及旧进程成员精确退休已分别实现；最终Owner d748e058 / RoleScene5bf03c3的11/9/10组与既有5项绿，双轴0，见WORLD_RELOCATION_RECOVERY_HANDOFF/REVIEW和world-relocation-recovery-ready.json。共享缓存、连接及入口政策仍需接线，不能将Module通过计为1627/住宅运行服修复。当前task-pve-20261024T053218Z发布已独立通过原join误撤移动声明的五组反例，见WORLD_RUNTIME_JOIN_CONTEXT_BLOCKER最新节；后文“当前”均属各早期批次，不代替最新精确来源验收。GUI、缺失1302/1307原图、15类特殊入口及全量实体目标继续未完成。

2026-10-23；本地端游1.6.1，网络版本601。按ARCHITECTURE.md划分状态所有权，玩法补全按DESIGN_AUTHORITY.md。以下为当前源码状态，部署与GUI验收分别判断；完整目标仍active。

本轮目录进展见WORLD_STORY_INSTANCE_DIRECTORY_HANDOFF：正式story-instance.1政策下allocate/load caller事务已实现，12组实际临时库/自然角色及受控MapOwner检查通过；共享完整地址路由、真正血手印入场、128加载预算/60秒投影回收和实体冷重建仍未完成。原生定时CHECK到自然STOP现已同对象执行并经当前源码/黑幕修正私有候选的加密Owner保存与重连；该新范围不改变下方各历史批次的原限定。

## 已恢复资料与原生证据

- 原304地图配置中302同名资源可用，308资源目录/maze经CRC校验。1302/1307配置路径缺RMP，另6个目录无配置行，保留缺口。WORLD_MISSING_INTERIORS_RESEARCH新增原资源候选及4处门派/任务顶层引用：1593/1422有相同尺寸与旧内景美术路径，但未证原加载别名，不能计作旧两图恢复。
- 3443原NPC摆放、6275门户格；6175门户通过源/目标资源和边界，223有向连接，临安配置图可达82张。不是82图实测。住宅100个目的点仍越界。
- 全资源执行新增302图临时MapOwner/view生命周期、同模板不同实例隔离和原scene/Move解码；212普通有向跨图代表使用原源格/目标、原DDA局部见证后实际交接。全部6275原goto新鲜PFS逐项等catalog；15组剩余含9组state0目标阻挡、4住宅越界、2same-map特殊入口。公开MapOwner已复现1594/1627同图reserve拒绝，650格尚未恢复，见WORLD_RESOURCE_HANDOFF_AUDIT。该批不是全图原生游玩或5141格逐个行走。
- 7592场景实体、251场景基表、5635怪物模板、4127NPC定义、1440移动时间表；场景实体不都当怪物。5632怪物形象可编码，3个原shape引用缺失。
- 7592条景物已追到原CSceneNpcManager自动按mapid及主角附近各轴576范围创建/回收，详见WORLD_SCENERY_LIFECYCLE_RESEARCH；不应服务器伪造NpcBasic。临安1328条中1293条有原历史日期门槛，35条无日期仍受距离/资源影响。原两表CRC/全属性列表及统计已独立复核；原生命周期仍为静态指令证据，未做函数执行或全图GUI验收。
- CRoleMove/CCheckMove/CRoleStop的5项原marshal fixture通过；最新原持续输入及自然到达链另证CRoleMove/CRoleStop末q64来自Scene+30/+34，本例1100，不是移动时间戳。其他producer/实例高位规则、速度及完整轨迹仍未证明。原MOVE与自然STOP已经隔离发布加密RoleOwner受理、终点落盘/重连保留，见WORLD_FIRST_PLAYABLE_NATIVE_CHAIN；MOVE本身不提前写到目标，原定时CHECK/GUI仍未验。
- 原场景X投影乘1.5、Y不变；边界优先用实际RMP尺寸。NpcBasic等实体原生协议核验及3443摆放批量编码通过；活动标签不能替代模型，怪物模板ID不能直接填NPC配置槽。
- 真玩家RoleBasic/RoleBasicOctets、玩家入屏/移除、SRoleMove/Stop与原handler共13项原生验证通过，见WORLD_ROLE_PROTOCOL。SRoleStop在本映像的处理器为空，不能靠它保证远端停步；门派/扩展属性及实际AOI尚未接线。

详细数量/协议依据集中WORLD_FULL_RECOVERY.md、WORLD_ENTITY_PROTOCOL.md，原始异常保留在对应JSON。

## 领域与共享源码接线

首测新增明确阻断：无章节legacy在当前共享分支intro0且无CG；固定发布实际登录→原decoder/intro/input predicate复现黑幕及移动锁。私有副本无章分支改1后安全检查及两自然新章回归绿，详见WORLD_LEGACY_INTRO_ENTRY_BLOCKER。需主策划确认恢复Adapter、原集成接当前shared/发布/用户验收，不能让用户重复测试未含修正的旧发布。

实例持久化已补 `world_transfer_storage.load_map_instance_transaction/bind_map_instance_transaction`，显式采用后传送的完整地址/位置/journal同事务更新；12组临时DB/实际MapOwner及原必要回归通过。旧档未知实例不猜默认，重连须在新租约恢复事务读取完整地址，见WORLD_INSTANCE_PERSISTENCE_HANDOFF。当前shared按map_id的路由/实例目录尚未接新接口，不能称真实同模板副本或家园重登已完成。

world_owner.MapOwner按MapAddress(map_id,instance_id,partition_id)持有位置及传送状态；独立有界邮箱核epoch、版本和截止时间。预留→冻结→目标loading→持久提交后清源，明确取消回执才恢复源。GameRuntime源码已接线，verify_transfer_runtime通过临时DB的持久交接、旧批次隔离、精确发送屏障和新运行时恢复。普通ready采用scene-transition-v1.json的designed发送屏障，不是原生客户端可见确认。接口和恢复条件见WORLD_RUNTIME_HANDOFF.md。

world_npcs.NpcScene绑定服务端key→摆放→静态NPC，核实例、epoch、版本、范围和距离后输出npc_interacted；不以点击直接发奖励。GameRuntime源码已接真实模型、可信交互及任务对话。verify_npc_task_runtime覆盖加密消息、原生提交、重连和奖励幂等，尚无本批GUI验收。

world_monsters.MonsterScene使用显式普通NPC渲染载体和原怪物shape，没有生产默认载体，不创建战斗数值或修改资产。当前生命周期：

1. spawn→visible。生成和状态变化递增Owner版本；Owner重建有独立generation，旧服务端快照不能误删重生实体。
2. encounter→reserved。BattleOwner明确接受后confirm_encounter→in_battle，明确拒绝后cancel_encounter→visible。超时/取消等待不等于拒绝；已开始不能走取消或普通remove。
3. 可信终局调用end_encounter，显式选择despawn策略，输出原生移除或释放visible；不判断胜负、不选刷新时间、不发任务或奖励。策略仍由来源/主策划决定。

verify_world_monster_lifecycle先复现并修复同键重生版本重置、Owner重建误删，覆盖占用拒绝、接受、旧取消、终局释放/移除。generation保护服务端回调；客户端key本身没有版本，动态键分配/重用、BattleOwner实际接线和持久恢复仍待完成。

## 碰撞接入范围

原maze点查询2893例差分通过；原角色+218状态0→mask1、非0→mask8，经4例真实getter/setter/query布局验证。进场来源现另有37例原codec/Process/成功setter/跳过分支及天气/构造执行：packet+2c严格byte==1归一，普通加载成功后覆盖主角+218；普通0确定mask1，第二byte是CMapWeatherConfig天气。加载失败、空主角、无效配置、reason516023/map1404例外不能默认覆盖，特殊状态业务仍待核；见WORLD_SCENE_MOVEMENT_STATE_RESEARCH。原负坐标向零除16，Owner先核非负/地图边界。

world_catalog.maze_grids()在启动时为302张可用地图加载原网格并校验CRC，返回不可变快照。MapOwner(...,maze=...)和MoveCommand.movement_state已接报文节点阻挡检查；配置maze但未提供可信角色状态时拒绝，不猜默认mask。verify_world_owner_collision证明阻挡拒绝不改位置/不发传送，路径中的阻挡节点也被拒绝；临安原门户计算在禁文件访问时通过。

这是领域接线。当前共享GameRuntime未提供maze和角色movement_state，不能称监听服已阻挡穿墙。节点间原DDA段查询已通过4862项原生差分；普通历史生成/消费与CHECK/STOP另25项原生执行已确认，但也实际复现了合法原移动被重算整数中途段误拒。故没有启用严格逐段拒绝：原DDA允许(25,88)→(73,70)，原engine/current/CHECK报告(60,74)及历史(24,88)，重算却撞格(2,4)。ROLE_MOVE又可能跨多个拐点，不能当授权直线。详见SCENE_GRID_PROTOCOL第五批；verify_world_report_quantization锁住该合法报告仍可被领域接受，阻挡节点仍拒绝，不将该检查称完整连续碰撞。量化感知的权威轨迹协调、特殊模式、速度和实际到达真实性仍待来源/设计；未经完整位置验证的world_movement日志不能直接用于奖励。

位置纠正的新增原生证据见WORLD_MOVEMENT_RECONCILIATION_RESEARCH：23组handler和5组原codec已由世界主窗口独立复跑。SRoleMove改本地主角位置后可能重寻旧目标；SSetRoleLocation虽重设目标并清引擎future，仍可保留角色旧history，之后真实CHECK继续发送该history。部分角色状态还会阻止实际actor位置写入。SRelocateRolePos仅请求CRelocateRolePos回报，特殊模式可报保存位置；SRoleStop为空。因此尚无已验证的无条件“纠正并取消/清历史”原消息，不能以发出包或drain完成代替客户端位置确认，也不能靠此重新启用已撤回的整数段校验。

量化producer进一步区分为current、到达history和初始snapshot头三条；29组原float32边界/同位置三producer/量化反例/wire16别名已独立复跑。current(60,74)不是±0.5，而是投影float32候选[90,91)×[74,75)；初始history24可包含真实25，到达history24则不含25。来源与开闭区间见WORLD_MOVEMENT_QUANTIZATION_INTERVALS；这不是轨迹授权或一格容差，未知producer/特殊态/回绕仍不能靠单一整数段拒绝。

原路径规划首次取得可执行两层Seam：6212f0网格核与6138d0原DDA捷径/短路径压缩，18例已由父独立复跑，见WORLD_NATIVE_PATHFINDING_RESEARCH。原query构造/地图安装、5/7邻居代价、非FIFO的等f heap顺序、阻挡目标失败均执行原指令；kernel不能切角而wrapper原DDA可走某些角点，两者规则不能合并。1920维上限不是命令预算；有界移植及后续上层证据如下，生产接线和参数仍未完成，不据此挪原portal落点或称自动寻路已上线。

后续纯world_pathfinding已实际移植原full-grid核和整数pixel wrapper的第3/6/7参数0分支，包含长路径压缩；2条公共Seam缺方法先红后绿，11组行为、320原核/185原pixel差分及43组合/10真实出生maze路径通过。节点/展开/保守DDA采样预算显式提供、预算不足无半条路径；没有生产调用者，接线见WORLD_PATHFINDING_HANDOFF。原距离完整域736万次后台执行及父66样本/48分支独立支持isqrt和heap更新语义，不把纯规划当实际移动或量化反作弊。

普通点击上层另有WORLD_BLOCKED_GOAL_ADJUSTMENT_RESEARCH的23例，父独立复跑：16像素象限候选、1..8像素局部source（actor不变）、区域byte同值分别确认。当前只执行到11f8800捕获目标或原ret失败，未完成actor整个寻路调用/位置缓存；此前“上层未执行”是研究历史，未因此修改portal或原缺失特殊实例语义。

## 未完成与下一步

| 缺口 | 需要继续完成 |
|---|---|
| 开场黑幕与不能移动 | 已定位intro判别触发Scene+39c黑幕与App+3d8输入门禁，5分钟超时仅去黑不解锁；原CG启动/清理同时解除。EXP字段错误已修正；持久章节和共享运行时按NEWBIE_OPENING_DECISION接线，GUI尚未验收 |
| 新手出生和全流程 | 43路线/333节点原图及10出生点路径已验；师父200xx是武器卡。10车夫真实事务已过，主集成接线后根古墓自然Owner/codec车夫反馈绿，其他派自然链与GUI另验。新租约/按图退役已接shared，根SQL失败及commit后清源失败两支同Runtime恢复通过，见WORLD_CART_TRANSFER_HANDOFF/WORLD_TRANSFER_RECOVERY_HANDOFF；未部署或计全量验收 |
| 碰撞运行启用 | 普通成功进场state来源已原生确认；仍需处理特殊地图/reason、失败/临时电影状态和角色可信快照接线，启动预加载、完整段/寻路与路径列表语义仍待完成 |
| 多人同屏/AOI | MapOwner已补入图/移动/有界出队/离开/换图收尾/ready/取消/旧交接退休与RoleScene同命令发布，容量/原编码失败保持两边；配套输出route→inbox→5份原decoder通过，见WORLD_MAP_VIEW_HANDOFF。目标收件箱独立9组仍有效。尚须生产AOI/元数据政策、shared生命周期及发送前binding围栏、两客户端实机；低位/111新4例否证getter转换，详见WORLD_ROLE_LOW_NIBBLE_RESEARCH，不自行补默认 |
| 出生与暗雷 | 44份monster.dat保留异常；CMineAreainfo只有ID/颜色/描述，原getter/缓存查询24例已独立复跑，raw高值转signed仍无有效关联；正值也跨地图复用。WORLD_ENCOUNTER_REGION_RESEARCH列出关联、重复记录政策、阵容、触发资格及Owner票据5项精确缺口，原出生/遇敌组合/概率仍缺来源/设计 |
| 怪物运行/刷新 | BattleOwner接受/拒绝/终局接线、动态键、出生属性、刷新/掉落按来源及主策划补全 |
| 特殊地图和门槛 | 650同图原入口现已复现reserve拒绝；1594家园625格的成对1..25原dest含义未证，1627另25格。另4住宅越界和9组普通state0目标阻挡，逐项见WORLD_RESOURCE_HANDOFF_AUDIT；住宅/副本实例及坐标变换、等级/任务/战斗限制仍待正确恢复 |
| 部署与客户端 | 源码与deployment.json启动摘要不同；本窗口未重启服务。真实移动、换图、NPC及怪物显示仍须逐项验收 |

本批方法：codebase-design隔开启动资源和热路径，怪物状态输出冻结快照/逻辑消息；tdd在MonsterScene及MapOwner.move Interface按实际失败→实现→通过推进；research追原段查询；writing-for-agents修正早期数量和接线状态。未声称全量已恢复、商业容量已验收或新功能已在线生效。

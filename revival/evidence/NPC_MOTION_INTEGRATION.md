# NPC权威移动与续播

2026-10-23，NPC窗口。npc_lifecycle.py已实现move、途中位置、改道、到达和当前快照续播；原出现/移除Module继续通过。共享MapOwner尚未导入该Module，固定验收发布未变，不代表现场NPC已开始巡逻。

## 证据与补全

原SNPCMoveTo报文/消费者见NPC_LIFECYCLE_INTEGRATION和npc-movement-native.json：20字节、64位key、正signed32毫秒、origin后target，原消费者以target/source/duration写入对象。该证据支持传输与动画时长单位，未证明服务端插值/碰撞策略，也没有执行渲染引擎的完整轨迹。

本批继续追原1201320：目标逻辑点经vtable+c8转换/设置，动画时长经渲染对象虚调用，原字段+11c的更新还含特定NPC倒计时分支。未把该特殊倒计时当通用服务端移动算法。未复制客户端浮点渲染为服务器完整权威。

端游定向检索限定官方sdxl.wanmei.com，关键词NPC移动/跟随/速度/路径/插值与巡逻。[2012战斗规则](https://sdxl.wanmei.com/info/qita/fight/20120729/133541.shtml)支持可见怪物NPC在局部移动；[2015葬剑魔窟介绍](https://sdxl.wanmei.com/news/gamenews/20151125/177821.shtml)提供巡逻侍卫的玩法描述。两者未给轨迹插值或服务器取整；师门“巡逻”也可能描述玩家任务，未拿来当NPC路径算法。同款端游资料未填出该缺口，不采用其它游戏的AI教程。

单一提案来源design/npc-motion-v1.json，明确designed_reconstruction_proposal，需主策划/集成审阅后在启动显式注入；当前共享入口不读取它。规则为按服务器单调毫秒线性有理插值，逻辑像素取最近整数、正好半格向上。实现全用整数，避免累计小步误差；这是重建模型，不能升级为原版动画取整已核验。中途理想线性坐标与该逻辑整数坐标的单轴差不超过半像素，不等于客户端完整视觉误差界。

## Interface与行为

- 启动调用load_npc_motion_rules，再将冻结NpcMotionRules及预加载完整SceneGrid注入NpcLifecycle。未注入rules/maze的静态Module拒绝move，不偷偷加载配置或猜NPC运动模式。
- 冻结NpcMove(entity_key,target,duration_ms,collision_mask)放入NpcLifecycleCommand(operation='move')；原地图address/generation/revision、服务端时钟/期限和请求冲突围栏照旧。origin从同一地图当前权威位置计算，客户端不能提交任意origin覆盖状态。
- collision_mask为可信来源明确选择的0..255原位掩码；不把人物state_byte规则自动套NPC，不把8命名为飞行。起点、终点及完整线段用原生已核验的maze_clear/maze_segment_result检查。稀疏未知格明确拒绝。默认每命令最多64个move、累计65536个像素查询预算为运行工作量设计，不是NPC速度/平衡或商业容量结论。
- move完整校验/编码后一次安装时间线；同一批后续实体失败，前面已算的移动也不会写入。改道从当前像素重基，旧到达取消；原命令重试重发当前实体/剩余移动，不重新开始时钟，后续到达或移除后也不会续播旧路程。
- `view(now_ms=...)`与`interact(...,now_ms=...)`计算当前权威位置；`snapshot(batch_size=...,now_ms=...,entity_keys=...)`发当前NpcBasic再发尚需移动的SNPCMoveTo。entity_keys是可信AOI当前子集，重复/未知key拒绝，空子集为空；选择谁可见留给地图/个人实例策略。
- 存在未结算移动时，view/snapshot必须显式传服务器now_ms；缺省时间明确拒绝，避免接线仍返回旧位置。已经推进的控制时钟不能倒退。原生忽略的origin(0,0)仍不接受为新的移动起点；量化已经到达目标时不发被忽略的零点续播或duration0。
- `advance(now_ms=...)`由地图tick推进，目标在端点时间自然生效，完成计划整理到实体并返回冻结NpcArrival。event_id由generation/原命令ID/key稳定生成，arrived_at_ms为计划端点时刻；只返回一次，不向角色库写任务/奖励。控制命令deadline只约束受理，不取消已经受理的轨迹。到达不发duration0（原客户端会忽略）。

NpcChange.before/after和同图generation仍供AOI与目标连接围栏。读取快照不允许提前传送到endpoint，旧请求回执也不能作为当前坐标。Arrival的持久投递、重启恢复与领域消费由集成/任务状态机处理；Module没有网络outbox或声称事件不会因进程崩溃丢失。

## 接共享入口时的新增要求

先按NPC_LIFECYCLE_INTEGRATION接出现/移除的单一地图权威，再审阅本运动提案并注入。当前唯一shared编辑者仍为原始复原窗口，NPC窗口未改game_runtime/runtime_storage/accounts/serve/gateway。

1. 所有移动地图的spawn/重连快照调用必须带同一轮服务器单调时间，交互也使用该时钟。地图tick调用advance，任务/巡逻订阅返回的稳定到达事件，事件入库和奖励不能在地图Module内完成。
2. AOI和个人阶段先确定可见entity_keys，再请求对应snapshot。SNPCMoveTo是单实体消息，大量移动实体会额外增加消息数；现ConnectionOwner默认128项/1MiB且队满会关闭慢目标。全地图snapshot的逻辑tuple不能未经AOI/批次预算一次塞满连接队列；由集成投递层在地图邮箱之外分批、背压/拒绝并维持generation/场景屏障，不能在地图所有者内等慢网络。
3. 路线/速度/碰撞mask来自可信活动/任务/明雷控制器；当前实现线段验证与移动执行，不会自动寻路，也没有把cnpcwalk固定2015演出改成当前永久巡逻。
4. 新事件触发需同时验证任务实例、角色/地图版本和已消费事件；NPC途中距离合格不等于任务可结算。原人物资源carrier正由主策划统一迁移，本批未动客栈HP/MP，也未新建NPC人物资源账本。

## 验证

verify_npc_motion.py使用真实NpcLifecycle公开Interface和控制用稠密SceneGrid，没有替代dispatcher/碰撞算法。字面检查：1680,5311→1780,5311的1000ms路程，四分之一位置1705,5311；旧位置的角色此时可访、后续走远不可访；当前快照只续750ms，交给原x86消费者确认起点/终点/时长顺序。

后续切片通过：重试不重启；改道重基、旧到达取消；新到达稳定一次；删除期间取消路程；重试旧命令不复活/倒走；内壁阻挡且显式另一个mask维持原位测试；未知稀疏网格/预算/混合批次/畸形字段原子拒绝，失败不占请求；已受理路程超过受理deadline仍完成；只为所选可见实体生成当前presence和续播。一个batch后续无效实体的对照advance无幽灵到达。

补充原地形切片已通过：原临安完整maze544×464、原NPC10000摆放1680,5311，在明确fixture mask1下，左行至1580,5311可通过，四分之一位置1655,5311，原消费者确认续播750ms；相反至1780,5311路线受阻则拒绝。原点在mask1下可行、mask8下不可行，说明不能把任意人物/飞行名称猜给NPC mask。这验证实际资源线段，不代表已核定该NPC原服运动模式或它在游戏中应该巡逻。

verify_npc_lifecycle和verify_npc_movement_native回归仍绿。记录npc-motion-verification.json、npc-lifecycle-verification.json、npc-movement-native.json。新增motion及可见子集的实际红例分别为缺NpcMove与snapshot不接受entity_keys；纵切实现后原检查转绿，其余为逐步补充的对抗验证，不伪称每个已有行为都重新红绿实现。

未验证：原始真实地图全部路线、真实NPC mask语义、原引擎插值一致性、自动寻路/巡逻/跟随、实际MapOwner广播/连接负载、活动/任务事件投递恢复、现场动画与商业容量。补全规则为提案且尚无生产导入，完整NPC目标继续进行。

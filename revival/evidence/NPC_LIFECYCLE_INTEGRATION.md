# NPC出现、消失与移动：当前交付

2026-10-24栏目证据订正：下文column4已穿修理是人工输入栏值后的真实服务器/编码/事务检查，未证明原修理UI实际发4。新原点击尾段确发1/3，发布版Peer对照中3被拒而4仍过旧Fixture；原service2→CNpcSellItemDlg与column4查询正在完整封证。当前不做3→4别名，跨模块调查和未验证边界见NPC_REPAIR_COLUMN_DIAGNOSIS.md，不能据旧绿灯断言原装备窗/商店GUI已恢复。

2026-10-23，NPC窗口。本批新增npc_lifecycle.py、对应验证、已装备修理实际wire检查和仓库关闭检查。未修改game_runtime/runtime_storage/accounts/serve/gateway，未重启验收进程或改真实角色库。

## 已装备修理与仓库钱已接线

主集成已将NPC修理路由接至runtime_storage.repair_role_equipment，并在同事务调用equipment_projection_messages。本窗口新增verify_npc_equipped_repair_runtime.py，原样走完整prepare、认证、连续RC4/原MPPC、实际EQUIP与原CRepairEquipItem(method2,column4)：最终只出现一份完整20项人物map，外攻45/内攻35/加强封印19，HP70/MP40不变，现金1000→960；正常随机成功/失败耐久分别保留，重连map/条件/现金同提交结果。没有替代dispatcher或projection。证据npc-equipped-repair-runtime.json。

主集成也已应用NPC_DEPOT_TYPES分发，本窗口原样复跑verify_npc_depot_money_runtime.py，从原{}红例转绿：实际加密存/取、未开仓/错NPC拒绝、内部同ID重试一次、重连失效旧访问并保留双余额。证据npc-depot-money-runtime.json。主策划另独立检查了票据时钟过期、移动、新线包与内部重试差别，NPC窗口不重复扩大测试。这些仍是开发源码/临时库结果，不代表验收进程加载或GUI。

## 出现/消失Module

`NpcLifecycle`由单个地图所有者持有，替代该地图的静态NpcScene交互状态，不能并存两套权威实体。构造注入原placements、NPCdefinitions（bootstrap时）、只读catalog、地图address、新generation、交互半径和两个容量；generation由地图创建方提供唯一值，不能接收客户端值。没有数据库、后台线程、网络、全服锁或运行中配置读取。

公开Interface：

1. `spawn(bindings,definitions,batch_size=...)`只在bootstrap调用一次，保持原静态Scene调用形状；先完整编码再安装静态状态。
2. `view()`返回冻结NpcPresence列表，`revision`、`generation`和`next_entity_key`供同一个地图邮箱内取控制快照。`control_snapshot(now_ms=...)`一次返回冻结NpcControlSnapshot(address,generation,revision,next_entity_key,presence)，避免跨所有者读可变对象；新key读值尚未预留，由expected_revision防止并发重复消费，原实体删空后也不会回到旧key。
3. `apply(NpcLifecycleCommand,now_ms=server_monotonic_ms)`执行可信spawn/remove。Command冻结address、generation、request_id、expected_revision、deadline、operation、entities、source_ref。spawn实体为冻结NpcSpawn(entity_key,npc_id,x,y)，只允许原定义与有效原地图像素；remove携带现存实体key。
4. `snapshot(batch_size=...)`按当前实体重建入场包。`interact`保持NpcScene的地图/角色epoch/位置版本/范围Interface，并只认可当前现存实体。

spawn用原SAddUserScreen/NpcBasic，remove用原SRemoveUserScreen的第二个q64列表。同配置可有多个独立key，不用只能按config ID去重的ActivityNpc替代。新key在本地图generation内单调增加，消失后不能把旧key分配给替代NPC；新实例内部placement_id另发，不冒充原静态摆放。key分配及source_ref是服务端控制策略，非已证明原服编码算法。

一个命令全部校验与原生编码后才换入状态并递增revision；混合批次失败不消耗实体key/placement/revision/请求凭据。请求凭据有界，已淘汰旧命令仍受expected_revision拒绝。保留凭据内的重复请求只输出当前受影响实体/删除，不执行旧效果：旧spawn在之后remove后重试会回remove，避免客户端幽灵NPC。

NpcChange返回冻结revision、replayed、entity_keys、messages、before、after，保留变化前/后位置，供集成按AOI和既有可见key确定收件人。消息只交目标连接发送泵。此Module没有实现可靠网络outbox或声称恰好一次投递；连接回补应使用当前snapshot/受影响状态，不能重发旧缓存spawn。被删除NPC立即拒绝新的visit；之前已受理的领域事务不由本Module倒退撤销，跨所有者严格撤权另按命令期限/领域流程协调。

### 共享接线要求（只交原始集成窗口）

- MapOwner创建NpcLifecycle并bootstrap，使用唯一map generation和明确receipt_capacity；保留当前静态绑定来源，NPC窗口未擅自加共享容量政策。
- `spawn`邮箱分支改读当前`npcs.snapshot(batch_size=64,now_ms=server_monotonic_ms,entity_keys=trusted_visible_keys)`，不能继续回最初缓存的spawn_packets。静态不传时间可兼容；显式启用运动后缺服务器时间会拒绝，具体要求见NPC_MOTION_INTEGRATION。
- 地图控制邮箱新增可信npc_state/npc_change等实际需要的操作。npc_change在角色参数解包之前收冻结Command，由地图所有者执行apply。客户端CVisitNpc/CNpcService绝不能授权spawn/remove。
- 依现有AOI可见性、角色epoch/场景归属、目标连接generation排队投递NpcChange逻辑消息；慢连接不能阻塞地图。个人剧情NPC须由个人实例/可见性策略隔离，本Module统一地图presence不代表个人阶段已完成，不能直接广播给全地图所有角色。

verify_npc_lifecycle.py通过：原静态NPC移除即撤交互；新原定义在新位置可访；旧key不能复用；generation/地图实例/revision/期限/容量/冲突请求拒绝；同请求混合spawn失败后可纠正再成功；同配置双实例与批量快照；旧spawn重试不复活已删实体；有界凭据淘汰后的旧命令拒绝；无热路径文件读取；另一地图实例独立。实际产出的单/双NPC出现和删除payload均被原x86 decoder完整消费。证据npc-lifecycle-verification.json。

尚未接实际MapOwner广播、任务/活动触发、个人阶段、重启恢复或GUI；不因Module通过而把完整动态NPC玩法标完成。原7592景物由客户端CSceneNpcManager管理，参考WORLD_SCENERY_LIFECYCLE_RESEARCH，不能伪造为这里的服务端NPC。cnpcwalk含2015固定日期的演出，不能无条件在2026循环播放。cnpcdisappearconfig已追到普通CNpc任务/对白离场表现消费者，para为分支相关坐标/文本，不能作为服务器通用消失条件；原执行依据见下节。

### 原消失表消费者补证

NPC_DISAPPEAR_NATIVE_RESEARCH.md及research_npc_disappear.py已独立复跑27例：17个原参数消费者、8个计时/渐隐边界、2个Scene回收边界，四张原PFS表CRC/完整语义一致。普通CNpc的11fcc50只在特定状态/计时条件下执行原getter89dfa0；状态3读取para1文本资源，状态4/5用于移动/台词/离场计时，最后通过alpha及本地容器回收。它与7592景物的CSceneNpcManager分开。

原模式4/5模型移动目标X=para1×24、Y=para2×16，属于该表现调用的精确算术，不能据此改服务器地图坐标、碰撞或全服NPC交互半径。cnpcconfig.hide到对象+258的完整初始化未追通，上层任务资格仅静态链；这些限制阻止把离线状态fixture误作真实任务触发或全图remove授权。research已实际用于保留客户端表现与地图权威两条所有权，不引入自动扫描表删除NPC。未验证GUI、实际任务/广播/重启恢复。

## 原hide初始化与可见状态补证

2026-10-24，NPC_VISIBILITY_INITIALIZATION_RESEARCH.md及research_npc_visibility_initialization.py已补此前原+258来源缺口：真实cnpcconfig.hide loader写bean+108，原getter/table lookup及copy写普通CNpc+150+108=+258。10个原定义覆盖0/1/2/4/5；实际可见setter则写+18并转发两个模型，保留+258。另160例实际执行原switch，第一实参0时hide1调用setter0、hide>1仅caller flag1调用setter0；第一实参1..6且hide>=1调用setter1，其余保留先前+18。参数业务名/完整初始化与渲染未证，不当spawn默认或任务资格。

主窗口在研究者停写后原样独立复跑170例，四产物SHA相同；原27例证据、自有NPC生产模块及鉴定final ready均未变，见npc-visibility-initialization-independent.json。三个原PFS表CRC/全字段列表一致，841个DisPlayNPCID列表仅静态消费者证据，不升级为server显示能力。与当前service audit原hide分布一起，结论是保留原多值模式，不加bool(hide)过滤、不把7592景物映射到CNpc、不撤已单独设计10380/294，也不据state数值直接授权全图remove。实际公共/私有按角色可见性和共享控制仍待精确政策/接线。

## NPC移动原生证据

已新增`npc_move_to(key,duration_ms,origin,target)`纯逻辑消息编码器与verify_npc_movement_native.py。SNPCMoveTo=0xc0fd2，构造daba20、marshal e509c0、unmarshal dabaf0。wire20字节为BE64 key、BE32 duration、两个Pos(i16,i16)，顺序origin后target。

已实际执行原handler11d8170，经原64位key查找（host只提供对应NPC）进入1201320，确认NPC+10c/+110写target，+114/+118写origin，+11c写duration；仅诊断日志与实体查找使用host adapter，字段赋值未替代。原动画把duration除1000，支持毫秒。key高32位、最大signed32时长、边界坐标均经原codec与消费者核对。

原handler遇duration≤0或origin(0,0)直接忽略；服务器codec明确拒绝这些情况。证明范围到渲染虚调用之前，未执行动画视觉。后续已实现显式设计时间线、途中位置与碰撞线段、改道/到达/重连续播，并通过公开Module与原消费者检查，见[NPC_MOTION_INTEGRATION.md](NPC_MOTION_INTEGRATION.md)。尚未共享启用、自动寻路/巡逻/跟随或GUI，不能因codec和Module通过就声称完整移动玩法完成。证据npc-movement-native.json与npc-motion-verification.json。

## 仓库关闭缺口

原CColseDeport（原类名拼写如此）是0xc04fb，body为空，没有NPCkey。构造d8efd0、marshal d8eff0、unmarshal d8f000已执行；原普通仓库关闭按钮10c221a..10c223f发送此消息。npc_depot已提供CLOSE_DEPOT及decode_close，严格拒绝未知附加字段。

verify_npc_depot_close.py在真实Owner复现：开仓→原关闭→仍能查column2，失败为“Native close left warehouse access active”。共享入口需要在RoleOwner收到原包后先decode_close，再清本角色npc_depot_ticket并返回[]；可以在battle/loading门控之前清权限，因为没有资产提交或跨角色影响。畸形body在清权限前拒绝，重复关闭无副作用。可审阅[npc-depot-close-shared.patch](npc-depot-close-shared.patch)仅产物未应用，NPC窗口未编辑shared。接线后同一脚本应转绿并允许重新开仓。证据npc-depot-close-native.json与npc-depot-close-runtime-baseline.json。

## 方法与未验证范围

codebase-design将同图presence、键代际、版本、幂等和交互资格放在单一NpcLifecycle Module；领域资产事务继续由角色所有者控制。tdd先得到缺少生命周期Module、关闭后权限未撤的真实红例，再实现presence切片并保留shared关闭红例，不临时替换dispatcher制造通过。原x86是codec与字段顺序独立oracle；修理wire检查针对已接shared行为补验，未宣称为新红绿实现。writing-for-agents按接线触发、可执行检查和剩余行为区分来源、源码、集成和现场。未验证商业容量、完整NPC服务/全部剧情及现场GUI，目标继续进行。

## 正式首批控制接线状态

接线前读[NPC_LIFECYCLE_ACTIVATION_DECISION.md](NPC_LIFECYCLE_ACTIVATION_DECISION.md)，参数唯一来源design/npc-lifecycle-v1.json。冻结control_snapshot已按公开Interface红→绿，旧快照在remove后仍保持原presence，后取快照准确为空。verify_npc_lifecycle_runtime.py通过真实prepare、认证、连续RC4/原MPPC及原仓库NPC访问后，实际地图邮箱npc_state仍红：共享入口尚按角色参数解包。证据npc-lifecycle-runtime-baseline.json；未临时替换dispatcher。main已收到此红例，可信change及完整投递围栏待按实际契约继续验证。

### 关仓共享接线复核

主集成已按四行补丁最小接入。NPC窗口独立运行verify_npc_depot_close转绿：关闭后column2拒绝、畸形1字节body拒绝且保留有效访问、重复关闭无害、重开恢复。另通过真实加密Peer/RoleOwner入口的loading/battle占用状态fixture确认合法关闭仍撤权且资产不变；此部分仅状态门控fixture，未执行真实战斗或场景交接。前述“仍红/补丁未应用”为原始故障依据，当前源码以本段和npc-depot-close-runtime.json为准；关仓增量现已随npc-close-master-commit-20261023T113819Z/PID44084发布，动态NPC控制仍未接入。

## 严格启动配置闭包

2026-10-24，root已单写npc-lifecycle-v1政策，删除旧interaction_radius32，以interaction_policy=2026-10-23.npc-interaction.2复用原离散格规则。512总binding、4096有界receipt、64批及movement_enabled=false保持设计值；initial_control_source仅来源标签，可信入口由拥有地图的编排注册建立。

NPC所属npc_lifecycle新增冻结NpcLifecycleRules，以及load_npc_lifecycle_rules(interaction_rules,*,path=None)、prepare(accounts,*,path=None)。在npc_interaction.prepare之后调用prepare，挂accounts.npc_lifecycle_rules，保留原npc_resources对象。严格接收root当前revision、512/4096/64、movementfalse、精确initialsource及真正冻结v2对象；旧圆字段、v1/替代对象、缺失或改变的已选参数均拒绝。

main后续唯一共享写者按rules.binding_capacity/receipt_capacity及rules.interaction_rules构造既有NpcLifecycle，generation来自所属WorldDomain.inspect_lifecycle(now_ms).owner_generation；bootstrap及当前snapshot用rules.snapshot_batch_size。interaction_policy为持有对象的只读revision属性，没有第二套公式或半径。movement_rules/maze首批不注入。标签不能替代capability；本次没有增加客户端包、后台入口、调度器、投递层或共享控制实现。

verify_npc_lifecycle_rules.py已保留缺loader及缺prepare两个公开启动Seam的真实红例；当前六组绿、34种非法配置拒绝。实际原临安196条bootstrap四批，显式动态fixture补至合计512，八批当前snapshot；第513条及未激活运动均拒绝且冻结控制快照不变。原数据/规则预加载后禁止文件读取仍能出现、交互和快照，文件后续改变不影响已取规则。旧Lifecycle十一组、v2交互八组及显式v1八组回归绿。原生编解码沿既有Module；合成容量实体不是原内容或商业容量实测。

固定本批两文件增量审查、哈希及状态见npc-lifecycle-startup-ready.json。旧v2审查中的npc_lifecycle字节快照保留为本批base，并非丢失或静默重写历史。共享npc_state/change、可信来源注册、mark_actor_mutation、当前接收者和实际发送围栏仍需main接线及真实Peer验证，不能以startup绿写成生命周期运行时已开放。

方法：tdd逐个公开启动Seam红→绿；codebase-design以持有同一冻结距离对象隐藏配置细节，复用既有生命周期Interface；code-review固定前版已审原字节，Standards/Spec分别审查；writing-for-agents将启动顺序、兼容、来源权限及完成条件共置。未触真人库、运行进程或客户端。

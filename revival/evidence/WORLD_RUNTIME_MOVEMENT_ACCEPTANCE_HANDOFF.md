# 移动投递门槛与准确候选验证

本批使用 diagnosing-bugs 的同一反例红绿链、research 的原始客户端指令证据、code-review 的 Standards/Spec 两轴；审查结果另见 WORLD_RUNTIME_MOVEMENT_ACCEPTANCE_REVIEW.md，未出结果前不声称审查完成。没有修改共享生产模块、运行服务、真人存档或打开客户端。

## 可重复的初始投递反例

`verify_world_movement_delivery_boundaries.py` 在第三个入场消息的实际 Writer.drain 暂停期间，先向真实加密 ConnectionOwner 发送原 C003d ACK，让 RoleOwner.joined=True，并确认不处于 newbie_pending、transfer、battle 或 require_move_start。随后发送真实加密 STOP；所以“旧的未 joined 检查”不能冒充新的投递状态门槛。

历史快照 GameRuntime ccd2bbde…在同一检查中提前接受 STOP，位置从 1006/360,2264 变成 361,2264，版本 1→2 且保存到临时 SQLite，检查 exit1。证据为 `world-movement-delivery-boundaries-baseline.json`。这是真正运行旧代码得到的反例，不是通过削弱断言制造失败。

固定候选 `world-collision-20261023T200906Z` 的 GameRuntime 4ff8b224…通过此反例，详见 `world-movement-delivery-boundaries-exact-candidate.json`。它后来被集成方拒作发布候选；仅保留这项历史通过，不给后继版本转签。

本轮对后继固定候选 `world-collision-20261023T202425Z` 重新独立运行同一检查，GameRuntime e6f8fc93ba9763803e602436e289e3bc2713f5a741317a8cebb744f98b0fc540，报告 `world-movement-delivery-boundaries-r2.json`：发送完成前精确拒绝且位置、版本和存档不变；释放实际 drain 后合法 MOVE/STOP 通过；墙内 CHECK/STOP 均拒绝且三份状态不变；新 epoch 重登与连续加密心跳通过，输入前后稳定。

拒绝的精确理由由真实地图公开邮箱额外观测，生产日志本来只记录 ValueError 类名，因此不要求日志包含异常文本。该额外邮箱调用不伪造上下文，也不替代加密路径的状态/持久化断言。真实客户端是否处理了消息、画面是否显示及点击交互，仍未验证；Writer.drain 不等于客户端执行 ACK。

## 准确候选与全图范围

`verify_world_resource_runtime.py` 新增 --runtime-source/--runtime-harness，以准确候选源目录运行，检查其 manifest.sha256 全部生产文件在执行前后不变，记录实际加载路径与哈希。harness 不得以同名核心生产文件遮盖候选；保留原自冻结 worker 模式及缺 NPC 批次故障检查。

首轮 Spec 审查检出 P2：原 guard 只列七个生产名，runtime_core/world_collision 等可被辅助目录替代，manifest 自身不变并不能排除此事。已实际用临时 runtime_core.py 和 world_collision package 做反例，旧冻结 verifier 会执行非授权 helper；修正后只允许 verify_/research_/diagnose_ 名称的可导入辅助文件/包，并核对每个已加载候选生产模块的实际路径和哈希。共八项旧/新、文件/包反事实通过，记录 `world-candidate-import-guard-verification.json`。inspect_client 保留原资产根，但其 bootstrap 提前导入的 pfs/bxml 在任何 runtime 类加载前重绑到同一候选，避免解析器混源；新路径检查首先真实检出了这一启动缺口，再修正重跑，不扩大为生产运行缺陷。

收紧后的 checker 已在 `202823Z` 候选重新独立执行早到 ACK/墙拒绝与 1006/1404 子集，报告分别为 `world-movement-delivery-boundaries-r3-guarded.json`、`world-resource-runtime-r3-guarded-pilot.json`；每个报告新增 production_imports，明确排除工具性 inspect_client 和已标辅助代码。它们仍不能覆盖下节旧 finalize 的真实红，更不能转为该版本最终发布许可。

旧候选 200906Z 已独立完成全部 302 张可用资源地图：3443 个配置 NPC、294 个原 decoder 批次、每图加密入场/同格合法一步 MOVE/STOP/重连；1442 生产文件与原 map.pfs、config.pfs 前后稳定。报告 `world-resource-runtime-exact-movement-verification.json`。仍有 1302/1307 原图资源缺失；这项验证不证明自然到达、NPC 隐藏条件/朝向、GUI、战斗或全路径碰撞。

后继 202425Z 的全 302 图结果需由该版本自己的检查证明，不能引用 200906Z。世界另以 --maps 1006,1404 做独立普通/特殊入口诊断，输出 `world-resource-runtime-r2-pilot.json`；诊断子集不标全量。

## 投递清理夹具接线

`research_world_scene_delivery_abandonment.py` 原 send_barrier 夹具使用无类型 object/None 编号，不能再触达生产精确类型及 kind/body 校验之后的清理路径。本批改为真实 SceneSendBarrier，并以 ENTER_SCENE=0xc0fa9 与相同 body 排队；测试角色/目录/dispatch/transport 仍为显式 Seam，不将它算作完整真实登录。没有放宽生产校验。

该夹具的 --runtime-source 现在先固定 inspect_client.OUT，保证独立候选读取自身 policy；首次对 202425Z 执行在加载 policy 时失败，属于测试启动路径错误。修正后六例独立通过，报告 `world-scene-delivery-typed-barrier-r2.json`，真实源均来自该候选；待完成投递为零，公开空闲 pin 槽均 64，输入前后稳定。最终夹具 SHA256 dcd55d5caeff335b2d3afb9da7c95ee70f82720bf91c4b6ff025ae0c6011cb73。

## 独立 NPC 方向证据

`verify_world_npc_direction_native.py` 与 `WORLD_NPC_DIRECTION_NATIVE.md` 的原 codec→handler 切片→整个 copier→受测模型分支→actor 向量存储共 19 例已父独立执行。报告 `world-npc-direction-parent-verification.json`，12 项实际源码/原映像/原 map.pfs 输入前后稳定。确认既有 NpcBasic.field_48 是方向来源；受测 CNpc+98=1 分支中非零 1..7 直通，0 则查本地图 npc.xml 首个同配置 ID。

当前 world_npcs.NpcPlacement 已保存原 dir，NpcScene.spawn 尚未传 field_48。NPC 所属窗口可依据此证据补投递，但当前没有修改其生产文件。后续 `verify_world_npc_shape_direction_native.py` 和 `WORLD_NPC_SHAPE_DIRECTION_NATIVE.md` 补证默认11206的model6027/shape3d非空，经原创建前段从毒值写出+98=1，再接方向消费者；父独立10例、14项输入前后稳定，见 `world-npc-shape-direction-parent-verification.json`。该默认模型路径有无override的条件明确保留；其他 shape/actor 分支、完整 CNpc 创建与 GUI 朝向仍未证明。不能把 3443 个已解码配置 NPC 宣称为全部外观和方向恢复完成。

## 新发现的跨租约传送回执缺口

`verify_world_late_finalize_membership.py` 在同一 202425Z 准确候选实际复现：空源重复 finalize 正常，但新 epoch 重新 join 后，历史 finalize 会删除运行时成员缓存；domain 新位置保持，公开 location 却报过期。报告 `world-late-finalize-membership-r2.json` 为真实红，接线归因与共享修复要求见 `WORLD_LATE_FINALIZE_MEMBERSHIP_BLOCKER.md`。未改 shared/domain 或将该红改为允许失败；本批已有其他绿灯不能覆盖此缺口。

同一未改 probe 已在后继202823Z再次真实 exit1，GameRuntime SHA6243c87964301bf2d57e29b84bc81ce2d60b7607279c90582f8d52900cff9095，报告 `world-late-finalize-membership-r3.json`；输入稳定、domain保留、cache清空、公开location过期。共享修复及新准确候选仍待集成方执行，世界没有重写shared。

## 交付范围

共享集成方负责最终新候选、全部发布门槛和唯一启动。世界负责以上可执行证据、领域模块及 NPC 所属接口交接。全量地图/场景/怪物及真客户端验收目标继续保持未完成，不根据本批绿灯缩小目标。

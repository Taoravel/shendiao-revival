# 私有剧情地图：共享接线缺口清单

读取时间2026-10-23 13:10:53 UTC（北京时间21:10:53）。这是**只读源码gap清单，不是固定代码审查或运行时验收**。所有行号指向 `snapshots/world-story-hooks-20261023T131053Z/`，后续共享修改应重新核对，不能按本文宣布当前源码或发布已接好。主集成保持共享文件唯一写者；本窗口未改共享、部署、真人存档或客户端。

`game_runtime.py` SHA256：`338ff6dc1efdd3fb5177c70ff8de7a28108b87b9c9b7c174a6cd451342f86fb8`。其余五份输入SHA/捕获时间见 `world-story-hook-audit-snapshot.json`。AST列举36处`.mailbox.call`并逐一核receiver：30处为地图调用，其余为战斗1处、角色5处；完整行/作用域/operation见 `world-story-shared-hook-audit.json`。

## 统一准入与执行终止

所有下表30处在**排入MapOwner Adapter邮箱前**取得对应完整地址、投影generation的 `ProjectionUse`。源/目标分别持各自pin，不按模板1501合并。同步拒绝排队可以立即释放；成功入队后，由实际命令成功、失败或出队deadline拒绝的终止路径释放。外部await取消/超时不表示终止。

当前 `runtime_core.SerialOwner.call`（44–62）以shield等待reply；取消调用者不会取消已提交命令。`_run`（64–86）才知道处理是否结束，且deadline可能在handler前拒绝。只在MapOwner.handle的finally释放会漏掉这条过期路径，只在调用者finally释放会提前解除仍执行工作的pin。接入可在地图Adapter封装完整调用/终止追踪，或给实际邮箱终止路径接明确回调；保持其余角色、战斗所有者独立，不能以全服队列替代。

## 30处地图调用与配套Seam

| 快照行号 | 原调用与用途 | 生命周期要点 |
|---|---|---|
|284|`target.join`：登录加载后的精确地图加入|当前租约事务核目录后取得实际StoryInstance，load/finish_load后持pin入队；成员cap采用正式私有1。|
|357、378|断线close：目标`ready`，最终当前图`leave`|即使发送泵取消仍须pin；ready不是客户端ready。当前357之后清transfer，但这条close路径没有目标`retire_receipt`，卸载启用前要在已durable事实下补清，否则旧incoming完成回执会永久阻止回收。|
|404、902|首次初始化、换图ready后的`spawn`|读取地图投影也要pin；返回逻辑报文后还要覆盖排队/发送/取消，不能随spawn命令返回就失去全部保护。|
|444、465、486、624|开场授权/结束、卡片、任务的`location`|只读也在真实地图执行器上；持pin到命令终止。后续角色事务另复验租约/快照，不把pin当任务授权。|
|520|原MOVE/CHECK/STOP统一`move_for_encounter`|Adapter邮箱本身必须围栏；domain内建移动队列的qsize不能代表这个SerialOwner队列。产生offer时，domain会保持offer/source成员状态，仍需后续handoff各命令pin。|
|540、571、627、653、730|商店/服务/普通访问、血手印提交、任务接取、仓库的`npc`|当前绑定/位置版本/完整地址由地图复验；距离规则已启动注入不等于生命周期已启用。不能在NPC服务或仓库分支绕过map pin。|
|581|普通车夫`scripted_transfer`|创建offer在源图pin内；之后独立进入handoff，不能只pin目标图。|
|632、643|血手印、章节车夫`authorized_transfer`|两处均含当前角色/任务批准后的源位置，再由源MapOwner建offer；pool不替代批准。|
|787、788、789|目标`reserve`→源`freeze`→目标`activate`|每个实际入队分别围栏；跨Owner await不在池元数据执行器或业务锁内。目标incoming/source departure在后续持久等待期间阻止退休。|
|792、795、799|失败目标`cancel`→源`resume`→目标`retire_receipt`|只有持久cancel成功后的相应清理才能退回执；未知SQL结果保留围栏/待恢复。late cancellation仍绑定原Owner generation。|
|819、820|已提交后源`finalize`→源`retire_receipt`|commit真实成功才清源；IO观察超时不是失败或成功确认。不能提前释放持久决定所依赖回执。|
|860、865|旧租约恢复`inspect_transfer`、`retire_recovered_transfer`|包括完整地址registered_map及883–887候选遍历；只检查现存投影，不能为检查创建空替代。取得对象与入队之间可能卸载，需按地址/generation重新准入。|
|891、895|scene_ready：目标`ready`→checkpoint→目标`retire_receipt`|既有顺序保留：实际存档成功才退目标回执。之后才清transfer/重建索引；发送确认与回收确认分别追踪。|

以上30处在读取快照时都直接调用 `.mailbox.call`，没有pool.acquire/release；域生命周期尚未configure，故当前不会自动卸载。此结论只针对该快照，未主张当前运行服已启用回收。

## 工厂、目录和128加载槽

`GameRuntime.map`（1125–1130）当前以完整MapAddress注册且NPC资源按模板选择，但仍同步创建无上限字典条目。MapOwner构造（100–119）使用成员2048、邮箱64；私有成员1/loaded128尚未应用。`registered_map`（1132–1134）只查现存地址，是恢复的正确区别，但要与池的加载/卸载generation准入组合。

`runtime_storage.prepare`已启动冻结story规则。`prepare_login_map_recovery`（184–201）在当前租约事务load并校验目录，却只返回 `LoginMapRecovery(decision,checkpoint)`；局部entry没有带回调用者。pool.acquire需要真实冻结StoryInstance，接线须把已核entry通过返回合同带出，或在同样可信租约事务Seam取得它。不能用地址或“当前没有实体变更”构造伪目录/伪static_original来源。血手印 `prologue_dialogue`事务已有真实allocate结果，目标加载同样传该记录。

在创建MapOwner、邮箱和资源之前reserve加载槽；等静态原投影完整建立并在自身执行者取新鲜空快照，才finish_load。读写配置、数据库、资源或构造失败/取消时，cancel_load只请求取消并继续占槽；原加载工作终止且已创建邮箱/资源清理完成后，finish_load_cancel才释放。超时后重建同地址会造成两个Owner，应继续核同一load ticket。全部外部回调装好后才configure_lifecycle；老对象已有成员时不能补开以遗漏历史投递。

## 场景发送：成功、丢弃和泵退出

当前SceneMessage/SceneSendBarrier（70–86、840–842）只追踪ENTER_SCENE发送后触发角色scene_sent；`ConnectionOwner._send`在writer.drain完成后（1021–1025）调该角色入口，再由scene_ready操作目标。它不是domain的SceneDeliveryTicket，也没有begin/finish_scene_delivery接线。

需要在目标MapOwner执行器登记begin_scene_delivery，绑定当前Location、connection generation和独立request，再把不可变ticket随逻辑报文/批次交连接所有者。相应投递全过程保留ProjectionUse，直到真实成功或明确取消的finish_scene_delivery命令也终止，避免pool先进入unloading而挡住清理回调。初次登录ENTER_SCENE（293–295普通tuple）、首次/换图spawn也纳入明确的场景批次生命周期；它们不能仅靠当前带barrier的普通换图分支覆盖。

当前下列退出路径都要有明确取消处理；取消只解除发送占用，不调用scene_ready冒充发送成功：

- `offer`（994–1006）：closed/旧epoch早退、帧数或字节容量满返回false，尚未入队的ticket由可信调用者结束。
- `_send`（1014–1017）：closed或旧epoch取出后丢弃；finally目前只清字节/queue计数。
- drain失败/超时、scene_sent被旧租约拒绝（1020–1032）：确认这个发送任务终止后结束其ticket；已发字节但未知客户端效果不等于ready。
- `close`（1076–1088）：取消并等待pump，然后disconnect；队列里尚未出队的场景ticket也逐一取消。只取消pump不会消费剩余队列，未登记ticket将泄漏。
- pump已shield等待角色scene_sent时被取消：该角色命令可能仍执行，保留它的真实终止追踪和子地图命令pin，不能按外层取消立即释放全部工作。

新连接或request复用须保留delivery_id/map generation；旧完成不能清掉新投递。每图scene投递容量64与每连接128帧/1MiB属于不同预算，满载按既有拒绝/断线策略清理，不临时扩大池限制。

## 空闲卸载、动态实体和停机

快照中没有回收调度器，也没有配置domain生命周期、标记动态actor、inspect/retire/final unload的共享命令。补齐全部入口后，池先检查最后pin释放后完整60000ms并begin_unload；地图执行器再查成员、incoming/departure/offer、内队列、发送及actor pristine，自身也完整空闲60000ms才retire_idle。明确拒绝后以同一Owner新鲜非退休快照cancel_unload；未知结果保持unloading，不能复活对象。

退休成功后先隔离原generation的工厂/registered_map准入，排空并真正终止原Adapter邮箱及清理资源，再完成卸载计数/移除该精确注册，避免新对象与尚在执行的旧对象重叠。实现的具体清理阶段须保留128名额直到旧投影真实终止；目录与角色存档不删除。重建保持目录地址，地图generation变化。

`GameRuntime.close`（1272–1277）目前直接遍历maps关邮箱。接回收后应先停止新load/unload准入和回收调度，再排空连接场景ticket、角色/地图任务及取消中的加载，最后关IO；防止close与定时卸载双清。NPC/怪物后续任何动态变更在所属地图上mark_actor_mutation，动态持久状态未实现前不允许标为static_original冷重建。

## 接入完成的可判定反馈

主集成修改后用真实GameRuntime/SerialOwner/连接队列验证：排队及deadline拒绝、调用者取消但命令仍跑、load取消仍占128槽、慢发送/旧epoch丢弃/queue满/close剩余ticket、断线ready回执清理、同地址卸载后新generation拒绝旧回调、两私有地图独立推进，以及自然血手印和冷重连。生命周期18组只证明所属领域合同，不能替代以上共享路径。已自然完成两角色血手印也不能反推pool已接。

方法：codebase-design按工厂/目录、地图执行、连接发送和角色事务分列Seam；diagnosing-bugs以真实SerialOwner取消语义核对超时；writing-for-agents把接入点和失败退出条件共置。AST清单与源快照可重查覆盖，但没有执行新的共享运行时测试。

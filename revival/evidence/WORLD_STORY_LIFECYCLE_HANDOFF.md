# 私有剧情地图：加载预算与安全卸载

2026-10-23。依据 `NEWBIE_BLOODMARK_INSTANCE_DECISION.md`、`design/story-instance-v1.json`。新增 `world_story_projection_pool.py`，世界领域 `world_owner.MapOwner` 增加显式生命周期接口；目录库 `world_story_instances.py` 本批仅追加启动冻结的运行预算字段，初版身份/SQL合同不变。共享 `game_runtime.py/runtime_storage.py/accounts.py` 未由本窗口改动，未部署或开游戏。

## 接入顺序

1. 每进程由一个元数据所有者持有 `StoryProjectionPool(rules,pins_per_projection=rules.pins_per_projection)`。目录启动loader已严格冻结新政策的pins_per_projection=64、scene_delivery_capacity=64；缺失、bool/float或非64拒绝，加入只影响运行预算，不改变身份revision/命名空间/旧记录。测试可显式使用更小pin预算，超过发布上限拒绝。它只处理有界内存元数据，不持有MapOwner可变对象，不执行玩法/资源/SQL/网络工作；各地图仍独立推进。
2. 当前角色事务核目录身份/租约后，将冻结 `StoryInstance` 交给 `pool.acquire(record,request_id=...,deadline_ms=...,now_ms=...,actor_state=...)`。新加载返回 `ProjectionLoad`，既有加载成功返回 `ProjectionUse`。加载中其他请求局部拒绝，原请求同期限可幂等重取；不延长原授权。loading/loaded/unloading均占名额，上限128，满额拒绝新加载而不阻塞既有地图。
3. 在元数据执行器外创建精确地址MapOwner，资源按map_id1501、成员capacity=rules.member_capacity=1。完整回调装好后，启动调用 `configure_lifecycle(scene_delivery_capacity=rules.scene_delivery_capacity,actor_state='static_original')`。随后在地图执行器上 `inspect_lifecycle(now_ms)`，再 `pool.finish_load(load,snapshot,now_ms=...)` 得到首个use pin。**观察超时只能请求 `cancel_load(load)`，返回ProjectionLoadCancellation且仍占槽**；只有原加载执行器明确终止并完成其资源清理后，才向元数据执行器确认 `finish_load_cancel(cancellation)`。重复取消返回同ticket，取消中拒绝acquire和迟到finish_load；未知执行结果保留槽位。未开始的加载也由加载调度器明确确认取消后释放，不由await超时推断。
4. 每个排队/执行中的跨Owner操作，在投递前持有 `ProjectionUse`，真实执行完成后 `pool.release(use,now_ms=...)`；异步等待在pool元数据调用之外。调用方等待超时/取消不等于命令已停止，pin必须留到原地图执行器明确完成/撤销，不能在外层awaiter的finally里无条件释放。相同未释放request重取同pin，释放后重用request会得到新use_id，旧回调不能释放替代pin。所有地图Adapter邮箱路径（含join、reserve、handoff、NPC和场景回调）均需接此合同；不能只包移动队列就宣称排队交接已围栏。
5. 开始卸载用 `begin_unload(handle,request_id=...,now_ms=...)`。有pin或最后一个pin释放后未满60000ms均拒绝；成功后新acquire拒绝。随后目标地图执行器取得新鲜快照并 `retire_idle(snapshot,now_ms,minimum_idle_ms=rules.idle_unload_after_ms)`，地图自身从首次全空观察起也须满60000ms。两层都用可信服务器同源单调时钟，排队操作刚结束不能借地图旧idle计时提前卸载。成功返回不可变 `MapRetired` 后，**保持pool unloading名额，先关闭原Adapter邮箱、等待实际任务终止并清理其资源；确认清理完成后才调用 `finish_unload(ticket,receipt)`**，验两层完整空闲及retire时序并释放槽。清理结果未知或仅外层await超时继续占槽，同一receipt保留供原卸载工作完成，不恢复已退休Owner。工厂只移除精确旧generation的注册；目录/SQL位置/持久回执不删除。
6. 若地图明确拒绝退休，取得该Owner的新鲜非retired快照，调用 `cancel_unload(ticket,live_snapshot)`，恢复可用。观察超时/失去响应保持unloading围栏，重新核同一Owner；不能凭超时取消或重建。已经retired的Owner只能完成卸载，不能取消复活。取消后重试产生新unload_id，旧取消/完成不能作用于新尝试。

pool的Actor状态入参是可信恢复事实，**不是客户端自报或从空目录推断**。当前只允许 `static_original` 冷加载；动态未持久或unknown拒绝冷加载。已加载且仍活着的动态投影可以继续取得操作pin，MapOwner的dirty标志仍阻止卸载。尚无动态实体持久恢复实现；共享Adapter必须在动态变更前完成其持久状态设计，否则不能启用这些变更或在崩溃后宣称仍为static。

2026-10-23顺序补正：上面第5步取代早期“先finish_unload释放槽、最后销毁Adapter”文字。pool不持有或观察实际Adapter，finish_unload是可信调用方在真实清理结束后的确认；只拿到MapRetired不足以证明外部执行器/资源已经终止。本次只修正接线顺序，不改领域代码或公开参数，不用旧18组冒充共享关闭/清理验收。全部共享入口清单见 `WORLD_STORY_SHARED_HOOK_AUDIT.md`。

## 地图所有者的退休条件与投递追踪

`inspect_lifecycle(now_ms)` 返回不可变MapIdleSnapshot，来源是实际成员、incoming、departures、offers、内建移动邮箱和已登记场景投递。任何一项非空、未启用生命周期、动态actor非pristine都会拒绝退休。已完成的传送回执也先保留为busy，直到运行时按原合同确认已durable并调用既有 `retire_receipt`；不因“不是Reservation了”自动丢弃。

新 `begin_scene_delivery(current_location,connection_generation=...,request_id=...)` 在地图执行器登记服务器发送屏障，支持active/loading成员；必须在异步投递前登记。成功发送或明确取消后，向同一地图Owner投递 `finish_scene_delivery(ticket)`。ticket带完整位置/租约/连接、owner generation和独立delivery_id；待处理同request重试幂等，完成后重用request得到新delivery_id。旧连接、旧generation、旧替代ticket不能解除当前投递。离开地图不会隐式抹掉未完成的发送。这个确认是服务器发送/取消结果，**不是客户端加载ready ACK**。

`mark_actor_mutation()` 将已启用的Owner标为不可冷卸载，没有内存“恢复pristine”入口；它不代替动态实体的持久快照。旧Adapter默认未启用生命周期，因此本批不会让当前共享运行时自动开始GC。不能在成员/交接已存在后补开生命周期来遗漏此前未追踪工作。

退休与并发producer enqueue使用一把**每地图独有、只覆盖非阻塞队列/退休标记**的短门禁；不在其内做玩法、I/O或跨Owner等待。地图执行器内join/reserve/move串行；退休后旧对象拒绝join/reserve/移动及后续enqueue。pool先挡外部排队请求，MapOwner再挡本地邮箱，两个层次不能互相省略。

## 实际执行与范围

`verify_world_story_lifecycle.py` 通过18组：60000边界、默认禁回收、join/leave ABA、队列、发送屏障/连接/替代ticket、动态dirty、预留/冻结/回执、128槽及取消等待执行终止、最后pin的60000计时、卸载重试代际、retiring拒绝新获取、同地址新generation、动态热用/冷拒、真实目录保留和32次并发producer/retire；另实跑新64/64规则字段与8个坏政策值、65pin超限拒绝。竞态实际观察到“入队先成功→退休拒绝”和“退休先成功→入队拒绝”两分支；它不是任意线程调度的形式证明或商业压测。

真实目录循环自然创建1角色，经实际加密Owner完成匹配开场，公开目录事务分配；空投影卸载后公开load仍读原记录，重建保持完整地址并换地图generation。它没有执行血手印任务、私有场景入场、NPC/怪物渲染或人物进入/退出实例，不能替代完整新手流程。

同批回归已跑：原MapOwner、移动邮箱/view、目标ready/finalize/view、恢复/view、完整实例持久化12组、持久目录12组、302图生命周期与212普通跨图代表。最后的场景delivery_id增补在18组中独立红→绿；此前原MapOwner核心join/submit/reserve改动已完成上述回归。

TDD红→绿包括：退休/投递/池入口缺失；旧卸载取消误作用于新尝试；动态热用被错套冷加载限制；bool租约别名；同request旧场景确认误解新投递；Spec轴发现加载超时提前释放实际工作槽后实红→增加取消中及真实清理确认；最后操作pin释放后立即开始卸载实红→独立保守空闲计时；新64/64字段缺失/超上限构造实红→启动冻结/约束。codebase-design保持目录身份、池元数据、地图玩法和连接发送分别唯一所有。writing-for-agents集中调用顺序与未验条件。

尚未接共享完整地址路由和全部外部邮箱/pin/scene hooks，尚无动态实体持久快照或实际进程冷启动恢复，未做GUI与商业容量验收。政策允许的完整目标仍未达成。

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_story_lifecycle.py
```

报告 `world-story-lifecycle-verification.json` 含实际组数、竞态分支、目录循环、五份执行前后稳定源哈希。接入者须先通过这些公共反馈，再按完整任务纵切/共享/客户端逐层验收。

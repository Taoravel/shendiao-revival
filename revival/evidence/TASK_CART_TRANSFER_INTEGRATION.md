# 新手车夫完成与世界目标的同事务 Interface

2026-10-23。已按 [NEWBIE_CART_TRANSFER_DECISION.md](NEWBIE_CART_TRANSFER_DECISION.md) 和政策 `design/newbie-cart-transfer-v1.json` 实现 `task_cart_transfer.py`，新增领域事件 `newbie_cart_transfer_committed`。十条独立模块临时库检查已通过；随后主集成完成共享接线，主策划的自然GameRuntime车夫检查独立转绿，见 [newbie-cart-runtime-verification.json](newbie-cart-runtime-verification.json)。包含真实角色/连接所有者、原clear移动报告、场景原decoder、精确发送屏障和后续合法移动/重连；**仍是临时库，无真实GUI/在线服操作。** 本窗口没有修改shared、世界/库存实现或主策划自然verifier。

## 启动与冻结命令

启动先沿既有流程加载TaskResources、NewbieChapterRules、MasterCardRules和 `task_cart_dialogue.load_cart_resources`，再调用 `load_cart_transfer_rules(cart,catalog,grids)`。它读取唯一车夫政策、验证十条原分支/各自原坐标，采用政策×16解释到嘉兴(576,3536)或(1136,3872)，校验地图范围与state0/mask1可走。解释仍为inferred，采用配方为designed，不升级为原服精确落点事实。返回只读CartTransferRules；请求路径不读配置或地图文件。

启动DDL在既有存储准备中调用 `prepare_cart_transfer_storage(db)`，世界表由 `world_transfer_storage.prepare(db)` 自行管理。任务 Module只读写自己的task_cart_transfers及公共任务效果；不复制world_handoffs/role_positions SQL。

角色当前有效的 `CartTransferIntent` 沿已有两段Interface获得：真实ActiveNpc证明→`open_cart_dialogue_transaction`→同任务/实体key/option0的CCommit→`authorize_cart_transfer_transaction`。资格保持独立completed章节、原师父选择卡凭据、精确获领实例装备任务completed、车夫active。少林BranchNpcID错配继续保留，不改源表或NPC。

纯 `resolve_cart_transfer(intent,cart,rules,movement_state=0)` 返回冻结ResolvedCartTransfer。仅接正常移动状态0，不找附近点或替换原路线。RawCartDestination仍保存原字段并标unresolved；只有这个政策Adapter产出的target_position可交世界，而不是把原36/221直接当逻辑像素。

## 调用方事务接入顺序

1. 在角色与源地图所有者有界流程中保存被接受的冻结intent，其稳定request_id就是传送ID。先把该source的当前坐标与版本通过既有公开checkpoint路径落盘并围栏后续源命令；不能在结算时偷偷放宽到旧坐标。本入口使用世界commit默认的**精确持久源检查**，不传allow_source_checkpoint_lag=True。
2. 世界所有者依次 `prepare_transfer`→目标reserve→源freeze→目标activate，得到TransferCommit（目标loading）。世界 `begin` 记录相同offer及其原deadline为prepared。任务没有因这一步完成。源Location、request_id、目标map/坐标、deadline、frozen/target版本与拓扑必须逐项相符。
3. 调用方打开一个当前租约角色事务，调用：

```text
complete_cart_transfer_transaction(
    db, account_id, role_id, epoch, task_resources, cart, cart_transfer_rules,
    accepted_intent, world_target_receipt, inventory,
    generation=current_generation, now_ms=trusted_now, movement_state=0,
    growth_rules=..., attribute_rules=..., currency_rules=...,
    pet_experience_rules=...)
```

   **此组合入口内部调用世界公开 `commit_transfer_transaction`，不要在它之前另行提交世界。** 它在同一个外层db事务验证/写世界决定和目标位置，再完成车夫、公共原奖励、唯一原嘉兴后继及任务/资产/传送凭据。若世界已经单独committed却没有任务凭据，入口拒绝，不悄悄补发任务来掩盖拆分事务。未初始化规则/钱包、背包或消息编码错误均由调用方回滚。
4. 函数返回冻结CartTransferResult：transfer_id、task_id、原loading target、completion、预编码基础messages和replayed。**基础completion来自公共TaskWorkflow，其growth full-map可能是裸身，不能直接作为最终已装备角色消息投递。** 共享存储Adapter仍在同一个db事务内调用已有 `_project_completion`（或其统一公开后继），从当前Inventory snapshot/成长/显式装备基线取得最终EquipmentRoleSnapshot；替换completion.attributes和growth_messages，再通过公开 `cart_completion_messages(projected_completion)` 重建任务消息，并与当前 `inventory.equipment_bag_messages(db,epoch)` 组合，替换原result.messages。不要在旧裸身full-map后追加第二份总值map；最终普通属性刷新只留一份当前20项完整map，包含加强封印1230。
5. **仍在这个外层事务内**使用共享 `_role_profile_transaction` 的同一最终growth/attributes读取并编码目标场景body及全部原生结果；RoleDetail的装备索引8/12/14、五维和潜能取同源profile，HP/MP/伤势保持当前vitals，不能拿旧login缓存或裸身snapshot。场景body必须在COMMIT之前编码好，不能提交后才首次调用world encoder并吞掉失败。沿公共固定宠物key的提交后刷新契约处理宠物。调用方任一步失败必须回滚，不能捕获异常后提交部分结果。提交后才发布角色缓存/目标归属、源finalize、向正确connection/generation排队发送；目标ready沿scene-transition-v1精确发送屏障，不用任意延时或假客户端回包。

共享Adapter内部顺序契约（示意，不是本窗口对shared的补丁）：

```text
BEGIN current leased role transaction
result = complete_cart_transfer_transaction(db, ...)
completion = shared_current_equipment_projection(db, result.completion, ...)
profile = shared_current_role_profile(db, ...)
messages = current_bag_messages(db, ...) + cart_completion_messages(completion)
scene_body = original_world_encoder(target, growth=profile.growth,
                                   attributes=profile.attributes, ...)
validate/encode every final role + scene + task message
COMMIT
publish current profile/target ownership; source finalize
enqueue exact batch to current connection; target send barrier -> ready
```

上面shared_current_*对应shared当前统一 `_project_completion`/`_role_profile_transaction`，由原始集成方在所属文件中使用，不要求任务Module导入shared私有实现。`cart_completion_messages`保留首次完成state1和原后继state0，重试按completion.replayed省去state1。十条原车夫ExpReward都为0，保留0；完成效果保留原RewardMap字段，并另记政策/世界收据指纹、resolved transfer字段及durable_target_loading，不伪称客户端ready。

源被冻结、目标已loading而事务失败时，持久决定仍为prepared/持久位置仍为源；本 Module不越权解冻或取消地图。依主策划政策，只有得到世界安全取消收据后恢复源；无法确定时围栏角色并从持久决定恢复，避免双归属。提交后发送失败则保持目标唯一持久权威，不能按发送超时回源。

## 重复、旧连接与重连

发版前规则指纹已排除三个纯进度字段 `implementation_status`、`native_gui_verified`、`live_server_changed`，后续仅更新这些字段不使历史车夫确认冲突；其他字段仍全部参加指纹，业务授权/坐标/提交/版本变动继续拒绝旧回执。实际启动Interface的临时政策检查已确认这两种区别，最终当前指纹为 `ec64d05568ea9ff6eeba1eccfa658b2fb7535f0b82723391079f2dfa24c56dbf`。这是未部署车夫版本的发版前修正；没有重写已有已付回执或猜迁移，后续实装进度统一记入主策划决定文档。

同一当前租约/generation的已付intent+原目标receipt重试要求完整指纹一致，世界公开commit返回False，证明原committed/ready收据匹配且不再次写位置。返回当前余额/背包并省去重复state1；即使任务之后人物已有更新位置，也不会被旧receipt拉回落点。首次受理的deadline不阻止已付确认。改变request_id、章节、源、定义/政策或receipt的重试拒绝，客户端重复包不自动铸造新传送intent。

旧epoch/generation调用即使任务已完成仍拒绝；不能把旧源Location换个epoch重新拼装成新世界receipt。新登录正常加载现有role_positions/position_versions和任务journal，恢复原嘉兴后继及当前位置，历史车夫不重新offer或领奖。这条重连是读取持久状态，不重放旧epoch的写接口；若后续要新增跨租约“历史传送ack”函数，必须消费世界专用只读决定Interface，不能自行复制世界SQL。

共享接线位置：启动 `runtime_storage.prepare` 加载规则/DDL；角色NPC菜单进入普通对白前试图打开当前车夫；原TASK_INTENT_TYPES分支在普通NPC plan_finish之前消费已保存的车夫ticket和已接受的intent；新增存储Adapter用上述组合入口。目标场景/角色快照编码、缓存发布和精确发送屏障仍由原始集成窗口负责。该窗口可以直接采用本Interface，无需新增策略审批。

## 本批方法与必要验证

codebase-design把原坐标政策、可信分支授权、世界持久化与公共奖励放在各自Module，通过调用方事务组合，隐藏共享路由和世界SQL。research前批原包/指令与官方窄检索的证据保留在TASK_CART_BRANCH_RESEARCH/INTEGRATION；writing-for-agents将启动、受理、事务、发送及两种失败恢复集中描述。

`verify_task_cart_transfer.py`已通过，结果见 [task-cart-transfer-check.json](task-cart-transfer-check.json)：

- 十条路线各执行实际独立创建章节/原intro结束、真实NpcScene师父proof、原选择卡取实际武器、实际精确实例equip/type59完成，再访问真实车夫proof并取得冻结intent。
- 实际源/目标MapOwner预留→冻结→loading与世界公开caller事务结合；车夫完成、唯一60001后继、原0XP和实际物品保持一致。
- 错误选项/章节/旧源版本/任务版本/generation/期限/移动状态/receipt、缺世界prepared拒绝。
- 启动载入实际替代政策，三个纯进度字段变化保持规则指纹/落点；授权契约变化产生新指纹。按新源码重跑十路线独立必要事务检查通过，root自然链脚本保持原样且未重复执行。
- 首路线晚期背包编码错误、第二路线组合返回后的调用方场景编码错误均回滚世界目标/决定、任务/奖励/效果与本Module凭据；同收据重试成功。
- 提交后源清理、目标ready由测试显式驱动（并非连接发送屏障实测）。后续checkpoint不被重复收据覆盖；额外+7经验后确认读取当前余额；省去重复state1，拒绝新传送身份；新租约回读后继/当前位置，旧租约回调拒绝。

本窗口十条测试中的NPC位置为直接可信夹具，未宣称自然行走；没有当前服务、真人角色、GUI或实际战斗。root的自然GameRuntime车夫verifier保持独立且已另行转绿，上方报告覆盖共享场景包/精确发送屏障/后续移动和当前装备投影，不由本窗口十条事务测试替代。

后续世界公开恢复Interface已由shared接入，主策划独立故障检查也转绿，本窗口已读取实际报告： [cart-scene-atomic-runtime-verification.json](cart-scene-atomic-runtime-verification.json)确认自然车夫末端场景编码失败整体回滚、同Runtime新租约回源并重新出发；[cart-committed-recovery-runtime-verification.json](cart-committed-recovery-runtime-verification.json)确认真实持久commit后清源失败，新租约同Runtime退役旧Owner/Adapter缓存并保留嘉兴目标/唯一任务回执/45/35/8。恢复顺序以 [WORLD_TRANSFER_RECOVERY_HANDOFF.md](WORLD_TRANSFER_RECOVERY_HANDOFF.md)和主策划决定为准；本窗口没有重跑root脚本或改世界/shared。故障是提交/清源注入，未宣称真实socket断网、GUI或分布式容量验收。

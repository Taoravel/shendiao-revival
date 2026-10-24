# 世界交接提交：新手车夫调用方事务Interface

2026-10-23。实现已稳定交付；源码入口world_transfer_storage.commit_transfer_transaction。本批不修改game_runtime/runtime_storage/accounts/serve/gateway、不可变发布副本、8724进程或真实角色。目标解析已经由任务所有者的task_cart_transfer按同一newbie-cart-transfer-v1政策实现，世界侧复核并使用它，不再创建第二份换算实现。

## 启动和坐标

1. 启动持久化迁移调用world_transfer_storage.prepare(db)，在现有world_handoffs新增offer列，按完整TransferOffer保存source/target/deadline/transfer_id身份。所有DDL只在启动执行。已有committed/ready记录仅能从完整原receipt恢复offer，逐一核对原transfer_id/role/epoch/source/target；无完整凭据则拒绝猜测。旧prepared记录无法恢复deadline，保留offer空，不能继续提交；新租约恢复/明确取消后重新授权新请求。迁移前按原集成部署规范备份。
2. 启动目标校验使用task_cart_transfer.load_cart_transfer_rules(cart,catalog,grids)；调用resolve_cart_transfer(intent,cart,rules,movement_state=0)得到冻结ResolvedCartTransfer。十条原任务各自的原坐标乘16，两个结果为(1006,576,3536)/(1006,1136,3872)，仍明确inferred单位解释与designed采用；state0/mask1检查，不搜索附近点。已核对该Module与主策划政策，不改原任务字段或另加坐标默认。

## 提交顺序

1. 角色所有者在当前租约下，将最新有效源位置/版本完成检查点，再取得或重新核验匹配当前Location的车夫ticket/intent。不能给过期ticket换贴最新版本。新车夫接口默认要求持久源map/x/y/version与offer.source精确相同。
2. 按稳定intent.request_id、intent.source、resolved.target_position、intent.deadline_ms调用MapOwner.prepare_transfer，world_transfer_storage.begin登记完整offer，再目标reserve→源freeze→目标activate获得精确loading TransferCommit。地图状态仍遵循独立MapAddress所有者，不能用一把世界锁代替。
3. 打开一个当前角色租约事务。任务入口complete_cart_transfer_transaction内部调用以下世界公开Interface，组合本任务/原奖励/唯一后继。**不要先独立调用world_transfer_storage.commit再完成任务，也不要在同一事务先调用世界helper再调用任务入口。**

```python
commit_transfer_transaction(db, account_id, role_id, epoch, receipt,
                            *, allow_source_checkpoint_lag=False) -> bool
```

db必须已经in_transaction；函数不自开连接、不BEGIN/COMMIT/ROLLBACK、不做DDL、不发网络消息。即使传入普通SQLite连接，它也自己校验当前角色账号归属、有效租约和未删角。严格核TransferOffer→Reservation→FrozenTransfer→loading Location的角色/epoch、实例、原位置、版本+1/+2、状态及目标；journal中的完整offer（包括deadline）必须逐项相同。

默认False禁止旧检查点、未知位置或缺半张位置记录；相同版本却坐标不同、新于源版本、错误地图均在写入前拒绝。True返回仅表示本外层事务已写目标位置/版本与committed决定，仍未证明外层提交。False仅表示同一完整receipt已经committed/ready，不重写坐标；当前持久版本必须不低于该receipt，相同版本坐标也须一致，较新合法位置保留。它不是重新设置角色Owner缓存的许可。

4. 同一外层事务内预编码任务、背包/最终属性及目标scene_entry，再由调用方提交。提交成功才发布角色快照、source.finalize/退休收据与既有目标精确发送屏障；该屏障不是客户端可见ACK。提交前异常由调用方回滚全部SQL。目标已loading而没有安全取消回执时，围栏并按持久决定恢复，不凭超时解冻源。提交后网络失败保留目标唯一持久归属，重连读取当前位置与完成凭据。

## 旧门户兼容范围

原独立commit包装器改为同一事务调用本helper，显式传allow_source_checkpoint_lag=True，保留旧门户异步检查点尚落后的兼容行为。它仍核已知同版本坐标、较新版本/错图、完整offer与receipt、当前租约。仅该显式旧Adapter允许两张位置记录都未初始化的原legacy情形；只有一张缺失仍拒绝。这个选项不适用于新车夫、任务、服务或奖励入口，不将其推广为源位置验证政策。

## 实际验证和未验证

- verify_world_transfer_transaction：公共真实MapOwner预留/冻结/loading收据；caller_probe晚期失败同时回滚位置/版本/决定和调用方标记；相同重试/后续坐标不倒退；事务/账号/实际换租约、旧/新/错/缺源位置、畸形receipt、完整deadline身份与已提交位置一致性检查；旧schema精确回填和未知prepared不造值。九组通过。caller_probe只证明跨Module事务性质，不冒充真实任务奖励。
- verify_task_cart_transfer由世界窗口独立运行一次通过：10条实际章节/选卡/精确获领实例装备前置、真实NPC交互证明、世界收据与公开helper、真实任务/奖励/唯一60001后继、晚期背包/目标场景异常全回滚、重复不重奖/不倒退、新租约恢复通过。它使用可信NPC点位夹具，没有自然行走/共享连接屏障/GUI。
- verify_transfer_runtime必要回归通过：旧门户无初始化持久位置场景、真实Owner/加密连接、旧批次隔离、目标发送屏障和后续移动/重载。新增严格helper未扩大旧兼容参数用途。

方法：codebase-design把持久世界决定作为调用方事务Seam，任务所有者组合自己的SQL；tdd先缺Interface红、deadline身份红、bool类型/已提交位置矛盾红，再修复转绿；后续必要旧入口和任务组合核验不重复称全TDD。writing-for-agents给出启动、源检查点、交接、同事务编码提交和失败恢复的完成条件。

交付后主集成已接共享车夫，根verify_newbie_cart_runtime古墓自然Owner/codec反馈已绿；世界窗口读取newbie-cart-runtime-verification确认原生可通见证到车夫、option0、目标scene原decoder/精确发送屏障、到达后移动/重连和重复不重发。该单路线自然连接反馈与上述10路线领域/事务检查范围不同，不能合成“10派全GUI已验”。当前未部署或真客户端验收，全量地图/怪物目标继续active。

提交前/后失败造成旧内存frozen/loading残留时，不通过普通leave或重建Runtime处理；公开新租约恢复步骤见WORLD_TRANSFER_RECOVERY_HANDOFF.md。helper、完整offer迁移与三分支地图退役Interface已稳定交付，并由原始集成接入；根真实SQL失败/commit后清源失败两支同Runtime恢复反馈已绿，后续shared仍统一维护。

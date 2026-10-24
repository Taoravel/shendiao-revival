# 传送提交故障：新租约裁定与旧地图成员退役

2026-10-23。公开Interface已经提供，位置/SQL仅世界Module维护，shared登录和地图Adapter由原始集成窗口接线。新代码未部署、未重启8724，也未操作客户端/真实角色。

## 已复现的原故障

世界窗口实际运行root-owned verify_transfer_failure_recovery.py --expect-stuck：真实临时Legacy角色、门户、保存源检查点，SQL触发器在目标loading后令committed更新失败。数据库回滚为源1007/(8480,6976)、stage prepared，角色被poison；同一GameRuntime重登报Role already in map，旧epoch在源frozen/v3、目标loading/v4同时残留。不能只去掉poison、调用普通leave或靠重启Runtime掩盖。

## 新公开Interface和接入顺序

已显式采用完整实例存档的角色另读 `WORLD_INSTANCE_PERSISTENCE_HANDOFF.md`：新租约同事务先取本决定，再读取完整当前MapAddress；提交与旧成员退休后才按该地址join。原本三项恢复Interface保持稳定；不能将decision的map_id单独转换为默认instance。shared目前尚未接新增load/bind。

1. 保持旧角色/连接围栏，完成新acquire_lease后才读取最终数据库决定。SQLite新租约写入与旧事务串行：旧事务若已提交，新读会看到committed；若尚未开始，后续旧写被租约检查拒绝。等待超时、丢失reply或取消worker不能决定commit/rollback。
2. 在新租约caller事务中调用：

```python
prepare_transfer_recovery_transaction(db, account_id, role_id,
                                     new_epoch, transfer_id=None)
```

它返回冻结TransferRecoveryDecision，或在无指定ID且没有旧记录时返回None。指定ID必须确属此角色旧epoch；省略ID只取该角色最新旧租约交接，适用于当前每角色单个未决交接。当前账号/有效新租约/未删角独立检查，即使db不是FencedConnection也不信旧调用。旧epoch与new_epoch不得相同。

prepared读取已知持久源位置/版本并将该旧决定改cancelled，位置不变；committed/ready要求完整精确receipt，读取当前持久位置/版本，禁止以旧receipt覆盖后续已保存移动。历史cancelled可有取消后合法移动，始终保留当前持久坐标，不能退回原offer.source。完整offer验证原source/target/ID；旧prepared缺offer时不会编造deadline，仅以原journal的旧身份/源/目标作为清旧租约依据。缺持久位置/版本、畸形/矛盾决定拒绝，不生成默认点。调用方先提交此事务，才能把返回值发给地图。

3. 每个实际MapAddress自己的执行者先调用：

```python
inspect_transfer(role_id, transfer_id) -> MapTransferSnapshot
retire_recovered_transfer(expected_snapshot, decision) -> MapTransferRetired
```

inspect返回Owner generation、完整地址、当前成员、该角色源offer、指定transfer的incoming/departure冻结快照。源FrozenTransfer/TransferCommit中含精确目标MapAddress；retire结果也返回target_address。先按journal.source.address找到源Owner，利用该公开快照/结果的目标地址路由目标Owner，不猜实例编号或访问私有字典。

若prepared阶段还没有源冻结记录，源可能无法提供目标地址。此时使用运行时已保存的reservation路由；若该路由也丢失，只在目标map_id已注册的候选实例上通过各自邮箱inspect，筛出含匹配transfer记录的Owner。空候选无需退役；不创建新实例来代替未知旧实例，不把全世界放进一条阻塞恢复队列。该回退用于冷恢复，尚未压测大量实例。

4. retire核快照仍为本Owner/current状态，Owner重建generation不匹配拒绝；角色旧epoch、transfer ID、source/target/完整offer和目标实例记录须一致。清对应旧成员、源offer及该transfer的incoming/departure。原快照在本Owner已经清空时可幂等重试；出现新成员或不同当前状态即拒绝，绝不删除新登录。它不会恢复旧epoch为active、写位置、发消息或创建新角色。

5. ScheduledMap/实际地图Adapter需要在普通在线成员检查之前路由上述恢复操作。retire后同一地图命令内清自己的positions等缓存，条件严格为result.role_id且缓存epoch等于result.old_epoch，不能无条件del role_id。即使退役重试removed=None，也要按同一旧epoch条件清可能残留的Adapter缓存。地图恢复不直接访问其他地图或等待DB。

6. 所有相关旧地图退役完成后，角色Owner再核新租约仍有效，从decision.authority_position/authority_version（或更晚的已提交角色加载快照）在当前配置路由对应实例，以新epoch普通join。MapOwner不判定持久事务，storage不接触地图可变对象。不要在只清源还留目标loading时先开放新会话玩法；每次await返回后由当前角色所有者重验自己的epoch/连接generation。

角色路由必须先撤销旧epoch继续派发地图命令的许可，已在同一Owner排队的命令按序先于退役处理；旧请求重试读取持久cancelled/committed决定，不能绕过journal重新reserve。清内存收据不代替既有retire_receipt所要求的外部durable inbox/outbox；任意跨进程迟到RPC的可靠去重仍属运行时接入范围，本Module不宣称清空收据后可以无条件接受旧命令。

## 边界和验证

verify_world_transfer_recovery先缺公开Interface红，再实现三条真实领域/SQLite分支通过：

- 未提交：新租约把prepared改cancelled、保留源，源/目标旧状态和收据全部退役；capacity/transfer_capacity均1，原两Owner中可立即进行新预留/冻结/loading，无需重建Runtime。
- 已提交：保留目标唯一持久位置，清旧源/目标成员与收据，新epoch在目标join；旧恢复快照不能误删它。
- 显式取消后已继续行走：保留取消后的真实新检查点/版本5，不能因旧cancelled记录退回初始点。

还覆盖错误账号/实际旧租约、错误transfer/new_epoch、Owner重建旧快照、完整实例/分区（目标instance2/partition1）、清理后的幂等重试和所有公开snapshot槽清空。verify_world_owner必要回归通过。

交付后，原始集成已按本Interface接shared load、精确注册地图查找、缓存旧epoch清理和新join。根独立反馈已通过verify_transfer_failure_recovery默认模式及--after-commit两支：真实SQL晚期失败后同Runtime回源并可再次过门户；真实持久commit后注入source.finalize失败，新租约仍在同Runtime恢复目标，并保留后续移动及二次重连检查点。世界窗口已读取当前接线和transfer-failure-recovery-verification/transfer-postcommit-recovery-verification两报告，未重复运行根测试或改其脚本。历史--expect-stuck是红基线，不作为恢复绿色。以上仍是临时DB/真实Owner和codec，非GUI、上线或任意分布式断网/大并发；位置实例持久化仍另验。

方法：diagnosing-bugs以原真实Owner/SQL故障宏反馈为基线，codebase-design将DB最终决定与每地图所有权退役分开，tdd为缺Interface及取消后移动倒退风险先红后绿，writing-for-agents明确冷恢复顺序和不可越过的完成条件。共享源码、存档、发布进程和GUI未改，全量目标继续active。

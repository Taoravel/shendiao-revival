# 旧传送 finalize 会清除新租约的运行时成员缓存

2026-10-24，World 独立确认，尚未修复。准确副本 `runtime/deployments/world-collision-20261023T202425Z/source/game_runtime.py` SHA256 `e6f8fc93ba9763803e602436e289e3bc2713f5a741317a8cebb744f98b0fc540`。

方法：diagnosing-bugs，以真实 MapOwner/SerialOwner 的公开命令构造可重复反例；授权传送及角色租约为可信夹具，不假装客户端请求可自行指定传送目的地。没有改 shared、domain 生产文件、原包、运行服或真人存档。

## 反例和控制

执行 `verify_world_late_finalize_membership.py --runtime-source <上述source> --report revival/evidence/world-late-finalize-membership-r2.json`，实际 exit1。全部 map 命令通过公开 mailbox 顺序执行：

1. 1006 加入角色1、epoch=lease-before-transfer、v1。
2. authorized_transfer→1007 reserve→1006 freeze→1007 activate→1006 finalize→1007 ready。
3. 同一 finalize 在空源地图重试，通过且源 domain/cache 仍空，作为正确幂等控制。
4. 1007 正常 leave；1006 正常 join 新租约 lease-after-transfer、v10，公开 location 可读，未直接填私有字典。
5. 重放步骤2的历史 finalize。domain.location 仍保留新租约/位置/version；运行时 positions 被删除。随后同一新租约公开 location 报 `Map membership expired`。

结果：`empty_source_duplicate_safe=true`、`domain_membership_unchanged=true`、`runtime_cache_unchanged=false`、`new_membership_publicly_readable=false`，输入文件前后稳定。纯内存、无 SQLite/网络/游戏客户端；这不是现场 GUI 故障复现，也不证明普通用户流程必然触发该时序。

## 归因与需修复的接线

三项可证伪解释为：运行时接线在成功返回历史回执后修改了新缓存；domain 幂等清理删了新权威位置；或新租约本身从未有效。公开 location 的前后控制和 domain/cache 分离观察排除后两项。

`world_owner.MapOwner._finalize` 对已存在的相同历史回执允许无副作用返回；它没有清新 domain 位置。共享 `game_runtime.MapOwner.handle` 的 transfer 分支却对 finalize 也先取 `result.location`（历史目标位置），写入 source.positions，随后无条件 pop 角色ID。这将“历史事务幂等成功”错当成“仍在清理相同源成员”的授权。

由共享入口唯一写者修复：finalize 不得把 receipt.location 当成源地图当前位置写入；清理运行时缓存及移动上下文必须对实际旧源成员、完整地址、epoch/version 逐项核实，历史完成回执不得覆盖后来的成员。空源重复 finalize 仍需安全幂等。不要通过让原 domain 的无副作用历史读取破坏幂等来掩盖接线问题。

该 probe 已提供精确拒绝/保持成员的验收，不修改冻结候选。修复后在新准确候选重新执行，本报告的 r2 红不可覆盖；另写新报告，再补同 epoch 往返、新 epoch 和旧版本回执的相邻时序。当前 domain world_owner.py SHA51cd7090…保持不变。

## 未验证

本批未验证真实故障重登、持久提交/恢复、相同 epoch 的完整往返、GUI、上线或所有回调类型；不把上述公开 MapOwner 纵切提升为完整客户端流程。整个全量恢复目标仍未完成。

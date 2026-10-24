# 同实例重定位的调用方事务与SQL恢复

2026-10-24。新增 `world_relocation_storage.py`，接续 [Domain能力](WORLD_RELOCATION_DOMAIN_HANDOFF.md)。本批只新增独立存储Module及验证，未修改shared、账户模块或既有跨图事务；**尚未清理原进程旧冻结成员，也未接共享发送/GUI，不能据此发布同图传送。**

## 已实现的Interface

调用方在角色所属的有界存储执行资源中开启事务，将同一连接传入以下方法；任何异常回滚整个调用方事务，提交完成后才发布地图/连接变化。热路径不连接、开事务、提交、建表、读资源或等待其他Owner。`prepare(db)`只在启动、已有账户/租约/位置/实例schema之后执行，创建有界单条证明记录的journal及索引。

`begin_relocation_transaction(db, account_id, role_id, epoch, prepared, *, now_ms)`：核当前账号/有效租约、确切typed准备证明、当前完整实例及源位置/版本，将stage写为prepared，源仍是持久权威。同一角色仅一条pending；同ID换Owner代次、preparation_id或其他字段拒绝，跨图prepared未解决时拒绝。目标坐标和状态由实际MapOwner提前核原maze，SQL不把客户端坐标当授权证明。

`commit_relocation_transaction(..., prepared, *, now_ms)`：仅精确prepared且未过期时，以源坐标/版本CAS原子写目标位置、目标版本和committed决定；同实例地址、entry_version与原进入transfer_id保持。源实例或进入凭据变化拒绝。已经committed的相同重试返回False，只读核当前权威，不回写旧点；后续正常走动或另一已知实例的更高版本不倒退。新lease不能拿旧证明重新写入。

`cancel_relocation_transaction(..., prepared)`：仅尚未提交时，原子保存原源坐标、推进后的源版本及cancelled决定，之后才能调用Domain取消。已提交目标不能回源；已取消重复只读返回False。过期本身不等于取消成功，依持久决定处理。

`load_relocation_transaction(db, account_id, role_id, current_epoch, request_id)`：仅SELECT，返回冻结 `RelocationRecord`，包含历史prepared/stage、原源进入凭据和**当前**完整checkpoint。历史证明保留旧epoch；checkpoint带本次合法租约。此方法不改归属、不激活地图、不授权任务/奖励或重放旧位置；未知实例保持拒绝，不推默认实例。

`prepare_relocation_recovery_transaction(..., new_epoch, request_id=None, *, expected_prepared=None)`：先取得真实新租约，再在其同一事务解析旧决定。committed目标保留；prepared明确取消并保存源/新版本；若已有严格更高当前checkpoint，只取消旧pending而保留后来权威。源与决定版本间矛盾拒绝。调用方提交此恢复事务后，才可退休旧地图成员、按当前checkpoint加入新租约。

无journal但有来自实际旧地图的精确prepared时，可核当前仍是确切完整源，原子补录取消决定，覆盖freeze成功而begin未写入的窗口；该证明必须由可信Adapter取得，不能来自客户端。没有历史、也没给证明的普通旧角色返回None，保持未知实例，不迁移存档；**None只表示无SQL历史，不表示原进程无冻结成员或允许跳过其清理。** 外账号、无事务、失效/删角租约仍拒绝。

## 采用顺序与尚缺闭包

1. 启动接schema；正常进入地图时从实际可信Owner显式采用未知旧实例，先保存确切源检查点。新Module不自动迁移。
2. RoleOwner授权具体同实例操作并撤销旧连接许可/移动上下文；在实际地图执行freeze，再在角色事务begin。源/目标schema都不新建实例。
3. 在同一角色事务commit目标，落盘成功后调用Domain.commit_relocation；失败先读取/取消持久决定，事务完成后再Domain.cancel。任意SQL失败回滚，不能吞错后提交前面的其他资产写入。
4. 接新lease恢复及**旧进程MapOwner快照/精确退休**，再加入当前完整地址；连接侧精确scene/flow/version发送屏障及原ready、同批次旧输入隔离仍须主集成接入。

当前第4项的旧内存成员退休Interface和实际shared调用尚未实现；SQL返回记录不能替代它。物理源/目标原包及同图Scene可接受性来源在前述Domain交单，本批没有制定1627消息序列或住宅坐标政策，也没有把房屋位置键当像素。

## 可执行证据与边界

`verify_world_relocation_storage.py`：9组实际SQLite调用方事务检查，含commit、后续位置/新lease只读重试、晚期SQL故障全回滚、cancel、prepared/committed/未写journal三窗口恢复、严格身份/期限/旧源拒绝、真实前次跨图进入凭据保留及未知实例拒绝、无历史兼容、恢复补录后晚期故障全回滚。全部账号/租约/源位置和其他事务写入均为明确临时夹具。

前次跨图进入通过真实MapOwner与原跨图事务产生非空进入凭据，再做同实例重定位，避免只验证空字段不变。冷建检查创建相同完整地址的新MapOwner，从恢复checkpoint加入并继续合法一步；原旧Owner仍冻结并被明确断言未清理。该检查不是实际GameRuntime重连、网络投递或真人自然导航。

调用方Adapter拒绝helper内BEGIN/COMMIT/DDL等；只读路径Adapter只接受SELECT。故障为SQLite实际trigger在目标决定或恢复取消最后一步抛错，公开checkpoint/journal及调用方probe均回滚；probe只是同事务其他写入，不冒称资产玩法已验收。记录JSON有32KiB解析预算，ID/字符串和坐标/版本均有严格类型及边界检查。

主报告 `world-relocation-storage-verification.json` 记录实际声明源码/配置SHA及前后稳定；是工作区/冻结复制的Module验证，不是已发布服务验收。单组复验用 `--group` 并另存报告，不能以子集报告代替整批。新Owner退休、真实连接/客户端、商业容量仍未验证。

方法：codebase-design把SQL和唯一位置权威藏在小Interface后；tdd在既定调用方角色事务Seam先缺Module红→真实commit绿，再缺cancel/recovery及无历史兼容红→逐段绿；code-review按新增空基线与固定after进行Standards/Spec两轴；writing-for-agents共置先后顺序、失败与未完成范围。整体目标仍active。

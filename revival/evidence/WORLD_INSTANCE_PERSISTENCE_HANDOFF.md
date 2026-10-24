# 地图实例归属的同事务存档

剧情私有身份现有独立目录allocate/load事务Interface及正式政策，先读 `WORLD_STORY_INSTANCE_DIRECTORY_HANDOFF.md`；这不会代替本文的位置/完整地址绑定。目录12组与本文存档12组分别判断，共享完整地址接线仍未完成。

2026-10-23。世界Module在 `world_transfer_storage.py` 提供显式实例绑定及读取；传送仍使用原 `commit_transfer_transaction`。位置、实例地址、传送结果在调用方的同一事务提交。共享接线、实例目录与真实客户端验收尚未完成；未部署或改运行存档。

## 接入顺序

1. 启动调用既有 `prepare(db)`，在角色/租约/位置表准备完成后建可选实例表。热路径不建表、不另开连接、不自行提交。
2. 对未知实例的旧角色先解决未决传送。仅从实际分配的Owner、完整可信源快照或精确持久回执确定完整 `MapAddress(map_id, instance_id, partition_id)`；资源模板编号本身不能确定实例。保存精确位置检查点后，才在当前角色事务显式绑定。
3. 以后所有已绑定角色的跨实例移动通过持久交接提交；原 `begin` 在写prepared前核完整源地址，`commit_transfer_transaction` 再核源并原子写目标地址。普通行走沿原检查点保存当前位置/版本，不重写实例进入凭据。
4. 新租约重连在同一事务先调用稳定的 `prepare_transfer_recovery_transaction` 解决最终决定，再调用 `load_map_instance_transaction` 读取完整当前地址。若有恢复决定，核当前位置/版本一致；提交后才按原恢复契约退役旧实例成员，再用读取到的完整地址加入新租约。

每次异步返回仍由角色Owner重核epoch/连接generation。持久读取或绑定不会创建实例、加入地图、解除loading或确认客户端可见。实例尚未注册或无法重建时，运行时必须按显式实例生命周期政策处理，不能退回同模板的默认实例。

## 公开Interface

```python
load_map_instance_transaction(db, account_id, role_id, epoch)
    # -> MapInstanceCheckpoint | None

bind_map_instance_transaction(db, account_id, role_id, epoch, expected_location)
    # -> MapInstanceCheckpoint
```

两者均要求调用方已开启事务、角色属于该账号、当前租约有效且未删角。返回冻结快照；不访问文件/资源、不建表、不调用地图或连接。账号/角色/epoch/地址畸形、存档矛盾等抛 `ValueError`，调用方应回滚，不能以默认坐标/实例继续。

`None` 只表示没有显式实例绑定。保留旧角色的未知状态，既不从map_id生成instance_id，也不由家园goto的destx/desty推断实例。None不授权盲目join；旧路径的迁移来源由集成方明确提供。

绑定的 `expected_location` 必须是可信当前 `Location`：active、同role/epoch，且其 `(map_id,x,y,version)` 与数据库精确一致。map_id/instance_id为正signed63范围整数，partition_id为非负signed63范围整数；XY为非负signed16范围整数。bool/float不作为整数接受。第一次绑定写入完整地址；已有绑定仅能确认原地址，不能靠再次bind换实例或重置进入版本。

可信Location来源由调用方负责；该Interface不把任意客户端数据认证为可信，也不凭历史journal替调用方选一个实例。若旧角色仍有未决交接，必须先恢复再采用最终来源，不能在恢复前把source或target猜为active。

`MapInstanceCheckpoint` 字段：

|字段|含义|
|---|---|
|role_id / login_epoch|当前读取角色及有效租约；epoch来自调用，不复活旧租约|
|address|完整MapAddress，包含资源模板、实例和分区|
|position / version|从既有role_positions + position_versions读取的当前持久位置/版本|
|entry_version|进入该实例时的版本下界；普通行走后小于当前version是正常情况|
|transfer_id|进入该实例的持久交接ID；首次明确采用旧档时为空字符串|

实例表仅保存地址和进入凭据，不复制XY或当前version。读取要求位置所属模板等于绑定模板、进入版本不高于当前版本；矛盾拒绝。绑定采用与位置记录共同的全局递增版本约束，已采用角色不能在重连时把version归1。

## 传送、重放与失败

既有传送函数参数及True/False语义保持：True表示caller事务写入目标决定，False表示精确已提交回执重放。调用方仍负责最终commit/rollback及提交后发布。

- 已绑定源地址与offer不一致时，`begin` 不留prepared记录；已记prepared后源地址再变，提交仍拒绝。
- 第一次提交在同一caller事务写目标位置/版本、committed journal与完整目标地址。实例写入最后失败时，调用方回滚全部三项，不能吞异常后提交前面写入。
- 已提交回执的重放核精确原receipt、当前版本和实例进入凭据。当前已走到更晚位置或更晚同模板实例时不回写旧地址/坐标。相同进入版本却地址或非空transfer_id不匹配则拒绝。
- 旧的已结束journal重试在 `begin` 先返回已记录stage，避免角色已经换到另一实例后误报“源实例变化”；prepared及新交接仍核源。
- 未绑定的角色保留原legacy行为，不在commit时静默采用。旧普通portal兼容的source checkpoint lag仍由原显式参数控制，不扩大为跨实例容错。

稳定三项 `prepare_transfer_recovery_transaction`、`MapOwner.inspect_transfer`、`MapOwner.retire_recovered_transfer` 的参数及返回合同未改；用view的实例仍按 `WORLD_MAP_VIEW_HANDOFF.md` 采用配套退休。实例加载与决定必须在新租约同事务读取，原稳定恢复决定本身不承诺独立加载完整新实例；这项组合由共享入口执行。

## 实际验证

`verify_world_instance_persistence.py` 在临时AccountStore及真实MapOwner上通过12组：显式采用/重读、晚期采用回滚、位置/journal/地址晚期SQL失败全回滚、caller事务无嵌套连接或DDL、后续行走/旧回执不倒退、异账号/重绑拒绝、记日志前与commit时两次源实例围栏、同模板不同实例提交、后续实例不被旧回执覆盖、矛盾拒绝、新租约保留地址且旧租约失效。当前父窗口复跑通过，报告 `world-instance-persistence-verification.json`。

原4项必要回归已在该实现完成后执行通过：world_transfer_transaction九组、world_transfer_recovery三分支、transfer_runtime普通门户/屏障/重建及task_cart_transfer十路线。后续代码只补说明；未为交单重复全部宏测试。

同模板案例使用明确的受控portal fixture，不代表原1594家园或1627特殊入口规则已经恢复。原房屋位置键及客户端消费者见 `WORLD_SPECIAL_PORTAL_CONSUMERS_RESEARCH.md`。

## 当前未接与未验

嘉兴100106→1501单角梦境的具体能力/缺口已按当前源码单列 `WORLD_STORY_INSTANCE_HANDOFF.md`：目前没有private/story分配目录，map factory/join/load仍按模板。公开prepare_transfer可接不同模板的可信任务目的，但不代替实例分配、归属/生命周期和完整共享地址路由。

当前shared的ScheduledMap仍按模板生成默认MapAddress、GameRuntime.map仍按模板路由；没有生产调用新load/bind。共享入口须统一接完整地址目录、持久读取/显式采用及MapOwner重建，并提供实例创建/存续/回收政策。世界窗口未修改这些共享文件。

未恢复住宅所有权/权限/房屋级别、专用进出流程、持久NPC/怪物实例状态、跨进程实例迁移或商业数据库。未部署、重启、操作真实角色或启动游戏；上述通过不等于真实重连已保持住宅或副本，也不替代黑屏/移动/新手全程GUI验收。

方法：codebase-design保留单一位置权威并让实例状态与已有交接同事务；TDD按缺load/bind、提交后残留源实例、错源可写prepared三处公共行为先红后绿，其余为必要补充验证；writing-for-agents按启动、采用、传送、恢复、失败及未接范围收口。

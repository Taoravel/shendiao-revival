# 分区运行时集成（第一阶段已接入）

最新部署：2026-10-23经用户“部署 我来验收”授权，新手序章共享入口已重启到PID31052，127.0.0.1:28993，非training；正式Challenge601/heartbeat与存档完整性通过。既有23张表数据保持，客户端未自动启动，等待用户新建角色实机验收。见latest-deployment-verification.json及PROGRESS第十三批；下面“后续源码未部署”等为当时历史状态。后续源码仍可能继续编辑，以启动摘要区分已加载版本，不自动热更新或重启现场。

最新源码追加NPC任务与跨图发送屏障，详见`NPC_TASK_RUNTIME_INTEGRATION.md`。这些后续源码没有部署到用户当前手测现场；当前画面黑屏/不能移动尚未解决，前批网络回归不能作为画面验收。第一阶段以下部署记录为历史批次，不代表后来文件都已加载。

2026-10-23。采用codebase-design，将连接编解码、实体邮箱和阻塞持久化分别放在小Interface后；diagnosing-bugs以受控慢I/O的实际推进顺序验证，不用搜索Lock代替验收。

## 公开Interface与验证入口

- `runtime_core.SerialOwner(key, handler, capacity)`：单个实体的有界邮箱，`call(operation, *immutable_args, request_id, deadline)`按入队顺序处理；不同实例独立运行。队满抛Backpressure，超时不撤销已提交事务。
- `runtime_core.BlockingIO(partitions, workers_per_partition, capacity)`：阻塞I/O隔离，`run(partition_key, callable, *args)`；各分区有独立线程资源和容量，禁止调用Session.feed。SQLite仍有文件级单写。
- `runtime_storage.prepare(accounts)`：监听前加载配置及迁移，返回任务资源、社交存储、策略、只读地图；`GameRuntime(accounts, prepared, io=None, logger=None, training=False)`支持注入持久化与诊断Adapter；`ConnectionOwner.run(reader)`和`GameRuntime.handle_socket(reader, writer)`为线上入口。仅目标连接发送泵可编码RC4/MPPC及写writer；社交结果只投递逻辑消息。
- `GameRuntime.roles[role_id]`、`maps[(instance_id,partition_id)]`、`battles[battle_id]`分别拥有角色、地图、战斗状态；login_epoch用于丢弃旧消息和持久化写入围栏。
- `accounts.AccountStore`保留本地SQLite Adapter；带epoch的存储和同事务结算由运行时接入。迁移完成后补记精确方法和剩余兼容路径。

已运行：`python revival/verify_runtime.py`，临时数据库通过8类检查：登录/建角入口所用原生认证、选角进图、库存查询与TaskDomain查询、社交跨连接持续密文解码、原子资产/公共凭据重试及失败回滚、暂停实际RoleOwner结算存储时另一连接心跳/地图移动判定/实际BattleOwner战斗出招独立推进、同角色FIFO与满载、旧epoch写入/投递拒绝及重登凭据、发送队列满载断开。报告`runtime-verification.json`。旧同步验证`verify_gateway.py`保持通过，保留为兼容协议对照。

`verify_runtime_contracts.py`由主策划独立维护，4项通过：取消调用方不撤销已受理命令、取消I/O等待不提前释放容量、非法邮箱/日志容量在创建资源前拒绝。`verify_gateway_isolation.py`旧真实TCP基线false，新`serve.main`为true；注入临时存储和随机端口，不涉及在线账号。原网络循环阻塞故障已有相同检查红转绿。

## 实际路径、容量与剩余工作

- `serve.main`已切到GameRuntime；账号构造、Inventory.prepare、prepare_task_store、SQLiteSocialStore.initialize在监听前运行。网络循环不执行同步Session.feed、SocialHub、SQLite、DDL或配置全表读取。
- 单连接发送邮箱128帧/1MiB，单次drain限3秒，满载断开目标；源方不等待慢writer。单实体邮箱64命令；持久化8个稳定键分区，每区2线程、最多32个运行/等待项；诊断独立单线程，队列2048条、批次64，满载计丢弃。所有容量必须正整数，队列不默认为无界。
- 角色邮箱按role_id和login_epoch；地图调度Adapter使用world_owner.MapOwner（每图实例容量2048、交接凭据128）；战斗调度Adapter使用battle_owner.BattleOwner（64邮箱、512重试凭据、播放等待30秒）；任务查询和跟踪使用TaskDomain及task_persistence同事务接线。各系统Interface仍由所属窗口维护。
- 社交RoleSocialOwner不保存Session；Delivery核对目标epoch两次后由发送泵编码。频道按scope/key及role_id模16分区，64成员一批让出循环；当前仍为同地图频道，未恢复距离AOI。在线快照的全量复制仍是大规模优化对象。
- `role_leases`持久化随机正整数epoch；角色写连接在写事务内校验有效租约。新租约与已有SQLite事务串行，因此旧事务可在替换前完成，但替换后旧写入被拒绝。I/O超时会隔离角色所有者，不能把未知提交结果当撤销并继续修改。
- `runtime_storage.settle`把Inventory.apply_settlement、资产专用凭据和公共role_settlements凭据放在同一事务；仅可信角色命令可调用，无客户端发奖消息。失败回滚、相同键重试和重登已验证。尚未把任务完成、经验、币种与跨角色交易接入这一事务，不能声称完整奖励系统已迁移。
- CHECK位置更新只更新地图所有者，按角色每秒合并检查点；STOP/登出提交最新版本。跨图目前只保留源位置并记录transfer_pending_integration，完整reserve/freeze/activate/finalize/加载确认和崩溃恢复仍需接入，未沿用旧同步Adapter直接写目标位置。旧源在途原生包没有携带版本，跨图接线必须继续隔离加载阶段。
- SQLite单文件仍只有一个写事务；线程分区仅隔离等待，不增加同文件写并行。持久化Seam可注入其他Adapter，但当前尚无商业数据库Adapter或跨进程所有者部署，没有商业容量结论。
- 已有每邮箱等待/执行累计耗时与高水位、I/O待处理容量/超时/累计耗时、连接积压/拒绝、日志丢弃计数；事件循环延迟、完整分布式追踪、指标导出和全路径CPU预算仍待补齐。

## 部署与原生网络回归

原28993未见监听，旧gateway.pid31844已陈旧。保留既有账号库备份后启动新入口，PID18232（后续以runtime/gateway.pid为准）。`verify_runtime_live.py`连接真实127.0.0.1:28993，用既有角色ID1验证认证、角色列表、选角预检、世界/时间/场景顺序、加载后好友初始化、原生解密/解压及心跳。未发测试奖励或修改角色属性；测试会获得并释放该角色的在线租约。报告`runtime-live-network.json`。本次尚未重做原客户端GUI画面验收，前期可见临安截图不能当新运行时的画面验收。

# NPC治疗与活力：源码交接

2026-10-23，NPC窗口。主入口仍为 [NPC_RECOVERY_HANDOFF.md](NPC_RECOVERY_HANDOFF.md)。本批实现已通过临时库和内存连接验证，真实客户端显示、点击和部署版本未验。

唯一人物资源消费者已追加：npc_recovery.settle显式成对注入resource_rules/equipment_rules时，已迁移角色使用root唯一carrier与最终caps，旧profile保持原路径，不自动迁移。治疗/收费/原生完整刷新及失败回滚详见[NPC_INN_RESOURCE_INTEGRATION.md](NPC_INN_RESOURCE_INTEGRATION.md)；共享新profile加载及激活仍待主集成。

## 集成时先核对

统筹窗口通知当前部署已被并行源码变化触发启动围栏后，本窗口立即停止运行时源码、配置写入，只继续离线读取、临时库检查和证据文档。没有启动/停止服务、操作现场客户端或连接真实角色库。共享接线后续由原始集成窗口集中维护。

本窗口确实修改过game_runtime.py，最近一次写入时间2026-10-23 14:44:43（本地时区）。涉及MapOwner scripted_transfer；RoleOwner NPC普通服务/原生请求路由、仓库访问权限、售卖缓存、治疗分发，以及本批活力初始化/入场/tick/close。精确位置以当前源码查找npc_recovery、role_vigor、NPC_GAMEPLAY_TYPES、initialize_vigor、scripted_transfer为准，非稳定行号。runtime_storage.py本窗口写入为启动期npc_gameplay.prepare，时间13:41:23。未改accounts.py、serve.py、gateway.py、inventory.py。

冻结时采集的SHA256：

| 文件 | 最近写入时间 | SHA256 |
|---|---|---|
| game_runtime.py | 14:44:43 | 0e2047ef9cd777e9e235379a803e8487abccc7b1ea9ef66d25e9684428e4d693 |
| runtime_storage.py | 13:41:23 | d826f407670f4a8396214eb08d2033ed234d9f489389094a40d189fbe3265e5a |
| npc_gameplay.py | 14:37:38 | 8d5420c693e63edbddb03d5570e73ade32093b61ceb20bb8a609936b168b5564 |
| npc_recovery.py | 14:41:57 | aa7bfed51b379cb9310f0f08b4495e0b383ff103ed7dcf2e382910915c3c772e |
| role_vigor.py | 14:40:50 | 5d5794460962f498c34d727a17c2841efec3d74114d180a745da20dd4de86a9d |
| pet_care.py | 14:37:38 | abc70a407a793a672cbfb4203fe48af4997b5964fbf50c4c5a9c87792e27b1d2 |
| design/npc-services-v1.json | 14:40:50 | d867401f57c98709e9e164c08db536e8a9ca215b219bda52549e0cb2dc6dcd7c |

上述是交接快照，不证明当前进程已经加载，也不授权在部署期间覆盖共享文件。

## Module与Interface

`npc_recovery.prepare`启动载入只读政策/显式NPC绑定并建凭据表；`plan`将地图证明和原CRecovery转为不可变RecoveryIntent；`settle`由角色所有者经有界I/O提交。角色有效租约、请求期限、同命令指纹均重验；资产、费用和公共/治疗凭据加入同一个事务，编码失败同样回滚。重试输出当前绝对状态，不能把之后新受的伤再次治好。

原CRecovery为0xc2333，12字节BE64 NPC实例key + BE32 kind1..4。普通CNpcService同样能走已验证的治疗分支。地图交互证明、战斗/loading/序章门控仍在Owner入口。NPC10086/10493显式绑定service10/11/12，客栈10157/11099/11100绑定service3；绑定关系是designed，原NPC定义和服务语义有原包证据。

- kind2治疗全部已知携带宠物HP/MP，包含HP0；kind3恢复忠诚；kind4两者。未知旧成长或照顾档拒绝，全部已满无扣费。寿命原值保持，不能当作补寿命入口。
- kind1使已知且存活人物的HP/MP达到当前上限，同时扣活力和费用。不承担人物复活；伤势640=maxHP沿用既有明确设计，未声称还原独立伤势玩法。
- 宠物刷新使用pet_record(vars(pet))保留最新PetState.skills，未把嵌套技能对象转换成不兼容字典。

`role_vigor`将活力的持久基线、在线计时、消耗和原生刷新封装在角色租约事务中。新恢复角色必须有持久创建来源才自动初始化；旧角色缺档保持未知。可信initialize_profile / RoleOwner initialize_vigor可明确迁移，客户端没有设置基线的线包。重复迁移不能重置已消耗值。

在线计时以当前epoch绑定，正常退出保存未满周期的在线余数，重连不计离线时间，满活力期间不能积攒未来增长。原生刷新为SRefreshRoleData的440/620两项。现入口通过已有tick每60秒检查一次；网络持续输入时idle tick可能推迟，消费时仍按当前服务器单调时间结算。尚未证明硬实时UI刷新，异常进程终止可能损失最近未检查点在线时间。

## 原包证据与设计范围

原映像SHA256为2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791。CRecovery构造db1c70、marshal e51c00、unmarshal db1d30；服务分发1633870中3/10/11/12对应kind1/2/3/4。

客栈原分支16338ce读取活力上限620，乘地址224e408的double，再经原ftol向零取整。常数精确为0x1.3333340000000p-3，即0.15000000596046448。读取当前440检查费用；等级490不超过20免现金，否则500。原分支同时比较HP60/140、伤势640/140、MP70/150。

宠物原报价11360e0按全部携带宠物计算，普通级受伤宠物每只20×(level+1)；1136290按忠诚缺口计算(45+2×血脉当前值1140的个位)×缺口。忠诚上限从原cpetxuemaiconfig.maxloy查取。原quote以-3代表等级≤20免费，原特殊等级>1000有另一映射，本批未支持该特殊成长段。

当前血脉数值模型不足，忠诚单价45是血脉个位0的明确本地设计，不能称完整原版报价。活力初始/上限100、每在线300000ms增长5是恢复档设计，非已恢复等级/技能公式。原440说明支持每在线五分钟增长，但未在本批取得原增长数量和上限公式。现金渠道复用既有npc_shop费用政策，为本地设计。所有参数来源集中design/npc-services-v1.json#recovery。

攻略调查只得到历史官方宠物死亡损失与宠物获取资料，未确认客栈完整公式；2025月卡规则与本地1.6.1版本冲突，不据此增加月卡门槛。以上未决公式应由统筹按DESIGN_AUTHORITY裁定，不能在交接中把设计值升级为原版验证。

## 验证与后续完成条件

采用codebase-design将地图授权、角色治疗事务和发送投递分开；tdd先得到宠物恢复、未知活力及客栈原请求红例，再实现真实Owner切片；writing-for-agents将数值来源、接线与可判定完成条件集中在本文。

| 检查 | 结果 |
|---|---|
| verify_npc_pet_recovery_runtime | service10/11/12；两个当前政策level0宠物kind4费用1840，现金5000→3160；HP/MP/忠诚满、寿命5950不变；重试/空操作/错kind与重连 |
| verify_role_vigor | 旧档未知；显式100→85；跨重连余数、离线排除、满值不积攒、余额与旧租约拒绝 |
| verify_npc_inn_runtime | 原service3及kind1；未知旧活力拒绝；HP/MP满、活力100→85、现金1000→500同提交；重试保留后来伤势；再次扣15/500；余额不足原样回滚；重连当前70 |
| npc-recovery-native.json | 离线原x86：3个NPC key（含高32位）×4kind逐字节序列化/反序列化；截断拒绝；440/620原map codec及赋值；9个活力上限的原x87+ftol消耗计算 |
| 既有NPC回归 | 仓库、出售/回购、普通修理、门派车夫通过；商店原检查的菜单只含[2]假设已过时，当前客栈原菜单是[2,3]。仅在内存中改为[2,3]重跑，其余购买、扣款、满包回滚、重连检查全通过；冻结解除后须持久更新该测试预期 |
| verify_runtime | 慢角色I/O期间另连接心跳/地图/战斗继续、角色FIFO/背压、旧epoch、连续RC4/MPPC、慢连接关闭全部通过 |
| verify_role_lifecycle_runtime | 实际退出/返回选角/返回登录/删角临时库回归通过；保留他角心跳，账号归属、在线租约竞争、晚期回滚和移动检查点继续有效 |

商店检查首次失败后用diagnosing-bugs收窄到原菜单解码断言；同一真实请求有新增休息项，全部购买断言未改即可通过，因此是旧菜单预期，不是扣费或发物故障。部署冻结期间未改验证源码，该命令原样重跑仍会在旧预期处失败，此限制须保留。

本批仍需：冻结解除后持久保存商店菜单预期及独立原生治疗探针；主集成核对上述shared改动是否纳入实际启动版本；原客户端分别操作四种kind、收费/免费与活力刷新；补全血脉报价、旧档迁移、独立伤势及活力完整公式。所有运行验证仅临时数据库与内存加密连接，未验证商业容量和现场GUI。

后续批更新：冻结已解除，verify_npc_recovery_native.py已持久保存并原样执行通过；商店菜单[2,3]预期已保存并从完整prepare重跑通过。中途组织启动规则故障已收敛，当前接线与验证范围见[NPC_DEPOT_MONEY_INTEGRATION.md](NPC_DEPOT_MONEY_INTEGRATION.md)。此更新不改变本页此前冻结快照的历史时间/hash。

冻结期间下一切片仅完成原生取证：仓库银两存取，见[NPC_DEPOT_MONEY_NATIVE.md](NPC_DEPOT_MONEY_NATIVE.md)。该切片尚无运行时处理，不因为报文已核对而标完成。

# 地图权威与玩家同屏：同命令接线

2026-10-23。启用玩家同屏的地图使用 `world_owner.MapOwner` 的配套 Interface，使位置与 `world_roles.RoleScene` 成员关系在同一地图执行者内完成检查和发布。当前仅所属源码与离线验证；共享运行时、生产参数、发布和客户端尚未接入。角色投递契约见 [WORLD_ROLE_DELIVERY_HANDOFF.md](WORLD_ROLE_DELIVERY_HANDOFF.md)，原玩家布局见 [WORLD_ROLE_PROTOCOL.md](WORLD_ROLE_PROTOCOL.md)。

## 启动与所有权

每个 `MapAddress(map_id,instance_id,partition_id)` 的执行者独占一个 MapOwner 及其可变 RoleScene。传入 view 必须为精确 RoleScene 类型、地址完全相同；执行期间没有 await、SQL、网络或文件访问。RoleScene 是地图内部的下属投影，不能由另一个线程或所有者同时维护，也不能跨所有者传递它本身。角色与连接只接收冻结 Location、RoleSceneChange、RoleDelivery 和绑定快照。

启动预加载地图及需要的 maze，显式配置角色容量、交接容量、地图邮箱容量、AOI半径、可见对容量和原列表批次。元数据由受信角色快照提供。开启某实例的投影后，该实例涉及成员/位置的全部命令都走下表配套方法；原 standalone 方法只保留未启用视野的兼容路径。混用会造成版本与成员不一致，不能依靠后续移动静默补齐。

## 调用顺序与返回

| 操作 | 公开 Interface | 前提与结果 |
|---|---|---|
| 初次加入 | `join_with_view(location,appearance,view)` | 当前受信 active Location 与冻结 RoleBasic 的ID/坐标相同；先核地图/视野容量及原编码，再发布两边。返回 `(Location,RoleSceneChange)`，包含范围内双方真实入屏；完全相同重试不重复入屏 |
| 直接移动 | `move_with_view(command,now_ms,view)` | 地图当前租约/版本/截止时间与当前view Location均匹配。返回 `(MoveResult,RoleSceneChange或None)`；成功checkpoint与view Location相同。仅意图不更新位置或视野，拒绝不改位置、旧offer或视野 |
| 队列移动 | `submit(command,now_ms)` 后 `process_one_with_view(now_ms,view)` | submit保留有界原邮箱；处理入口先核view所属实例，再取命令并重新核当前版本/期限。空队列返回None，取出后返回同move tuple；不能继续调用旧process_one，否则漏掉view。错误实例不消耗命令 |
| 普通离开 | `leave_with_view(expected,view)` | 必要角色检查点已提交，当前active权威与view一致；返回 `(原Location或None,RoleSceneChange)`，同步删除并向仍可见者移除。两边均不存在的重试为空；旧登录离开不能删除新登录 |
| 源换图收尾 | `finalize_with_view(receipt,view)` | 调用者已持久提交目标归属，来源仍为相应frozen状态；源view应仍等于offer.source的active快照。返回 `(TransferCommit,RoleSceneChange)`，同命令移除源权威/view；完全相同且源已空的重试不重复发包 |
| 目标激活 | `ready_with_view(expected_loading,appearance,view)` | 目标权威仍loading；满足既定scene-transition发送屏障。先对新active位置完成原入屏编码/容量检查，再发布active权威与view。失败仍loading。返回 `(新active Location,RoleSceneChange)`；不是原生客户端ready回包 |
| 取消恢复源 | `resume_with_view(cancellation,view)` | 取得目标明确取消回执，不能以超时单独解冻；源view保留offer.source。返回 `(恢复active Location,RoleSceneChange)`，两边版本一致；重复取消不重复投递，后续正常移动可继续 |
| 新租约退休旧交接 | `retire_recovered_transfer_with_view(snapshot,decision,view)` | 按 [WORLD_TRANSFER_RECOVERY_HANDOFF.md](WORLD_TRANSFER_RECOVERY_HANDOFF.md) 在新租约事务提交最终位置决定后调用，旧epoch已被围栏；返回 `(MapTransferRetired,RoleSceneChange)`。清对应旧地图成员/交接/view，拒绝新epoch投影。完成所有旧图退休后，以持久决定加入新epoch |

准备/预留/冻结/目标loading阶段不创建目标view，源view保持冻结前最后可见快照。源清除发生在持久决定后；目标入屏发生在发送屏障后的ready。取消恢复使用原SRoleMove投影已接受位置；原SRoleStop为空处理器，不能据此声称精确停步。

原 `prepare_transfer_recovery_transaction`、`MapOwner.inspect_transfer`、`MapOwner.retire_recovered_transfer` 的参数与返回保持不变；共享恢复调用者可继续使用。配套退休方法只为已启用view的实例补同命令清理，不替代DB决定或验证新租约。

## 成功、拒绝与投递

配套方法先完成地图校验，再完成view的全部容量/原编码检查；view成功后立即更新权威字典。预期的校验或容量拒绝保持两边旧状态，无中途await/callback/I/O。移动用MoveResult.rejection返回拒绝，其他成员命令校验失败抛ValueError。异常进程终止、内存分配失败不属于跨Module持久事务保证；这里保证的是正常内存命令发布顺序。

调用者仅在同步返回成功后发布checkpoint/逻辑投递；原有持久检查点、跨图角色事务、发送失败恢复仍各自遵守所属契约。不能把地图内存成功等同SQL已提交，不能把RoleSceneChange发出等同客户端已显示。目标队列满也不会撤销已接受的地图移动，应按目标RoleViewInbox失败策略断开/重建场景，不能丢一次入屏后继续移动。

每份RoleDelivery仍需捕获目标 `RoleViewBinding`，按接收者sequence交目标连接所有者；排队及RC4/MPPC编码前都核当前地图/epoch/membership_revision/connection_generation。保持整批准入和连续序号，具体见投递交接。地图执行者不访问Session，不等待慢连接。此批没有把现有epoch-only共享发送路径称为已满足这些条件。

## 验证

以下均通过公开Interface，无真实角色或运行服修改：

| 可执行入口 | 已验证范围 |
|---|---|
| `verify_world_membership_view.py` | 双方入屏、相同重试、地图/视野各自容量拒绝、原编码失败不占地图、离开/重登隔离，5组 |
| `verify_world_move_view.py` | 配对容量拒绝保持坐标/旧offer，释放容量后同命令可重试、portal proposal与视野同发布、旧版本/意图及无文件访问，5组 |
| `verify_world_mailbox_view.py` | 空队列、错误view不消耗、配套出队原移动消息、邮箱满/排队变旧/过期，5组；缺方法先红后实现绿 |
| `verify_world_transfer_view.py` | 冻结/目标loading不提前显示、源收尾及重试、目标编码失败仍loading、目标ready/后续移动，5组；持久提交在此fixture视为调用者已完成 |
| `verify_world_resume_view.py` | 冻结拒绝、明确取消后双快照同版本、重复取消无新增投递及后续行走，3组 |
| `verify_world_recovery_view.py` | 源未提交、目标已提交并行走后两支；清旧view/保留新位置、新epoch不能被旧退休删除；DB授权另由存储验证覆盖 |
| `verify_world_map_view_native.py` | 配套命令→捕获route→目标inbox→原完整decoder；源Add/Remove，目标Add/Move/Remove，5份真实输出 |

原MapOwner、302网格节点碰撞、存储三支恢复及普通持久传送必要回归通过。各入口生成对应 `world-*-view-*.json`，原生链为 `world-map-view-native.json`；原映像fixture只证明字段解码/内存行为，没有GUI/GPU/真实插值或商业容量验收。

全资源范围另由verify_world_resource_handoffs实际覆盖302图的MapOwner/view生命周期、实例隔离及原scene/Move解码，212有向普通跨图代表走原源格/目标并在目标继续移动；6275原goto独立新鲜PFS比对及15组剩余分类见WORLD_RESOURCE_HANDOFF_AUDIT。两支same-map实际拒绝是明确未恢复项，不因普通配套Interface通过就算全portal成功。

## 上线前仍需补全

1. 主策划登记生产AOI形状/范围、可见对和消息/字节/邮箱预算、满载策略。当前圆形实现及测试64像素不是原服证据；原客户端景物各轴576距离属于本地景物，不能移作玩家AOI。
2. 角色初始朝向/更新、packed低位和外观扩展来源明确。原高四位八方向已证，低四位getter不补111的新4例见 [WORLD_ROLE_LOW_NIBBLE_RESEARCH.md](WORLD_ROLE_LOW_NIBBLE_RESEARCH.md)。0x71等仅fixture，不能截断/取模权威school111来凑同屏字段；未知部分按主策划显式designed并保留完整自身资料。
3. 由共享入口所有者接上述生命周期与目标发送前binding围栏；独立核验真实连接、慢队列、换图旧投递、断线/重登及两实例并行，再由真人测双角色可见、移动和换图。没有该接线/发布/客户端证据，不能称多人功能已上线。
4. 碰撞状态的进场原生来源另见 [WORLD_SCENE_MOVEMENT_STATE_RESEARCH.md](WORLD_SCENE_MOVEMENT_STATE_RESEARCH.md)：普通成功加载时packet+2c严格按byte==1归一后覆盖主角+218，普通0→mask1；天气byte不是第二移动状态。加载失败、空主角、无效配置、reason516023/map1404跳过路径仍需处理。发送屏障不证明该原生分支实际运行，且特殊状态/量化连续碰撞仍未完成；本批不默认启用全部地图碰撞。

方法：codebase-design把view预检与权威发布集中到地图命令Seam；tdd按成员、移动、换图/取消/恢复、出队各行为实际红→绿，原生输出和存储为独立追加核验；writing-for-agents按启动、生命周期、失败、投递与上线条件交付。当前完整地图/场景/怪物目标继续active，未部署、重启、开客户端或改真实存档。

# 地图真实成员绑定：供共享入口接线的 Interface 方案

状态：设计候选，未实现新Interface、未接共享入口、未开放收费或玩家AOI。当前发布仍为 main 的 world-collision-20261023T204238Z；下述所属变更不自动进入发布。用户全量目标保持未完成。

方法：codebase-design 将成员来源、位置权威和连接发送分别放在已有地图/角色/连接所有者；diagnosing-bugs 用实际公开Seam观察稳定绑定、冻结与零pair容量；不使用位置version、常量1或客户端字段伪造membership_revision。原始依据是现有 world_owner/world_roles/world_role_delivery，不是原服隐藏业务规则。设计没有新增金币、权限、任务地图alias或NPC可见政策。

## 已有契约与实际验证

`verify_world_role_binding_contract.py` 父执行7项观察，报告 `world-role-binding-contract-verification.json`，6份源码输入前后稳定。两图catalog、外观0x71、位置及可信租约均为明确离线夹具，无运行服/存储/GUI。

* `WorldDomain.join_with_view` 同命令发布权威Location和RolePresence。后者是派生投影，位置仍由WorldDomain独占写入。
* `RolePresence.revision` 随投影更新；`membership_revision` 在普通移动中保持。实际Location.version 1→2，而bind_role_view所得完整绑定不变。不能拿任一前两者代替成员身份。
* 更换connection_generation会改变binding，不更改同一地图成员。连接代次由可信连接所有者给出，不由地图或客户端创造。
* 现有freeze保留源view旧active快照直到finalize；domain实际已frozen。单独bind_role_view仍可接受那个旧快照，故它是可信快照到身份的转换函数，不是“此刻仍active”的权限检查。
* activate的目标loading没有view成员；ready_with_view才建立目标成员。源finalize、目标显式leave后，再以同epoch重新join原源图，会生成新membership_revision，即使owner_generation相同，旧binding也不同。此为公开生命周期命令夹具，不是完整持久传送返回或实际网络流程。
* 现有RoleScene的pair_capacity=0会拒绝附近第二角色；失败前后domain/view都不新增成员。这不是metadata-only模式，不能以该参数绕过完整AOI设计。

## 决定：沿用RoleScene/RolePresence，显式新增成员模式

建议由World所属给现有 `RoleScene` 增加工厂：

```python
RoleScene.membership_only(address, catalog, *, role_capacity) -> RoleScene
```

它返回同一准确类型，保留WorldDomain._view的同实例/同执行者严格检查。该实例的模式固定为member metadata，不能在线热切成AOI；不需要radius/pair_capacity/batch_size，不构造假RoleBasic、不编码/发任何原玩家包、不产生RoleDelivery或消耗玩家投递sequence。RolePresence.appearance在此模式明确为None；完整AOI构造仍要求真实RoleBasic和现行显式容量/外观门槛，行为不变。

membership-only的join/move/leave仍走WorldDomain已有配套Interface；appearance参数仅此模式传None。view只接受已由domain校验的Location、复制为不可变RolePresence，不能消费原始MOVE或自主改权威位置。移动复制新Location但保留member revision；同一精确join重试幂等；真正leave/rejoin新revision。容量取调用者显式预算，不新增生产默认数值。

比较后不采用：第二套可写positions/member字典（双重位置权威）；用常量或位置version拼RoleViewBinding（身份错误）；启用完整RoleScene但丢弃AOI消息（隐式消耗sequence/丢失入屏）；pair_capacity=0（真实拒绝正常第二成员）。上述删除后，生命周期校验复杂性会散回每个调用者，因此放在已有深Module比共享入口手工拼字段更有Locality。

## 两个新增地图公开命令

建议WorldDomain提供以下Interface，由实际MapOwner.mailbox包裹，不向客户端注册同名协议：

```python
role_binding(expected: Location, view: RoleScene,
             connection_generation: int) -> RoleViewBinding
fence_role_binding(expected: Location, view: RoleScene) -> RolePresence
```

`role_binding`必须在该地图执行者内核实：同full MapAddress、当前domain成员精确等于expected且active、view.snapshot精确对应相同Location；再用原bind_role_view生成完整身份。owner_generation来自该RoleScene创建代次，不是WorldDomain/MapMovement里其他含义的generation。地图冷建时必须新建RoleScene，不能沿用旧generation。connection_generation由当前RoleOwner持有的可信连接关系传入；地图本身不认证网络连接。

`fence_role_binding`仅用于membership-only模式。在验证精确当前domain/view后，单调推进RoleScene自身revision与membership_revision，返回保留Location的不可变新presence；旧binding永久不匹配。它不移动角色，不写库存/任务，不伪造网络ACK。完整AOI模式不得直接调用该方法，否则会破坏其投递sequence；未来AOI生命周期需独立审验。该方法处理“已开始的生命周期意图撤销旧服务身份”，即使后续传送取消，也不恢复旧revision。

fence应在共享RoleOwner确认进入transfer/CG/battle/同图瞬移等意图后、任何跨所有者await之前开始；在地图命令内以当时精确active位置执行。之后freeze可保留源view的旧位置投影，但所有旧身份已作废；domain frozen期间role_binding一律拒绝。取消/恢复后，原resume_with_view同步新Location，角色重新取得推进过的binding；先前延迟回复不会因为回到同图而复活。普通MOVE/CHECK/STOP不fence，绑定稳定。若fence命令因成员变化失败，不得自己填revision继续；角色应取消该流程或按现有重连/恢复协议重取真实状态。

## 生命周期接线表

|事件|地图权威/投影操作|绑定与连接动作|
|---|---|---|
|首次加入|domain join_with_view，成员模式appearance=None|active精确快照生成binding，连接所有者安装后才能发该成员服务回复|
|普通行走|move_with_view 同命令更新位置投影|保持membership_revision；NPC操作仍另核当前精确位置/空间证明|
|开始传送/CG/battle|先撤销角色modal/ticket及连接当前绑定，再请求map fence；传送随后freeze|旧绑定无效；不得按旧presence或paid receipt重新安装|
|目标activate|只有domain loading，不建活跃投影|不安装目标绑定，不准收费/回复|
|源finalize|finalize_with_view精确清旧源；晚期历史回执不改新成员|连接CAS清旧绑定，禁止按roleID清新身份；r4修复原则继续适用|
|目标ready|ready_with_view才发布活跃目标presence|准确ready/投递门槛后取目标binding，并在连接所有者安装|
|明确cancel/resume|resume_with_view同步源Location，沿用已fence后的新member revision|恢复须新取当前binding，不重用冻结前旧对象|
|断线/真正leave|leave_with_view在必要检查点/恢复后同命令退出|只清匹配旧binding；新epoch重入生成新member revision|
|连接替换|先使旧连接失效；若原lease退役则leave/rejoin|同member换真实socket也必须新connection_generation；不能从迟到回复获取新连接重包|
|Owner冷建|新domain和新RoleScene代次，持久归属按原恢复流程读入|只有真实新join/ready才安装；旧owner_generation绝不能复活|

表中CG/battle普通恢复只处理绑定，不能冒称正式PVE开启。冻结前撤销连接绑定与地图fence两个执行者之间会有等待；角色在等待期间保持流程锁定，不能处理新服务命令。它们不是跨所有者原子事务，也不持全局锁/网络锁；过期回调按epoch、完整binding与流程身份拒绝。

## 真正发送前的 Interface

共享角色所有者只传不可变binding，不跨执行者持有可变RoleScene。NPC查询/确认/事务仍使用真实current Location、空间凭据、inventory CAS和自身ticket；binding只补充成员/连接身份，不取代这些权限。

连接所有者增加明确安装/撤销当前binding与带binding逻辑回复。安装请求必须携带当前role/epoch、连接generation及角色当前流程的receipt/scene身份，不能来自回复本身；同一旧请求不能覆盖后来的绑定。撤销按expected-binding compare-and-clear，旧close/finalize不能清新binding。

入队与实际RC4/MPPC编码/Writer.write之前都比较完整captured binding与连接当前binding，并核当前角色流程/ticket/scene身份仍匹配；角色开始上述流程时先撤销，旧队列内容不能等resume后重包到新binding。若安装控制与生命周期控制有pending状态，暂停这些scoped回复，不能只核epoch。正在write之后的字节无法撤回；后续scene/绑定切换沿已有严格发送屏障排序，drain不是客户端执行确认。地图操作与连接控制走各自有界邮箱，不为此引入全服队列。

此阶段不实例化RoleViewInbox，不路由玩家RoleDelivery，也不更改同屏生产半径。未来启AOI须新建完整projection/generation、完整入屏重建和独立sender/sequence验收，不能热开metadata实例继续旧sequence。

## 实施与验收要求

World所属实现工厂、metadata分支、两条domain命令及公开Seam回归；main唯一写共享MapOwner/RoleOwner/ConnectionOwner接线；NPC所属消费真实binding并保持原ticket/事务。当前本文与7项witness只说明设计依据，下面各项还没有通过新实现：

1. metadata模式两名同位置角色正常加入且无任何wire输出/sequence，None外观仅此模式有效；完整AOI原编码/容量回归保持。
2. 移动变位置version而binding稳定，重复join幂等；同epoch重返、冷建、连接替换全部隔离。
3. fence推进真实成员revision，冻结/缺成员/错地址/错view/陈旧expected都不能取绑定；取消恢复后旧绑定仍拒。
4. domain/view配套失败不能只发布一方；目标loading不授权，ready后才建立绑定；重复历史receipt不会清新member/context。
5. 实际加密入队前/编码前阻塞夹具：旧身份、场景、epoch、连接与陈旧安装/撤销全部拒；另一地图/连接继续心跳。
6. 原NPC查询/确认/扣费/CAS/幂等回复在真实binding下重新验收；当前没有实现/上线收费。首次真实客户端验收另列，不以纯Module验证替代。

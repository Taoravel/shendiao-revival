# 同实例重定位：所属地图能力，尚未接共享

2026-10-24。用户全量世界目标中的同图入口，当前普通 `reserve` 会以同一地址拒绝；本批在地图自身的单写者中新增独立重定位状态机，保留原跨图合同。**只完成Domain能力，数据库事务、断线恢复、真实发送屏障和政策接线尚未实现；1627或住宅在运行服仍不能据此标为修复。**

## 来源与实际决定

原1627入口为25格，代表源格(114,81)、raw目标1627/(101,115)，现有逻辑目标(1616,1840)。验证从原PFS重新读取goto/maze并核长度/CRC，邻近起点(1816,1304)和确认源点(1832,1304)是明确离线见证，不是完整客户端自然寻路。原同图Scene接受路径及住宅字段差异见 `WORLD_SPECIAL_PORTAL_CONSUMERS_RESEARCH.md`；该来源仍未证明原服实际发送哪种同图通知。

`codebase-design`据此将重定位放在现有MapOwner Interface：仍只有 `_roles` 写当前位置，独立有界记录只存冻结/决定快照；同一实例不分配第二个成员槽，也不创建假实例。源与目标点按调用方可信movement_state核原maze，不做两点之间的行走DDA，重定位不声称连续行走。启动使用已有显式transfer_capacity作为本地图重定位回执预算。

这只是能力合同，**没有新增玩法政策或自动分发**。调用方必须另行授权具体入口、完整实例、原目标的用途和状态；普通move不会自行调用新方法。住宅1594的destx是位置键，不能以这项通用能力把它当目标坐标。共享集成及政策仍交原始集成/主策划窗口。

## 公开Interface与顺序

`freeze_relocation(offer, now_ms, *, movement_state, view=None)`：要求本Owner登记的当前同模板offer、完整当前Location、可用原maze及可信状态；检查类型、边界、时限和预算后，将唯一源成员变为frozen、版本+1。返回带真实Owner代次、原offer、冻结源、计划loading目标及状态的不可变 `RelocationPrepared`。pending精确重试不再次修改；换状态或旧Owner证明拒绝。配套metadata投影先推进许可世代，旧许可不会在取消后复活。全AOI保持源投影至提交。

**调用方持久提交仍待实现。** 必须以当前账号/角色/租约及完整地址，原子保存唯一重定位决定和计划目标/版本；同实例地址及进入凭据应保留，不伪造一次跨实例进入。提交前失败须确证无目标决定才能取消；提交后连接故障保留目标，不能回源。当前没有可供共享调用的重定位SQL Interface，不能把其他跨图事务硬套过来（原事务明确拒绝源目标同地址）。

`commit_relocation(prepared, *, view=None)`：只在上项真实事务提交后调用，撤除旧投影，将唯一角色切到同地址计划目标、loading，返回 `RelocationCommit` 及逻辑投影变化。超时不再否决已提交目标。完全相同的loading/刚ready重试不重复投递，后续移动或新成员后的旧重试拒绝，不能倒退。

调用方随后以新的场景流程/连接代次和精确位置版本投递原消息，取得真实服务器发送屏障；再调用既有 `ready` / `ready_with_view` 激活，版本再+1。新metadata许可与旧许可不同；原生报文没有场景世代，原批次、旧版本、旧连接及观察上相同迟到包的协议限制仍按scene-transition政策处理。本批ready仅由明确受控fixture调用，没有验证writer/drain或客户端ACK。

`cancel_relocation(prepared, *, view=None)`：只在调用方确证目标未提交时，将唯一源恢复active、保留源坐标并推进版本；返回 `RelocationCancelled` 与投影变化。已内存提交目标不能取消，原源许可保持已撤销。调用方仍须落盘恢复版本并重建准确移动声明。取消/提交本身不做数据库或网络I/O。

`retire_relocation(receipt)`：调用方已保留持久决定及重放记录后，释放精确终态回执；不能退休pending冻结。终态记录计入地图闲置检查，角色离开仍不允许有回执的地图回收；精确重复释放无效果，冷建同地址新Owner拒绝旧证明。未接持久重放前保持记录，容量满明确拒绝。

## 验证与未验范围

入口 `verify_world_relocation.py`，报告 `world-relocation-domain-verification.json`。TDD按已有MapOwner/配套RoleScene公开Seams依次观察缺freeze、缺commit、缺cancel、状态bool重试误收、缺回执退休及退休后重复释放失败，再逐段实现转绿。当前8组核源冻结、同地址loading/ready后移动、取消与许可世代、状态/冷建围栏、有界回执/空图回收、满载另一实例独立推进、全AOI容量失败保留loading、热路径封锁文件I/O。全AOI外观为显式fixture，不是生产外观政策。

同批既有owner、跨图view、成员metadata、剧情生命周期和scripted-transfer回归通过。历史成员metadata固定v2仍保留9a701d8源，不覆盖其冻结或ready凭据；本新增Owner源属于独立后续版本，不能暗自替换原共享成员候选。

待完成：重定位事务/唯一键/完整地址CAS、提交前后故障与新租约恢复、旧内存成员的精确退休、连接控制撤销与真正发送屏障、共享分发及明确入口政策、原生输入和GUI实测。**本批不能作为可发布运行时闭包**，完整目标继续active。共享文件、正式存档、服务和客户端未修改或启动。

方法记录：codebase-design将单一位置权威和有界决定集中在所属MapOwner；tdd逐个公开行为红→绿；原PFS用于独立见证与资源匹配；code-review采用真实before/current的Standards/Spec两轴；writing-for-agents将前置条件、顺序、失败和未完成项共置。本说明是实施交接，不是主策划落点裁定。

# 私有场景回复批次取消：最小共享修正候选

2026-10-24。主集成为 `game_runtime.py` 唯一写者；本窗口只在私有临时副本应用候选，没有修改共享源码、发布、服务、真人存档或客户端。

## 精确基线与交付

- 基线GameRuntime SHA256：`0d36cf6a940afdcb903c338f6e5a0fb48c48bb537276de824a3146db744bff25`。
- 候选GameRuntime SHA256：`5bbf51acc3a020f0b758bc47ac5e77a220c208a0029d6061e4f1925b0baf9373`。
- 补丁：`world-scene-delivery-source20261024-candidate.patch`。
- 同快照红→绿、执行输入清单与10组回归：`world-scene-delivery-source20261024-candidate-verification.json`；原始6组观察分别在 `world-scene-delivery-source20261024-baseline.json` / `world-scene-delivery-source20261024-candidate.json`。
- 真实原/候选源码分别保存 `candidates/world-scene-delivery-source20261024/base/game_runtime.py` 与 `final/game_runtime.py`。只取此patch，不复制工作区其他变更；若当前基线不同须局部复核并重跑。

## 触发与根因

`scene_messages`一次登记两条实际MapOwner投递ticket和pool pin。第一条因连接容量不足未入队，其清理在真实MapOwner受控hold；取消处理批次的任务。原实现只让第一条清理继续，没有把尚未offer的第二条交给任何终止路径。真实close、实际finish任务与地图队列均已结束后，队列/字节/成员/work都为0，但pending_scene_deliveries=1，公开pool只余63/64个pin槽；可信时钟到61000仍以在途操作拒绝卸载。

已按三个实际生产循环分别运行正常/取消，共6组：`receive`、`run`的tick回复、`_send`的scene_sent后回复。基线三个正常组0pending/free64，三个取消组均1pending/free63；同一副本只应用候选后，六组全部0pending/free64。主机提供身份、dispatch/role逻辑回复、catalog/Writer/Reader等明确Adapter；真正的ConnectionOwner循环、scene_messages、MapOwner、SerialOwner、pool及真实终止均运行。不是实际任务授权、数据库或GUI验证。

## 候选行为与所有权

增加内部 `_offer_batch` 并统一三处调用。迭代器取出的当前项由连接队列或offer_message的拒绝清理接管；`finally`仅给未迭代后缀建立清理任务，并shield等待。已入队前序仍由发送泵/close处理，不提前释放；当前拒绝项仍由既有finish_delivery的实际终止跟踪处理。receive中的每个barrier递增scene_generation顺序保留。没有增添全局锁、全服执行队列或更改消息/政策/容量。

必要回归独立在同一候选副本跑过10组：实际加密发送、旧epoch拒绝、旧场景fence及后续流连续、65消息部分构造失败、字节容量拒绝、真实drain错误/3秒超时、active+queued取消、清理观察者取消仍持自己pin、未知清理失败保留围栏后精确重试。`verify_world_scene_delivery_terminal.py --fault-early-release`在提前释放实际delivery pin时准确exit1，不用另一命令的pin掩盖该占用。

方法：diagnosing-bugs以当前实际退出路径构建准确红反馈；tdd在既有ConnectionOwner/MapOwner/pool Seam执行同快照红→最小候选绿；codebase-design将三处批次所有权集中在小Interface；writing-for-agents共置接线顺序、夹具与未验范围。本候选的固定双轴审查状态另见 `WORLD_SCENE_DELIVERY_SUFFIX_REVIEW.md`，没有该记录时不宣称已审。

## 剩余范围

原图/实体渲染、真实网络断线、商业负载、完整新手链和GUI均未验。此patch不解决maintenance清理报错后的恢复状态机，不替代主集成正在处理的loading断线retire_receipt，也不包含旧角intro修正。清理结果未知时继续fence是当前安全行为，自动恢复能力须另验，不能因新6组绿称全部终止路径已完备。

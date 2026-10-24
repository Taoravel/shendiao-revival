# 运行时碰撞缺口与显式current-cell Interface

2026-10-24。主集成是共享入口唯一写者。世界只修改 `world_movement.py`、`world_owner.py`，没有修改GameRuntime、runtime_storage、NPC模块、政策、服务或真人数据。

## 真实加密负例仍红

`verify_world_encrypted_collision.py` 在临时库以公开保存接口建立旧角1006/(360,2264)起点。实际加密登录收到普通A0场景包；同格MOVE/STOP到361/2264通过。再发真实STOP到1664/960，原maze byte11，当前GameRuntime仍接受并保存墙内目标。默认安全断言exit1，结构化 `world-encrypted-collision-verification.json` 先于断言保存；clear控制通过、运行时无战斗，源码前后稳定。

独立 `verify_world_runtime_collision_probe.py` 经实际MapOwner/SerialOwner也复现，bounds反例正确拒绝；`world-runtime-collision-parent-verification.json` 是父复跑。已定位两处接线缺失：runtime地图工厂没有注入原maze，MoveCommand没有可信movement_state。因此本次新增Interface本身**不等于共享碰撞已接好**。

## 原量化要求与接口

原证据WORLD_MOVEMENT_QUANTIZATION_INTERVALS已区分current、到达history及初始snapshot三种producer。普通有限、未回绕的非负current满足：X报告的投影float候选始终落在同一个24投影像素网格，等同wire X的16逻辑像素格；Y直接截断也保持当前格。正X全1..32767候选区间已穷尽核查。history按逻辑float±0.5，恰在格边界时可能跨格，不能把每个history整数当成当时真实占据格，更不能复算整条整数线段当连续轨迹。

新增显式选择：

```python
plan_movement(position, arrival_cell, kind, body, catalog,
    maze=original_grid, movement_state=trusted_state,
    collision_points='native_current')

command = MoveCommand(expected, request_id, deadline_ms, kind, body,
    movement_state=trusted_state, collision_points='native_current')
```

`plan_movement`与MapOwner传递同一小Interface。默认仍为 `reported_nodes`，旧调用行为不变。`native_current`要求明确maze及可信state；当前点按原mask查询，所有报文点仍检查bounds；MOVE目标只属意图，未因它而落盘，之后CHECK/STOP的墙内current会拒绝且不推进版本。历史碰撞及轨迹不由此放行成已验证，只是没有把不可反推的history整数强当精确占据格。

调用方选择native_current即声明使用已证普通actor current getter、有限、未回绕、地图逻辑坐标域。它不从报文推断特殊producer或角色状态；movement_state仍由角色/地图所有者的可信快照提供，不来自wire q64、NPC类型或随意常量。

## 主集成所需接线

1. 启动冻结原maze（prepare已有完整grids），由真实模板给所属MapOwner，不在移动热路径加载文件。
2. 按实际服务器发出的场景状态及已完成的角色/场景生命周期建立可信移动状态。原Scene成功普通A0可建立0，包括首次reason516015；1404、reason516023、加载失败/早退和后续特殊状态另验，不能套全图0。证据见WORLD_SCENE_MOVEMENT_STATE_RESEARCH。
3. 每条实际移动命令携带对应成员/epoch/地图版本的可信state，并显式选此producer合同。原资源/实例地址围栏、加载/开场门禁保持。
4. 先使上方真实加密安全检查转绿，再回归原自然MOVE/CHECK/STOP、全资源clear路径与普通传送。不把点地纠正用于更改原portal落点，也不宣称已验证速度、连续轨迹或特殊移动。

## 验证与审查范围

`verify_world_current_cell_collision.py`：Planner新keyword实际红→补实现，再MapOwner MoveCommand keyword实际红→转发后7组绿。原量化probe独立产生同一float输入的history(16,20)/current(15,20)边界对照；它是明确quantizer fixture，不冒称整条原鼠标/寻路可达性。覆盖默认兼容、显式历史边界、墙内current拒绝且版本不变、MOVE非到达、CHECK前缀、缺maze/state/非法模式与所有点bounds、32767个正X候选区间。

必要回归world_owner、owner_collision（302 grids）、plan、move_view、transfer_view、recovery_view全部通过。固定双轴审查另见WORLD_CURRENT_CELL_COLLISION_REVIEW；本交单不将待接共享或GUI写成已完成。新增字段是可信内部命令选项，无线包变更、默认放宽、热读或全局串行化。

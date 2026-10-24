# runtime join 在验证前撤销当前移动声明

2026-10-24，World 子研究只新增 probe/两份报告/本文；未修改生产/shared/所属Module/冻结source、未开GUI/服务/正式数据库或战斗。

当前优先来源为 `runtime/deployments/npc-repair-20261024T023920Z/source`。此为main所报新BASE，本研究没有查看实时进程/正式socket；不能把所报PID当作本研究OS确认。GameRuntime SHA `34f0b6dc6d7cf2d4fb1ddfb1e46be0ba3cad65ae9b61cff581dc33aba06a52bc`、runtime_movement SHA `0594837c886bb2902d3fd03476d5b9ca9a56a8d17bd70089513e1592c268f444`、runtime_storage SHA `9cdcc5cd708f9cc03441e85c393830151ebd7a0814ccedf6f7ed25237b546b43`。

历史r4 `world-collision-20261023T204238Z` 另独立运行同一最终probe，仍RED；两份1442文件manifest逐项比较，唯一差异为runtime_storage.py（r4为d23d811c…）。地图纯内存路径未使用storage操作，不把历史r4冒称当前BASE。

## 可执行反例

`verify_world_runtime_join_context.py` SHA `d87c3d4fbdd36f58843262e71184ebb8460186bd97862ea2496626e002fa60fa`。

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_runtime_join_context.py --runtime-source 'D:/神雕侠侣/revival/runtime/deployments/npc-repair-20261024T023920Z/source' --report revival/evidence/world-runtime-join-context-repair-base.json
```

实际exit1：`Runtime join revoked already admitted movement authority`。报告完整保留五例，不在首个缺口后停止观察。重复运行新BASE仍相同；历史准确r4报告为world-runtime-join-context-r4.json。两源实际模块路径/哈希、manifest前后SHA及全部1442生产文件前后均稳定。

每例都新建真实runtime MapOwner和真实SerialOwner，catalog来自该source，原1006 maze由原map.pfs读取（PFS Adapter核长度/CRC），没有手填maze或自选无碰撞fixture。先公开join，公开declare_movement，原scene_entry/location/body和normal_scene source精确匹配，再movement_will_send和movement_sent。**完成回调是显式受控服务器fixture，不是实际Writer.write/drain、ConnectionOwner、原生客户端执行或client ACK。** 没有直接塞movement私有字典或替换生产依赖。

随后每例先真实公开move_for_encounter STOP从1006/(360,2264)移动到(361,2264)、version1→2，以此确认声明确实能用。再只改变join操作，观察下一合法STOP到(362,2264)：

|变体|join结果|domain Location/cache|下一合法STOP|
|---|---|---|---|
|不再join控制|无|不变|成功，v3|
|加入不同role2控制|接受|role1不变|成功，v3|
|完全相同Position幂等重试|接受|完全不变|拒绝，Movement waits for exact normal-state delivery|
|同role旧epoch|Role already in map|完全不变|同上拒绝|
|同role同epoch冲突位置|Role already in map|完全不变|同上拒绝|

三个失败移动均未改位置/version/cache；随后仅用相同公开声明/完成Interface重新建立该当前位置的normal context，同一个(362,2264) STOP立即成功。这是解释性恢复控制，**原`later_move_passed`仍为false、最终安全断言仍exit1**；不以重声明掩盖错误join造成的撤权。

## 因果定位

按diagnosing-bugs构建实际可重复红信号，再以主源和互斥控制区分：

1. runtime join先对已在地图的role调用movement.leave，预测拒绝/重试join都不改domain/cache但清现有许可；本例与主源吻合。
2. domain.join改变了权威版本/位置，预测后续应出现位置不符/过期且快照有差异；两份精确快照不变，排除。
3. 原maze阻挡、首声明未生效或下一STOP格式错误，预测无操作/不同role控制也失败，或重新声明仍失败；这些控制均通过，排除。

准确 `game_runtime.MapOwner.handle` 的join分支先读取positions，若已有cache便执行`movement.leave(domain.location(role))`，之后才`domain.join(...)`。`runtime_movement.MapMovement.leave`删除pending/context；`current`在下一公开move命令中报缺精确投递。无须修改原图、扩许可或忽略异常才能解释结果。

## 接线要求与未验范围

由main唯一共享写者修复：验证join的完整当前身份及幂等结果后再决定是否发生真实成员替换；拒绝join及精确幂等retry保持已接受movement context。旧join回调不能先清当前movement/member binding。真正换成员仍需按生命周期撤权并以新真实投递重建；不能对合法替换偷偷沿用旧许可。

建议在后续member接线的新准确候选上原样跑此probe，保留控制/三缺口分支及真实拒绝语义；本研究不自行改shared、重启或把该修正夹入repair。当前尚无metadata binding运行时接线，所以这里只证明现有movement context撤销缺口，不声称已经观察到新member binding被删除。

未验证：完整实际登录、网络write/drain、自然触发这些join调用的用户路径、GUI动作、持久状态、收费/战斗、所有地图与商业并发容量。方法research只用准确冻结主源及原资源，diagnosing-bugs以单变量公开命令控制定位；产物与边界在本文共置。整个地图/场景/怪物目标仍未完成。

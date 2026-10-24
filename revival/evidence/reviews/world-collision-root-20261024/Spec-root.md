# Spec 独立审查

缺失0、额外行为0、错误实现1；未读取另一轴结论。

**[P1] 已付开场结束包重新授予normal声明。** 政策.2 L22要求“Only matching completed intro transaction may request a fresh normal0”，裁定L9限定“匹配CEnd的真实任务事务提交后”。但候选 `game_runtime.py:555–567` 每次newbie_finish返回均无条件追加 `normal_location_message('authorized_intro_completed')`。准确release依赖 `task_newbie_chapter.py:307–316` 在chapter已completed时仅核原movieID，跳过当前播放许可/位置/期限校验并返回evidence=None；候选 `runtime_storage.py:272–275`已明确让此paid分支不发消息。故完成开场的角色移动/换图后，无当前IntroTicket重发原CEnd仍获得当前地图的新location0，替换pending/当前声明并改变context代际；原消费者会重设目标，这不是纯历史确认。应仅在action.evidence非None的新匹配完成时追加声明，paid保留当前读取、不生成新许可或位置命令。无需伪造服务器DTO即可触发。

其余核对：政策L25–28的精确身份/投递及撤销，对应 `runtime_movement.py:75–120`、`game_runtime.py:389–408/1003–1052/1195–1227`；初入不依赖CG ACK，1404独立位置命令，transfer/battle/close及旧代围栏均有对应路径。L32–33对应 `world_movement.py:53–84`、`game_runtime.py:250–263` 的native_current墙拒绝与同Owner原子advance，未删正常地图。

方法：本批重读code-review/codebase-design，沿ARCHITECTURE的map/role/connection Interface追踪真实caller与回执；非Git，仅固定6项/635diff行，依赖仅取该release/source。6候选+4BASE SHA、2新增空基线、diff、实际发布manifest/candidate及seal均匹配scope；scope前后SHA `aeb84aa8cc2471c7431a73e4cfb3bbbcb344db91fb150cadee226e9162d926c3`不变。

未执行代码、DB、服务、GUI或战斗。发布门槛另未闭合：准确候选302图日志虽有功能all_passed，随后因harness/workspace/tasks.py越出冻结import范围exit1，最终result缺失；不得视为准确302回归通过。此为待补验收证据，未误报为地图源码删减。

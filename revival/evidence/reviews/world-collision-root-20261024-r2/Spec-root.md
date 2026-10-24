# Spec 独立复审 r2

缺失0、额外行为0、错误0。原P1已修复；保留r1报告，未读取另一轴结论。

- 政策.2 L22“Only matching completed intro transaction may request a fresh normal0”：候选 `game_runtime.py:568–571`现仅在 `committed.action.evidence is not None` 时追加location0。准确r2依赖 `task_newbie_chapter.py:311–316`的completed replay返回None，`runtime_storage.py:272–275`同样返回空消息；因此无当前播放票据的旧CEnd不再生成新声明或重设目标。新匹配完成仍经过持久事务、最终角色发布，再取得当前权威位置声明。
- L28“close…revoke pending and admitted contexts”：候选L435–438在close持久等待前显式失效，MapMovement.invalidate递增context代并删pending/current，最终L472移除成员；旧回执不能重装。L25–26的“message kind and exact body”“precise logical message…drained”由L1211–1229补全：只接两种精确barrier类型，队列kind/body须匹配声明；SceneSendBarrier另须ENTER_SCENE及其原body，检查在write前，成功drain后才确认。
- 特殊初入L1029–1034仍是非barrier Scene先发送、随后独立location0；特殊transfer L952–958/1036–1056仍待精确Scene完成再生成独立声明。普通transfer带原movement声明，其他非barrier消息保持旧路径。未变五文件SHA一致，沿用r1对native_current、墙拒绝、原子advance及302地图范围的完整静态审阅。

方法：沿用完整code-review/codebase-design，以map/role/connection真实Interface追踪授权和回执；仅固定候选及对应release/source依赖。非Git，6candidate+4BASE+6previous SHA、两新增空基线、两diff、manifest/candidate记录及seal均匹配scope。scope前后SHA `6bdd982c5d9946669cfaa40e6962e2909afbda2c74cc91c1c59dd04dc810e721`不变，6源码末次再核亦一致；seal `e958c9086490a2ad2bdeaaf7d4f73c3d1301260db0abaf078b4cec0b9a5b2733`。

仅静态复核6项652diff行/38行增量，未执行测试、DB、服务、GUI、真人或战斗。准确302图及新增strong-earlyACK/terminal最终运行证据仍待集成方闭合；本报告不声明这些已通过，也不替代发布门槛。

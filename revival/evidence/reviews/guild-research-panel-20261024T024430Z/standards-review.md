# Standards

**Standards 1；P0=0、P1=0、P2=1、P3=0。**

P2：`guild_runtime.py:184` 的 `except (ValueError,Backpressure,StaleEpoch,TimeoutError)` 未覆盖提交后读取 Adapter 的 `sqlite3.OperationalError`。独立反例令 `guild_audience` 抛“database is locked”：调用方收到 OperationalError，但研究经验已持久增加7，恢复读取后重放返回 accepted=7。该新增路径违背 ARCHITECTURE“数据库故障触发局部……恢复”“重试返回既有结果”的错误隔离要求，也违背本 Module 已声明的“展示故障不把提交伪报失败”。应仅在提交成功后的展示阶段登记此存储故障并返回既有结果，保留提交本身错误向外传播。

沿既读 code-review、codebase-design 与完整 Fowler 启发式核查；其余无硬标准或判断性 smell 发现。7候选、4基线、675依赖、7规格、644资源与差异/原指令哈希匹配。独立公开 Peer 六组及原生三组全绿；上述故障补查见 standards-independent/checks.json。26脚本的完整最终索引在落报告时尚未生成，未以部分输出冒充完成。

无 Git，使用第21批固定源/精确差异。未验正式维护源、生产曲线、NPC、GUI或容量；未改固定源、游戏、真人库或服务。

# Spec

Spec：P0=0、P1=0、P2=1、P3=0。

**[P2] 提交后的展示读取故障被误报为奖励失败** — `guild_runtime.py:179–184`。契约13行要求“不把提交伪报失败”。`award_guild_research`已提交后，`guild_audience`读取可抛`sqlite3.OperationalError`，但except未覆盖SQLite错误。独立真实Owner/Peer反例：仅在展示读取边缘注入该错，调用方抛异常，研究经验已增加5；原查询读回5，重放取得已提交凭据。应将已提交后的持久化展示故障记延后并返回receipt，提交失败仍须向上传递。

其余无可行动的缺失、范围夹带或错误。独立整家族代次变化、同成员代次旧wake过滤、租约优先授权、已有研究但运行时未配置时只清cache，以及完整原刷新接收器均通过。

7候选/675依赖/644资源/7规格及diff/原证据hash一致；26脚本原检查全绿，不覆盖上述反例。固定结果与导入另逐hash核验。证据：spec-independent-result.json、spec-fixed-results-audit.json。未改source；正式维护/参数/NPC/GUI仍未验。

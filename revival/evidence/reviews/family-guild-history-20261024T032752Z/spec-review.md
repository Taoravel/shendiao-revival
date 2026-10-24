# Spec

Spec：P0=0、P1=0、P2=1、P3=0。

**[P2] 容量拒绝的家族被游标越过，可持续饥饿** — `family_maintenance_runtime.py:78–84`。契约19/21行要求有界公平扫描及按family合并；当前先把cursor推进至整批末尾，再因容量break。独立实际Store/Runtime：同分区、limit1/batch2，首次处理1后跳过17；新到33/49时只处理33、cursor49；再到65/81时只处理65、cursor81。17一直pending；若持续高ID到达就不绕回。应仅推进已创建或已运行任务的条目，保留首个未调度位置。

其他无可行动发现。独立105次真实传位使旧加入历程退出最新100窗口后，旧archive仍可ack；未ack前后事件拒绝，重启/重放不增revision，权限与两类索引seek通过。

9候选/692依赖/647资源/6规格及精确diff/hash一致；28脚本全绿、162导入含runner逐hash核对。该绿未覆盖上述反例。证据及candidate绑定见spec-review.json。未改source；跨库、template7、GUI/NPC与商业容量未验。

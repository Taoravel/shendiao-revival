# Spec review

2026-10-24。方法：读取 `code-review`、AGENTS、ARCHITECTURE 与 DESIGN_AUTHORITY，按父任务明确的特殊出口诊断规格逐项核对。没有仓库提交历史；使用 `git diff --no-index` 比较实际保存的 resource audit before/current，新 runtime probe 按空基线审新增。只写本轴报告及独立执行证据，未改生产、共享入口、冻结源码或运行服。

## Findings

**0 项。**

资源修正只将原包路径按无歧义 casefold 解析，并记录实际名称与总行数。冻结报告对应 304 地图、142 表、6275 行；1412/1413 两处大小写解析均明确保留。九个出口原 goto 与目标坐标、原 NPC 数据继续作为研究事实，不引入替换落点或碰撞策略。资源脚本 SHA `221cbfc6200bdbcb40552164a3b7ffacdbaabacb3ce59e09cedd5884da664fd1`。

Runtime probe 只选择原生报告实际产生消息的1301/1305两例；源邻近点明确是临时数据库夹具。真实加密入场、源 MOVE/STOP、换图及目标原生 scene 解码后，逐个原样回放 MOVE/CHECK/STOP 的 `kind/body_hex`，没有替换原 blocked landing。首 MOVE 拒绝且位置/版本不变，之后 CHECK/STOP 准入并达到原报文最终位置、落盘的断言与规格一致。其余七例不生成虚构回放；范围标记继续排除 GUI、原服务器和策略修复。

## Verification and limits

已重算 runtime probe 的冻结与实际执行脚本 SHA，均为 `44a94a2e807a990e06bd9ae28a23386ee571cb6b250fc21959aec0b51187d61e`。独立执行同 SHA 工作区脚本、准确 npc-repair source/harness 与冻结 native report，exit0：`observed=2, reached=2`；证据为 `spec-runtime-independent.json`，全部实际回放报文字节与冻结 native report 逐项相同，生产及输入稳定。没有独立复跑整个资源扫描或原生对象图，不把静态审计及两例回放当九例已恢复或客户端实测。

Spec findings: **0**。

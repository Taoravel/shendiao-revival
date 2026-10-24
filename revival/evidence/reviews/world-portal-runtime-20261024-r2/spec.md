# Spec review: original NPC resource absence

2026-10-24。按 `code-review` 的 Spec 轴核对父任务给定的普通门户验收子规格。用 `git diff --no-index` 比较保存的真实 before/current；before SHA `c902399b21ddf36ce36987d41e56b097850b54e1d226b55f5136679755eac399`，current SHA `f3a0cb22a90a2a44d8dabd1195544b71c5c5da1386f14d96265552e2712d3dcd`。工作区原脚本仍为 before SHA，持续运行的 r1 作业未被本变更改写。

## Findings

**0 项。**

改动仅将原 `npc.xml` 查询改为无歧义 casefold 解析，并返回表名及原字节 SHA；缺原表时返回严格空列表。实际解码的全部目标 NPC 记录仍无条件经过 `records == expected`，所以缺原表但实际收到 NPC 的情况会失败，不会跳过比较。原有场景原生解码、加密传送、位置/版本/完整地址落盘、同 runtime 与冷 runtime 重登断言均未变，生产碰撞及目的坐标也未改。

联合覆盖方案符合本次规格：保留 r1 原始失败报告及其中真实完整通过的病例，再以 r2 对其余失败病例逐对执行同一完整链。最终应核对准确相同的候选 manifest、原包及 catalog 哈希；按精确源/目标对和见证比对集合、排重后覆盖全部212组，并关联每例原报告与脚本版本。该方案应称两批联合覆盖，不能称单次全绿；目前还不能证明最终212已完成。

## Verification and limits

只读解析父执行的 r2 pilot：1007→1014、1230→1231 两例均完整通过，输入及生产稳定；前者原表72 NPC，后者无表且实际0 NPC，两重登均通过。独立提取冻结 `expected_npcs` 函数，在准确候选 PFS/BXML 与原包上执行：1231返回 `([], None, None)`；1014返回72条且原 entry/hash吻合；构造大小写冲突条目时明确拒绝。此独立检查只执行资源期望函数，未复跑完整网络 pilot。

全212原始作业及剩余病例 r2 终局、联合证据绑定与 GUI 尚待父任务验收。本轴只写本报告，没有修改生产、运行服或冻结源码。

Spec findings: **0**。

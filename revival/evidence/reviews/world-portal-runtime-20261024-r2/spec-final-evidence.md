# Spec final evidence review

2026-10-24。方法：沿用 `code-review` 的 Spec 轴，独立核验 `world-portal-runtime-combined-acceptance.json` 及其引用的原报告、冻结脚本、准确候选和原包；本次不重跑完整网络作业。新增的 `spec_final_check.py` 只读所有输入，写本轴检查结果，实际 exit0，结果在 `spec-final-evidence-check.json`。

## Findings

**Open findings: 0。**

独立用冻结 r1 的见证生成函数、准确候选生产模块、原 maze 与冻结 helper 重新得到212组普通见证。第一批实际212例无重复，199例完整通过，余13例均在原 NPC 表读取处为 `KeyError(.../npc.xml)`，原红报告保留；第二批选择集合恰等于这13例，没有漏项或用控制例替代。所有补跑例都完整通过，严格0 NPC、完整实例存档及同 runtime/冷 runtime 重登断言均已到达。

联合212例逐对的源图、传送格、源邻点、入口像素、目标点、目标合法一步与独立重建结果完全一致；每例所选原报告、存档版本、NPC数量及记录摘要与 receipt 相同。两批与原配置绑定报告的 manifest、原包哈希一致；实际重新核验全部1442生产文件、catalog哈希、原包、依赖源和 receipt 全部引用产物哈希。r1 的工作区脚本路径在作业结束后已更新为 r2，本轴按真实保存的 `verify_world_portal_runtime-before.py` 核验旧 c902 SHA；r2按冻结 f3a0 SHA核验，没有把后来工作区内容冒认为旧执行源。

receipt 明确保留 `single_all_green_run=false`：这是199＋13的两批联合覆盖。15组特殊入口集合与原排除集合完全相同；两个 blocked-native 回放没有被计入普通212，也没有把其余特殊入口或 GUI 标成恢复完成。

## Completion boundary

该 receipt 足以支持“同准确候选下212组普通门户的上述离线加密运行时链已联合覆盖”。它继续保留显式源位置/实例采用夹具，不能证明自然全程可达、全部6275格、客户端加载确认、GUI、新手全程或整个地图/怪物目标完成。没有修改生产、共享模块、运行服、冻结源及原报告。

审阅 receipt SHA：`83771772162da7675637f5fe681cab656c17e7130ed1a3ba97229e0e5d5ef718`。

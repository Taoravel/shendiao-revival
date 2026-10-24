# Standards

硬违规0；heuristic判断项0。仅审4个新增固定文件，上批无同名base；非Git，无提交列表。SHA-256实核一致：

- npc-identification-query-v1.json：67a06fea785edd54e76a3490ee49f9ff5d1297cb1809be1313f6081ab5dae94e
- newbie-dream-return-v1.json：fd369d20ba847764eb6436f83819628b52f7f8bc54c743669c708d22edf304f4
- NPC_IDENTIFICATION_QUERY_DECISION.md：d39b04103c4ff0f1d6db713629629a3fd0f63595a5a03232c558eaa0ba42023e
- NEWBIE_DREAM_RETURN_DECISION.md：e9f29a133785c2f08b6b8d4da6ef0882092abd8f3b0870bc27735ed73dc1294b

采用code-review／codebase-design／writing-for-agents，依据AGENTS、ARCHITECTURE、DESIGN_AUTHORITY核查。两JSON均为唯一参数源；原证、inferred与designed及实施／部署分级明确。query保留地图准入与角色只读事务，未知档拒绝无迁移；dream-return明确事务外地图／网络等待、位置／任务／奖励／凭据原子决策、幂等当前读、提交后目标唯一与恢复、实际票据终止后投影回收。完成条件可逐项判定，未把设计补全误报缺证。

12项Fowler smell逐项判断，无可行动问题。仅静态阅读／哈希核对；未运行DB、服务、GUI、真人或战斗，领域实现、共享接线及运行验收仍未证明。

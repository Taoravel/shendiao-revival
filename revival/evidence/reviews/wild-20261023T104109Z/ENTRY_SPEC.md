# 入口补充 Spec（仅静态）

范围：entry-scope.json的5文件，前后hash全匹配，无Git提交。沿用code-review、codebase-design，覆盖真实移动→受理→战斗→终局、失败重试、断线及新lease恢复；资源Module另审。

1项部分实现：[P2] 断线遗留战斗所有者。需求3“独立有界BattleOwner调度”、6“断线…按draw零胜利奖处理”。game_runtime.py:844–852在非终局checkpoint失败后保留pending；此时断线，338只重试pending，跳过真正close。若重试成功，finished仍空；1179–1180关闭并移除角色，却保留rt.battles及其邮箱任务。新lease可恢复资产，但旧战斗永久残留，反复发生会累积。应独立清理战斗所有者并保留持久恢复依据。

其余无确证错误或越界。仅静态，未运行战斗、DB、服务或GUI。

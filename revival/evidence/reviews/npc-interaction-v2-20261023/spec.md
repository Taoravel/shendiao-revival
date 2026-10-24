# Spec

需求缺失：0项。额外范围：0项。错误实现：0项。

按已读code-review Spec、codebase-design及架构约束检查六文件；十二个base/current真实字节SHA均匹配manifest，固定来源以manifest为准，无Git提交。

默认v2严格冻结16/13/169，唯一allows接受三段非负整数逻辑位置，分别整除16后比较格差平方和<169；无摆放override，不用208像素圆。Scene/Lifecycle共用predicate；v2.radius_for拒绝，构造旧32只解析为None。显式v1及无rules旧圆保留。审计为v2记录模式与空半径，不伪造标量圆。

独立优先导入冻结current：cell8组、显式legacy8组及旧Scene/Lifecycle回归全绿。覆盖同捕获血手印q64/合法62点、两个普通64点、164/169边界、格内偏移及非208圆双反例、严格配置/原资源、当前证明/租约/完整地址/移除/generation。接近判断未新增资产、任务或服务授权。

方法影响：从共用公开Interface追踪规则到两消费者及审计，独立字面边界验证避免用实现反推预期。产物为本报告；仅领域/纯验证，未证明共享自然intro链、固定发布或GUI，普通原碰撞查询仍是研究fixture。未改其它源码、政策、真实库或服务。

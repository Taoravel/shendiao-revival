# Spec

0项可确证需求缺失、越域或错误实现。

沿用code-review独立Spec轴、codebase-design的收件人范围Seam，审固定baseline/source及两份差异；2个baseline、4个candidate SHA256全部匹配，当前spec亦精确匹配冻结0899fb42…，未改冻结内容。非Git，无提交列表。

PRIVATE_SCENE_SCOPE_DECISION.md:13要求“仅关键字字段，默认None”“保持原四位置参数及…继承构造兼容”；source/social_owner.py:66–77正确采用kw_only冻结字段、严格非bool/范围验证及public归一，private完整tuple保留。Spec:15要求“旧范围…不能掉回…target.offer”“None保留原渠道路径”；source/social_runtime.py:78–120先核epoch/key，经原关系过滤后await共享hook，缺hook/拒绝均计数且直接返回，None沿原target路径。子类展开保留原scope，未混入guild.initial或组织闭包增量。

仅静态审查与哈希核验，未执行代码、DB、服务、GUI或战斗。共享fanout、ticket/pin、scene_token及连接drain全链属于主集成另验，本结论不证明真实私有聊天隔离完成。

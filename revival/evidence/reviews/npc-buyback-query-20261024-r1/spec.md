## Spec

结论：漏项/部分实现 0，范围越界 0，实现错误 0；只读候选符合本片规格。

方法：沿用完整 code-review、codebase-design、tdd，读取本批 AGENTS/架构/来源约束；核四文件实际差异。固定点为发布5bf→5b25096c，新文件空BASE，坏JSON原型独立封存，没有虚构Git引用。manifest SHA保持 `075e967157188aaf5dcf0fa491cfcfde768a13630ac4ccbcb700692a4aae0bd5`。

“只SELECT本角色+本NPC……不建表、不扣费”由独立读事务、精确过滤、已知钱包/租约检查及连接级query_only实现；调用方事务的authorizer实测拒DML/DDL。capacity+1用于拒绝越界，TTL只筛不删。完整目标key、服务2、owner/epoch、deadline及缓存字段校验满足规格；空缓存返空包，不制造货架实例，也不扩大214权限。

独立四项完成：`missing_query_red`、`bad_record_red`分别精确得到exit1，非功能绿灯；`readonly_query`13组及`legacy_sale_runtime`原加密Peer12组通过。每项前后校验12本地/3083外部输入。正向缓存由公有sale实际生成；畸形记录只对真实行临时故障注入并回滚。隔离、未知钱包、当前回购后状态、旧lease及原codec均通过。

`_encode_listing`只抽取原纯编码；原交易仍经_cache清理，sale/buyback费用、revision、fingerprint和凭据流程未变。与新查询共享投影符合规格所述后续价格政策接点。

“查询采用c0434、service2准入”仍是待root采用提案；三项显示价/扣款差异未修复。当前成员/投递二次校验、shared原query4路由、GUI、费用政策合审与部署属于明确未完成门槛。本报告不批准上线，不把局部只读检查当全部NPC恢复完成。

Spec：0项，最高严重程度：无。

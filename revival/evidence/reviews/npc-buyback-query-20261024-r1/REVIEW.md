# NPC只读回购查询：固定双轴审查

## Standards

结论：文档规范违例 0；可行动的 Fowler smell 0。

采用 code-review、codebase-design、TDD 方法，完整审阅真实发布 5bf→候选 5b25096c 及新增文件空基线；观察到的 4fc 坏记录原型单独保留。manifest SHA 与指定 075e9671… 一致，未虚构 Git 提交。标准依据为冻结 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY、GLOSSARY 和十二项 Fowler 启发式；仓库未发现 CODING_STANDARDS/CONTRIBUTING。

`npc_shop_sales.py` 将只读查询与原 `_cache` 清理分开，符合 ARCHITECTURE 的角色数据所有权、明确事务和有界读取要求：校验当前 owner/epoch、期限及已知钱包，SELECT 按角色/NPC/TTL 限定并读取 capacity+1 检查溢出；调用方事务不触发清理或扣费，独立连接启用 query_only。缓存实例来源在编码前校验，未为未知数据补默认资产或钱包。纯 `_encode_listing` 由新查询和原交易刷新共用，避免重复价格投影；原清理、费用、凭据流程保持。新 query 不授予214、不中途发送，也没有新增共享写者、全局串行器或热路径 DDL。

独立结果为 **2 项正向通过 + 2 项真实 RED 重现**：readonly_query 的 13 组公开行为通过；legacy_sale_runtime 的准确原加密 Peer 12 组通过。missing_query_red 与 bad_record_red 子进程分别确实 exit1，不计功能绿灯。每项前后核对 12 本地及 3083 外部固定输入。真实 sale 缓存、原 c0434 往返、查询期间 SQL 写入/表 DDL 拒绝、跨角色/NPC/权限/TTL/未知钱包及实际 buyback 后当前读取都有独立证据，位于 `verification/standards/`。

依据 DESIGN_AUTHORITY 的交付分层，service2 准入/c0434 选择仍是待采用提案；费用显示与扣款差异、shared 原 query 路由、投递后围栏、GUI、部署及完整 NPC 恢复均未由本片完成。本审查未修改固定源、生产、旧封签、真实库或服务。

Standards：0 项，最严重问题：无。

## Spec

结论：漏项/部分实现 0，范围越界 0，实现错误 0；只读候选符合本片规格。

方法：沿用完整 code-review、codebase-design、tdd，读取本批 AGENTS/架构/来源约束；核四文件实际差异。固定点为发布5bf→5b25096c，新文件空BASE，坏JSON原型独立封存，没有虚构Git引用。manifest SHA保持 `075e967157188aaf5dcf0fa491cfcfde768a13630ac4ccbcb700692a4aae0bd5`。

“只SELECT本角色+本NPC……不建表、不扣费”由独立读事务、精确过滤、已知钱包/租约检查及连接级query_only实现；调用方事务的authorizer实测拒DML/DDL。capacity+1用于拒绝越界，TTL只筛不删。完整目标key、服务2、owner/epoch、deadline及缓存字段校验满足规格；空缓存返空包，不制造货架实例，也不扩大214权限。

独立四项完成：`missing_query_red`、`bad_record_red`分别精确得到exit1，非功能绿灯；`readonly_query`13组及`legacy_sale_runtime`原加密Peer12组通过。每项前后校验12本地/3083外部输入。正向缓存由公有sale实际生成；畸形记录只对真实行临时故障注入并回滚。隔离、未知钱包、当前回购后状态、旧lease及原codec均通过。

`_encode_listing`只抽取原纯编码；原交易仍经_cache清理，sale/buyback费用、revision、fingerprint和凭据流程未变。与新查询共享投影符合规格所述后续价格政策接点。

“查询采用c0434、service2准入”仍是待root采用提案；三项显示价/扣款差异未修复。当前成员/投递二次校验、shared原query4路由、GUI、费用政策合审与部署属于明确未完成门槛。本报告不批准上线，不把局部只读检查当全部NPC恢复完成。

Spec：0项，最高严重程度：无。

两轴分别结果：Standards硬违反0、Fowler判断0；Spec0。父和两位独立审查者合计6正向检查（每人readonly13组、原加密Peer12组）以及6实际RED（缺Interface与坏JSON各3次）；RED不计功能绿灯。每项12local/3083external保持。费用一致性、准入政策采用、shared/GUI/部署及总NPC目标未完成。

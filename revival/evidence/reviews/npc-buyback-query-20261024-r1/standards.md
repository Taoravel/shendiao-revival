## Standards

结论：文档规范违例 0；可行动的 Fowler smell 0。

采用 code-review、codebase-design、TDD 方法，完整审阅真实发布 5bf→候选 5b25096c 及新增文件空基线；观察到的 4fc 坏记录原型单独保留。manifest SHA 与指定 075e9671… 一致，未虚构 Git 提交。标准依据为冻结 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY、GLOSSARY 和十二项 Fowler 启发式；仓库未发现 CODING_STANDARDS/CONTRIBUTING。

`npc_shop_sales.py` 将只读查询与原 `_cache` 清理分开，符合 ARCHITECTURE 的角色数据所有权、明确事务和有界读取要求：校验当前 owner/epoch、期限及已知钱包，SELECT 按角色/NPC/TTL 限定并读取 capacity+1 检查溢出；调用方事务不触发清理或扣费，独立连接启用 query_only。缓存实例来源在编码前校验，未为未知数据补默认资产或钱包。纯 `_encode_listing` 由新查询和原交易刷新共用，避免重复价格投影；原清理、费用、凭据流程保持。新 query 不授予214、不中途发送，也没有新增共享写者、全局串行器或热路径 DDL。

独立结果为 **2 项正向通过 + 2 项真实 RED 重现**：readonly_query 的 13 组公开行为通过；legacy_sale_runtime 的准确原加密 Peer 12 组通过。missing_query_red 与 bad_record_red 子进程分别确实 exit1，不计功能绿灯。每项前后核对 12 本地及 3083 外部固定输入。真实 sale 缓存、原 c0434 往返、查询期间 SQL 写入/表 DDL 拒绝、跨角色/NPC/权限/TTL/未知钱包及实际 buyback 后当前读取都有独立证据，位于 `verification/standards/`。

依据 DESIGN_AUTHORITY 的交付分层，service2 准入/c0434 选择仍是待采用提案；费用显示与扣款差异、shared 原 query 路由、投递后围栏、GUI、部署及完整 NPC 恢复均未由本片完成。本审查未修改固定源、生产、旧封签、真实库或服务。

Standards：0 项，最严重问题：无。

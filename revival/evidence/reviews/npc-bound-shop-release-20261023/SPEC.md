# Spec

0项可确证缺陷、遗漏或越权。

沿用code-review独立Spec轴、codebase-design的钱包/库存/来源同事务Seam，审manifest固定4项输入；8个base/current哈希均匹配（新文件base为空），非Git，无提交列表。

NPC_SHOP_BOUND_PAYMENT_DECISION.md:9要求“总价只扣bound_silver，产物binding1”；:11要求“mode0旧指纹字节配方保留”“重发读取当前余额/背包”。current/npc_shop_payments.py:23–43冻结精确两配方；npc_gameplay.py:136–173保留合法service2/原货架正价、数量及旧mode0五元组，仅给mode1追加配方意图；:174–200将真实扣款、绑定grant、领域凭据、source hook及当前回复预编码留同事务，paid不重复付款发物。currency-v1.json:12–17只新增bound_silver/npc_shop_bound，无现金替代、混付或其它币种开放。

配方明确designed，未误标完整原服事实。仅静态审查，未执行代码、数据库、服务、GUI或战斗；部署后真人显示、运行现场及其它玩法不由本报告验收。

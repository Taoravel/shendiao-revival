# Spec

0项可确证缺陷、遗漏或越权。

沿用code-review独立Spec轴、codebase-design的公开钱包调用方事务Seam；核原生研究→端游资料边界→designed配方，未把mode1已证等同完整原服配方。manifest四个current及唯一base的SHA256均匹配；非Git，无提交列表。

current/evidence/NPC_SHOP_BOUND_PAYMENT_DECISION.md:9要求“总价只扣bound_silver”“两币不能混付、替代或自动兑换”，:13明确“实现仅增currency.1的独立用途”。current/design/currency-v1.json:12–17仅给bound_silver增加npc_shop_bound，现金及元宝用途、revision保持；现apply_currency逐币用途校验继续阻止混付/替代。新付款政策:26明确wallet-only激活范围，未实现或宣称NPC发物。

current/verify_currency_bound_shop.py:35–65静态覆盖500→200、现金1000、同键/冲突、用途拒绝、晚错同键150→50及新旧租约。未执行验证，未改生产；NPC库存/绑定实例、共享路由、发布及GUI仍待独立验收。

# 普通 NPC 绑银购买发布

2026-10-23 20:03:09（北京时间），精确候选 `npc-bound-shop-20261023T115742Z` 已部署为 PID39796，唯一监听 `127.0.0.1:28993`。后续部署先读取 `latest-deployment-verification.json` 并核对实际进程；本文记录本次发布，不代替实时身份。

## 行为与范围

当前合法普通商店支持原请求 mode1：按原正价只扣绑银，产生绑定物品；mode0 原银两支付及历史凭据保留。数量、货架、服务许可、余额和背包约束仍适用。设计依据及完整事务契约见 [NPC_BOUND_SHOP_INTEGRATION.md](NPC_BOUND_SHOP_INTEGRATION.md) 与 [NPC_SHOP_BOUND_PAYMENT_DECISION.md](NPC_SHOP_BOUND_PAYMENT_DECISION.md)。

固定基线为实际原 PID44084 的 `npc-close-master-commit-20261023T113819Z`。仅4份生产输入变化、194行差异：npc_gameplay.py、npc_shop_payments.py、design/npc-shop-payments-v1.json、design/currency-v1.json。shared 与野外原字节继承，师父武器卡、退出、训练师菜单和关仓修复保留。

## 已完成的验收

1. 同一真实加密 Peer/RoleOwner mode1 反馈在原44084固定基线准确失败，新候选通过；当前余额、绑定隔离、重复与冲突、满包/晚错回滚和失败键重试均通过，实际执行旧发布产生的 mode0 凭据可兼容重放。
2. 候选10项必要检查绿；精确候选独立 Standards/Spec 均0项，并独立复跑两条绑银检查13组。固定报告为 `reviews/npc-bound-shop-release-20261023/REVIEW.md`。
3. 停服前核原进程身份、唯一监听及 Established=0，完成一致备份后切换。启动后1427份源码/配置哈希与启动记录匹配；版本601握手、未认证心跳及数据库 quick_check 通过，107张既有表（含 sqlite_sequence）逐行不变。

机器证据：`npc-bound-shop-deployment-verification.json`；停机一致备份：`runtime/deployments/npc-bound-shop-20261023T115742Z/accounts-at-stop.sqlite3`（相对 revival）。两份 candidate 元数据已标为 deployed/PID39796。发布4输入现可解冻做后续批次；运行固定副本保持不变。

## 未验范围

未打开客户端、真实认证或执行战斗，实际商店画面仍待用户验收。NPC生命周期、私有完整地址与血手印、care、新角色资源授权及v2均属于后续独立批次。本次未改真人角色/任务、删除角色、迁移钱包或自动发钱。

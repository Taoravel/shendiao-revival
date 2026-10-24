# 采用元魂最终属性后的成长动作：下一实际纵片

2026-10-24。前批 `pet-soul-final-totals-batch.json` 已审当前完整14合计、共同读取、原唯一HP/MP、实际穿脱/2符/返还/药物/裁剪/死亡及人物root source组合；不是完整玩法或所有成长操作完成。新规则实例的旧成长writer目前主动拒绝，未采用实例仍使用原路径。全量目标active，下一工作直接解除正确的成长缺口，不能删防护或让旧裸caps writer通过。

## 第一条真实验收

沿 `verify_pet_soul_final_asset_cycle.py` 已有真实role/pet/source/sole HPMP场景，当前宠物L1、太阳珠cap202，明确治疗到195HP/30MP（HP高于裸上限157仍合法）。实现 source-aware XP结算：原L1阈值200，授200后L2/xp0；相同designed成长底图裸cap169/MP71，太阳45→最终cap214，按明确成长cause保留缺失量7而非穿脱绝对值cause，得HP207/MP34。死亡0升级仍0。完成点是实际state/source/库存版本/原+新必要凭据与原生编码同事务，可重登/paid只读当前，并非只写一个plan或改现有测试的expected。

随后同一Seam补capped XP与加点：L1授450、cap2后L2余250，不能丢弃超额；L1体力+1使太阳后cap202→212，当前HP80→90保持缺失量。负数、bool、超额潜能、旧版本/旧epoch/缺基线、来源变化拒绝；真实写失败和完整native编码后异常全回滚。人物70/40/100仍保持，不把宠物XP当人物成长。

## 必须沿用的 Interface 约束

- 成长/加点的数学与资源调整分开。`GrowthRules._change` 当前把HP与**裸**旧caps比较，不能直接拿已采用的HP195调用它，也不能用伪造HP0掩盖真实资源。先从既有XP/分配数学提炼公开、资源无关的进度计划，原默认award/allocate复用同一计划；新writer再用真实完整旧/新最终caps处理唯一资源。避免复制XP循环或另建HP/MP。
- `load_pet`/原source reader/pending守卫继续工作；新writer复用当前metadata完整CAS、source stamp、库存CAS与caller事务。未来血脉/石头/蛋糕/进化/返生等也须source-aware闭合，不能只绕过当前`is_adopted`拒绝。
- 旧`inventory_pet_growth_receipts`存在真实历史支付。新入口先经其所属Module公开的只读意图校验，合法旧paid只读**当前**最终profile，不能按老receipt重放XP/HP或把同一旧请求换新ID再发一次。新source-aware凭据与原receipt必须有明确互斥/迁移和冲突规则；新的source-aware writer不应随手复制私有fingerprint/写对方表。完整设计要先用“采用前已付→采用后重试”实际临时库案例定住。
- 客户端无重试ID的请求仍由角色所有者固定稳定server身份；旧长逻辑键需要稳定派生短资源键时将完整逻辑身份纳入fingerprint，不截断。提交后才由连接所有者投递。

## 其它当前未验门槛

五项aggregate比例native scale依旧unknown：`PET_SOUL_RATIO_DISPLAY_RESEARCH.md` / `pet-soul-ratio-display-research-batch.json` 的152原码案例只证明逐珠tooltip读取原配置×100/取abs/`%d%%`，没有Pet aggregate getter。保持server exact signed Fraction，不据其猜×100或×10000发aggregate包。普通battle复制只证明核心字段；完整比例/魔法/命中/躲闪/防御穿透与终局资源还需battle owner接口。

main最新消息上下文（不是本窗口OS独立审计）：共同BASE `task-pve-20261024T053218Z` / PID37096，1454source/454startup/旧110+5 Task新空表。不要从旧023920覆写Inventory/runtime_storage；shared/native3、NPC fresh1/3/paid4 current-only由main统一定界/接线/发布。所属已审E913 `item_messages`继续保留真实socket/score/资源已知来源要求，未知不补0；本窗口未操作运行服。

方法：codebase-design把真实旧/新caps与成长数学放在不同Seam，复用共同read与原唯一state；TDD以HP超过裸cap的真实场景、历史已付与两种资源cause的区分作下一红→绿；writing-for-agents将具体数值案例、旧receipt规则和发布门槛放在一起。本文是下一实现要求，不是这些动作已完成的凭据。

# 任务与成长统一资源接线审计

2026-10-23。只读当前源码，唯一本批产物为本文。已读 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY、ROLE_RESOURCE_STORAGE_INTEGRATION、ROLE_RESOURCE_EQUIPMENT_SEAM_AUDIT，以及 research/codebase-design 两份完整 SKILL；本任务已是后台研究，不递归委派。未修改 Python、共享入口、根窗口独占 Module 或政策，未读在线角色库、运行服务/GUI/战斗。

后续根窗口已交实际GrowthResourceContext/裸身-only成长写，本窗口已实现共同奖励和intro/master-card/独立type59消费者。库存血脉依赖已由所属窗口修复，复合奖励和全前置领域链检查当前通过；精确签名、阶段及未迁消费者见 [TASK_RESOURCE_GROWTH_INTEGRATION.md](TASK_RESOURCE_GROWTH_INTEGRATION.md)。下文保留审计时的旧调用次序和当时缺项，不能再据其“尚未导出”断言最新源码状态。

## 结论与最小决定

迁移后的角色必须在同一调用方角色事务中完成：**扣交物 → 宠物经验（现有次序）→ inventory_change 来源同步 → 裸身成长写与 ordinary_growth 资源过渡 → 奖励物品 → inventory_change 来源同步 → 当前最终 profile 预编码**。普通成长不能跨 inventory_revision；即使装备数值未变，也不能拿旧来源直接普通成长。只改外层最终消息替换无法绕过内层旧读写围栏。

资源 Module 已有 source-only 计划与 CAS，不缺该机制；当前实际缺口是“只写裸身属性”和“把成长及最终资源过渡合并”的公开 Interface，以及任务/成长消费者的显式依赖传入和最终编码调整。根窗口正在补这些 Interface；本文给出需求，不宣称它们已经存在，也不另造策略或第二份 HP/MP。

## 当前真实调用次序与失败位置

| 当前源码 | 实际行为 | migrated profile 的结果 |
| --- | --- | --- |
| [task_workflow.py:40](../task_workflow.py#L40) complete_task_transaction | active 时先固定任务收件宠；apply_task_plan；:48..50 扣 objective_debits；再 `_settle_completion` | 交物资产 revision 在人物 EXP 前变化，不能事后笼统当“奖励完成后再刷新” |
| [task_rewards.py:176](../task_rewards.py#L176) settle_task_reward | settle_pet_experience → character_exp channel(:178..181) → items channel(:184..187) → 货币 → 当前经验 | 非零宠XP实际发放也在人物 EXP 前推进资产 revision，见下文 |
| [progression.py:28](../progression.py#L28) credit_experience | auto_credit_profile；无显式成长才保留旧经验银行路径 | 不能捕获 migrated 围栏异常后退回经验银行，避免丢失已初始化角色的成长/资源政策 |
| [role_growth.py:281](../role_growth.py#L281) auto_credit_profile | 有 profile 则 plan_growth_credit，再 `_write_growth`；无自己的 credit 请求账本，依赖外层 task channel | 任务 EXP 幂等仍归 character_exp channel；不能发明重复结算账本替代它 |
| [role_growth.py:182](../role_growth.py#L182) `_write_growth` | 先写 roles.level、role_progress、成长点数/revision；:191 sync_growth_attributes | `sync_growth_attributes` 在 migrated profile 抛 ResourceProfileRequired；必须外层整体回滚，不能提交先写部分 |
| [role_attribute_storage.py:117](../role_attribute_storage.py#L117) sync_growth_attributes | require_legacy_resource_contract；derive 裸身；以裸身 caps 调旧 growth_vitals 并写 attrs+vitals | 当前不是 naked-only writer。不能删围栏后继续运行，它会把唯一总资源上限重设为裸身 |
| [task_workflow.py:61](../task_workflow.py#L61) `_settle_completion` | attribute_snapshot_if_initialized→read_attribute_snapshot；随后立即 growth_refresh | migrated 即使 EXP/items channel 已付、此次没有成长写，也在这里拒绝。需改为最终资源 profile，不能指望外层覆盖先失败的裸身编码 |
| [role_growth_actions.py:22](../role_growth_actions.py#L22) `_require_profile` | 旧 read_attribute_snapshot；政策核对 | migrated 手动升级/加点在写入前已经失败，必须换当前裸身/资源可用性检查 |
| [role_growth_actions.py:31](../role_growth_actions.py#L31) `_result` | 重读 current growth 与旧混合 attributes；立即 growth_refresh | 必须返回同事务当前最终 profile 的已验证逻辑消息，而非裸身+总资源混合体 |

围栏根源：[role_resource_storage.py:73](../role_resource_storage.py#L73) require_legacy_resource_contract 只要 profile metadata 已转交即拒绝旧合约；[role_attribute_storage.py:64](../role_attribute_storage.py#L64) read_attribute_snapshot、初始化及旧同步都调用它。`attribute_snapshot_if_initialized` 不是 migrated-aware 判别：它只看 snapshot 行是否存在，然后转旧读。

额外真实资产变化：[task_pet_experience.py:120](../task_pet_experience.py#L120) eligible 发奖调用 Inventory.change_pet_growth；[pet_growth_store.py:108](../pet_growth_store.py#L108) 明确 `inventory_versions.revision+1`。因此只有 objective_debits 后同步一次仍不足以涵盖宠XP阶段。应在 EXP channel 真正执行前，以 objective + 宠XP 两者执行后的真实当前资产统一同步；已付宠XP重放不会再次增长资产 revision。

## 目前已存在且可直接复用的公开 Interface

所有调用均在当前角色/epoch 的同一外层事务中；不得自行开连接、提交、读启动配置或发送。

| Interface（当前签名） | 明确契约 |
| --- | --- |
| `inventory.immutable_snapshot_transaction(db, *, epoch=None)` | 当前同事务冻结 InventorySnapshot，包含未提交扣物/宠成长/奖励变化；旧 snapshot 或历史资产收据不能替代它 |
| `read_naked_attributes(db,account_id,role_id,epoch)` | 只读当前裸身 RoleAttributes，核对当前角色等级/growth revision；不读资源、不触 migrated 旧读围栏 |
| `current_equipment_totals(db,account_id,role_id,epoch,inventory_snapshot,rules)` | 同事务核对实际 inventory revision、显式装备基线与政策；从裸身生成 EquipmentTotals；不读 vitals，可以在资源 source 待更新期间使用 |
| `resource_caps_from_projection(totals)` | 从受信 EquipmentTotals 取得 ResourceCaps，包含裸身基线/成长/资产/装备基线完整来源；不要手填或改标签 |
| `read_role_resources(db,account_id,role_id,epoch,rules)` | 返回唯一资源完整 before，source 是上次资源提交来源，允许在本事务资产改动后仍读取这个 before；只读、不治疗、不自动迁移 |
| `plan_resource_source(before,caps,'inventory_change',resource_rules)` | 已存在。caps 数值、裸身基线/成长/属性政策、装备基线/装备政策必须不变；只允许 inventory revision 不倒退，HP/MP/resource version 原样。不是 medicine，也不容许藏成长或装备 caps 变化 |
| `plan_resource_caps(before,caps,'ordinary_growth',resource_rules)` | 当前严格要求 inventory revision、裸身基线/属性政策和装备基线/政策均不变；growth revision 可前进，caps 不下降；存活保留缺失量，死亡仍 0；数值与编码限制由资源 Module 保留 |
| `apply_resource_transition(db,account_id,role_id,epoch,transition,request_id,*,rules=resource_rules,equipment_rules=equipment_rules)` | 完整 before CAS，校验 DB 当前真实 after 来源，重算原因政策，资源载体/source metadata/receipt 同事务。相同 transition 的重放只回当前资源，异意图同键拒绝 |
| `current_resource_profile(db,account_id,role_id,epoch,inventory_snapshot,*,equipment_rules,resource_rules)` | 已存在。将当前 totals 与唯一资源组合，caps **及完整 source 必须精确一致**；有待处理的资产/成长变化即拒绝。这是最终读取/预编码 Interface，不是同步资源的 writer |
| `growth_refresh(current_growth,final_profile)` | 接受 EquipmentRoleSnapshot，核对同一次 growth revision、资源与最终上限，并校验原生整数/float32精确表达；在提交前调用，提交后才发 |

出处：[role_equipment_storage.py:109](../role_equipment_storage.py#L109)、[role_equipment.py:86](../role_equipment.py#L86)、[role_resource_plan.py:132](../role_resource_plan.py#L132)、[role_resource_plan.py:190](../role_resource_plan.py#L190)、[role_resource_storage.py:151](../role_resource_storage.py#L151)。source-only 即使推进 source 而不推进资源 version，也必须落 metadata；“HP/MP 未变”不是跳过的理由。最终 totals 当前仍只支持师承十武器 v1，未接六槽不得伪称全部装备支持。

## 建议接入的最小 Interface 与实际缺项

**依赖注入**：任务已有当前 Inventory；新增显式 keyword `resource_rules`、`equipment_rules`。手动升级/加点 Adapter 还须显式获得当前角色 Inventory。全部规则是启动加载的冻结对象；不能在请求路径读配置，不能从 Session 提取可变缓存或让装备 Module 另开数据库。保留现 growth_rules、attribute_rules 和任务各渠道规则；新参数不用改变客户端 wire。

**缺项 A：裸身-only writer**。根窗口须提供公开、同事务、带 owner/epoch 与 growth scope 核验的写裸身 Interface：从原 baseline + 当前 GrowthState derive 并只写 attributes，不读写 vitals，不绕过 migrated 合约覆盖资源。当前 `sync_growth_attributes` 不是这个 Interface；也不能靠任务调用私有 SQL 自己拼实现。

**缺项 B：成长资源事务入口**。根窗口须提供公开 Interface 将一次真实成长计划与资源过渡封装：接当前 Inventory、冻结成长/属性/装备/资源规则；在来源已同步时取得 before，沿既有成长凭据 apply 原计划，以 A 更新裸身，当前 immutable inventory→totals→caps，再用 ordinary_growth+CAS落唯一资源，返回当前状态/最终可组合来源。手动/加点已付重放只确认原领域凭据并重读当前，不重复资源变化。自动任务 credit 继续由外层 character_exp channel 限制只执行一次。具体函数名/签名以根窗口新代码为准，本文没有声称一个未知 helper 已存在。

**最小任务侧内部 Seam**：不需把任务奖励拆成让调用方手工管理的多个公开付款接口；在现 EXP callback 执行前、奖励 items channel 执行后各放一次同事务来源同步，并让 credit_experience 进入 B。这样保留既有深 Module 的渠道收据和异常回滚，把 source/caps 复杂度集中在资源 Interface。`complete_task_transaction` 的 objective 扣物照旧；不将早期扣物移到领奖之后，也不提前发奖励物品。

## 同事务分阶段次序

1. **入口验证**：对 migrated 角色，在任何任务/资产 mutation 前用当前 InventorySnapshot→current_resource_profile 验证本事务初始来源精确当前。未知资源 profile/未知装备基线/政策不符不隐式补建或降级。原未迁移路径按明确旧合约处理，不能 catch-all fallback。纯读取不迁移、不治疗。
2. **任务目标阶段**：完成前固定任务宠接收者与角色旧等级；apply_task_plan；原 objective_items settlement 扣物。现任务宠XP阶段保持在人物 EXP 前执行。此时尚未调用最终 current_resource_profile（来源可能暂时落后）。
3. **EXP 前来源阶段**：读取唯一资源 before；重新取实际 immutable inventory、current_equipment_totals、resource_caps_from_projection。来源不同则 plan_resource_source(...,'inventory_change',...) + apply_resource_transition；数值 caps/成长变化则明确失败，不能用它洗掉额外变化。此阶段覆盖目标扣物、宠XP等实际已发生资产 revision。若 EXP channel 已付不执行 callback，仍须在本次实际资产变化完成后做来源同步，不能把同步永久只藏在会被跳过的 credit callback。
4. **人物成长阶段**：仅对未付 character_exp 调 credit_experience→B。B 前后 inventory revision 相同；真实成长/潜能只推进它们自己的来源。零 EXP 或正 EXP 不升级仍可能改变 growth revision，应以实际当前状态处理；不能用“level 未变”代替来源核对。
5. **奖励物品及其余渠道阶段**：现 items channel 后，再以本事务最新 InventorySnapshot→totals/caps 同步 inventory_change。待结算 item 未实际发放无需捏造 revision；实际资产变动导致的来源差异必须完成。货币等剩余渠道若其实现又改变资产 revision，最后从实际当前 snapshot 再核对；不靠假设缓存 inventory revision。
6. **最终读取与预编码**：继承现任务后继激活逻辑；重读当前 GrowthState 和最后一次 current_resource_profile，生成唯一 final growth_refresh，装入 TaskCompletion。TaskCompletion.attributes 应为这一最终 EquipmentRoleSnapshot；不得先以裸身提前编码再等外层替换。GrowthActionResult 同理。所有失败整体回滚渠道、扣物、XP、成长、资源、货币、宠物及任务收据；成功后连接 Owner 才投递冻结消息。

source-only 同键不能每次按后来 before 重造 transition 后调用 apply：该函数指纹包含完整 transition，历史同键不同 before 会冲突。已付领域请求走重读当前确认，新的确有来源差异才受理新阶段命令；任务 phase 的稳定身份与原已受理 transition 应由现渠道/操作凭据约束。若专门封装 source 同步 helper，可在当前 caps/source 已精确相等时仅读返回，不创造空资源操作/收据；不得复用旧操作来治疗或倒回 source。

手动升级/加点无目标扣物或奖励物品，次序可缩为“验证 current_resource_profile → 领域请求凭据 → B → 同事务当前最终编码”。`request_manual_level` 重放返回历史 GrowthState，外层应继续 read_growth；`request_potential_allocation` 重放已返回 current，但最终 profile 仍需当前读，不能拿 receipt 旧资源覆盖。角色级 mailbox/租约与调用方事务继续负责串行，不增加世界锁或全服执行器。

## 必要验证建议与本批限制

主策划随后给出的具体接合形状是根窗口将提供冻结 `GrowthResourceContext(inventory_snapshot,equipment_rules,resource_rules)`，并由role_growth各事务函数新增可选keyword `resource_context`，同时由根窗口迁移role_growth_actions。读取本批源码时该context/裸身-only writer仍未导出，因此以下是明确接线提案，等待根窗口实际签名后实施，不是已完成消费者：

- 本窗口保留 `progression.credit_experience(..., *, resource_context=None)`并透传给auto_credit_profile；不自行实现或修改role_growth/根属性/资源算法。
- `task_rewards.settle_task_reward`与 `task_workflow.complete_task_transaction`及其当前结果/重试入口新增显式keyword `resource_rules=None,equipment_rules=None`，继续使用既有实际Inventory参数，不从可变Session或历史背包收据取上下文。
- 在objective扣物和petXP实际处理后，用当前公开source-only计划/存储收敛来源，再从**此时实际库存快照**构建GrowthResourceContext供未付EXP；不能将任务入口旧快照一路传到升级。EXP已付而本次补发宠XP时，也执行实际source收敛。
- items/pets奖励实际执行后再次收敛来源；TaskWorkflow从当前snapshot的current_resource_profile预编码一份最终属性消息，替代先执行旧attribute_snapshot_if_initialized/growth_refresh再等待shared覆盖的路径。

本轮依主策划“保持仅规划”未修改上述三个所属消费者、root独占role_growth/role_growth_actions/属性/装备/资源Module或共享入口，未自动迁移任何profile。下一批需重新读取根窗口已交付代码，按真实Interface实现；本提案的完成条件是明确依赖与阶段，不以待实现helper当作已接线。

根窗口接线后只需一组有区分力的临时库纵切：migrated 角色目标扣物+非零宠XP+人物XP+奖励物品全过程，各阶段实际 inventory revision 对齐；升级或加点改变裸身上限时只执行 ordinary_growth；已付任务重放不再扣/发/治疗、后来资源损伤不被旧回执覆盖；晚期物品/来源/原生编码失败使整笔回滚；旧epoch拒绝；未知 profile 与不支持装备不自动补建。还需保留旧未迁移路径必要兼容检查。本文没有运行这些用例，不引用其他文档的通过结果当本批新接线已验收。

research 实际方法：从当前 task channel 顺序追入 credit、growth writer、属性围栏，再从公开投影/资源 Interface 反查来源限定与同事务资产变化。codebase-design 实际决定：资源 Module 隐藏来源/CAS/原因规则，成长 Module 隐藏裸身写和成长凭据，任务 Module 保留付款渠道；通过显式依赖小 Interface 接合，不复制私有表结构与算法。

读取快照 SHA256 前16位：task_workflow `20b956cf1c199d88`，task_rewards `cd518f9f7685df82`，progression `04cc297d79a944b9`，role_growth `06013dc828f35141`，role_growth_actions `02d602ce597967ad`，role_attribute_storage `12cd5849b1ac6df9`，role_equipment_storage `eca2c26ee614be2a`，role_resource_storage `08bc22b9f2030ff0`，role_resource_plan `cbf28928450ca278`。多窗口后续修改需重读真实签名；本批静态审计不代表已部署、客户端显示或商业并发验收。

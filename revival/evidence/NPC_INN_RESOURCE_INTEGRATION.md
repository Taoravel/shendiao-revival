# 客栈唯一人物资源消费者

2026-10-23，NPC窗口。按主策划请求，仅修改npc_recovery.py及NPC验证/交接；未改人物数值/资源/装备Module、共用政策或game_runtime/runtime_storage/accounts/serve/gateway。没有GUI、部署、真实角色或实际战斗操作。角色资源基础见ROLE_RESOURCE_STORAGE_INTEGRATION与ROLE_RESOURCE_TRANSITION_DECISION。

## 精确注入与接线

公开调用保持原三参数，并新增两个必须成对注入的keyword-only依赖：

```python
npc_recovery.settle(accounts, inventory, recovery_intent,
    resource_rules=startup_resource_rules,
    equipment_rules=startup_equipment_rules)
```

规则由启动阶段的load_resource_rules和load_equipment_attribute_rules加载一次，调用方传冻结对象。当前已有accounts.equipment_attribute_rules，resource_rules使用主集成最终确定的启动字段；NPC Module不自行加载配置，也不初始化/迁移profile。只传一个依赖明确拒绝。都不传保持旧调用；若该角色已经转交新资源合同，旧read_attribute_snapshot围栏会拒绝，不能借旧路径写回裸身资源。

主集成需同时覆盖原CRecovery0xc2333分发和CNpcService service3分发，避免前者新规则而后者还走旧合同。RoleOwner.io不接kwargs时，可由集成的可信存储wrapper调用上述kwargs；NPC窗口未修改shared。宠物kind2/3/4仍使用自身资源/照顾事务，注入新人物依赖不会将宠物恢复另存到人物资源表。

## 一次外层事务内的行为

settle仍是角色所有者经有界I/O调用的NPC持久化Adapter，自己开启一个当前租约的外层事务。被调用的货币、活力和root资源Interface全部加入同一个db，不另开连接/提交。

新profile分支先read_role_resources取得唯一当前资源，再current_equipment_totals取得当前实际装备/裸身总属性，resource_caps_from_projection提供真实final_caps。HP0拒绝普通客栈复活；已经全满拒绝无效果收费。随后plan_resource_values(before,final_hp_max,final_mp_max,'inn_rest',resource_rules,current_caps=actual_caps)做原因限制，任何装备/成长上限漂移不能藏进治疗；当前已有携带物品revision前进且caps不变时，可随本次真实治疗一起转交source。

按现有原生客栈政策结算活力和费用，再apply_resource_transition写唯一carrier/source/资源收据，NPC自己的恢复/公共凭据和费用/活力同事务。没有新NPC人物资源表，也没有第二份当前HP/MP。资源收据孤立存在而NPC领域收据缺失时拒绝，不把它当尚未支付的新治疗。

完成后及历史请求重放，使用严格只读的current_resource_profile重组最终属性+唯一资源；已提交重放不重新做plan、不扣费、不治疗、不修改来源。严格组合时source未匹配就拒绝，不能在读取或已付重试中静默修补来源。领域明细中before/after仅为历史审计，不是另一份当前权威。

未迁移旧角色：即使调用方成对注入新规则，read_role_resources的ResourceNotInitialized才允许回旧路径，随后使用原read_attribute_snapshot/update_role_vitals。先查资源profile再要求装备基线，保留缺装备basis但已知旧人物属性的兼容角色。其它policy/source/租约错误均不回退。该分支不会插入role_resource_profiles。

## 当前刷新Interface与提交顺序

返回值仍为逻辑消息list，经原目标连接发送泵投递，Module不碰Session/RC4/MPPC：

- 新profile：同db重新取得当前inventory snapshot，current_resource_profile严格组合，read_growth取得同次成长，再growth_refresh生成完整人物20项0xc32c8（60/70当前值、140/150实际总上限、适用640及当前战斗/五维等）。随后原活力440/620刷新与当前绝对cash。每项在外层commit前编码，错误整体回滚。
- 旧profile：保留原role_resource_refresh的60/70两项，随后活力和现金消息。未知钱包不伪造0；既有收费规则不变。

完整map而非仅两项新HP/MP使晚期原生精度错误也能撤销费用、活力、资源与NPC收据。并不代表六槽cap数值已由NPC重新计算；所有上限及来源仍来自root最终投影，NPC不新增装备公式。

## 验证与实际范围

verify_npc_inn_resources.py通过临时AccountStore、真实角色租约、原NPC10157的NpcScene证明和公开settle Interface；没有替代root资源/装备计算。fixture显式迁移已知HP10/MP20、caps500/1000、真实绑定49009穿戴、现金2000和活力100。

| 检查 | 结果 |
|---|---|
| 已迁移收费治疗 | HP500/MP1000，现金2000→1500，活力100→85，资源version只进1；资源/钱包/NPC恢复/公共收据各一次 |
| 当前刷新 | 唯一完整20项map，HP/MP/caps500/1000和实际封印19；不返回历史before或裸身拼凑profile |
| 历史重放 | 后来50/60资源保留，余额/活力/版本/收据不变；新一次治疗才再次收费 |
| 携带来源前进 | 真实加入32000物品，inventory revision前进；新的付费治疗在同caps计划中更新实际source，最终严格profile成立；单纯读取不更新 |
| 失败/输入 | 全满、无/半套注入、错误policy、余额不足均无资源/活力/收据副作用；可信测试补充余额后同一未成功请求可成功 |
| 真实晚期编码失败 | 独立已知旧档命中16777217，其HP/MP caps与装备三项仍可投影/迁移；完整growth_refresh因float32不精确拒绝。费用、活力、唯一资源和四类收据完全回滚，无mock编码器 |
| 新租约 | 实际acquire_lease后旧Owner拒绝；新Owner同历史ID读当前70/30且不治疗，新ID才收费治疗；后来HP0，新请求拒绝复活、历史请求显示0 |
| 旧profile兼容 | 无装备basis的已知旧人物通过成对注入仍走两项刷新，role_resource_profiles保持未知，没有自动激活 |
| 热路径 | 在builtins.open/io.open禁止读取时新分支仍完成治疗；所有规则已在启动读入 |

结果npc-inn-resources.json。必要旧路径回归verify_npc_inn_runtime与verify_npc_pet_recovery_runtime原样通过，含旧角色重连伤势/活力、宠物寿命不补与现金原子性。

本批tdd红例为settle不接受resource_rules；正常纵切转绿后，真实携带revision变化暴露过早调用严格profile的红例，再将治疗前使用totals/唯一before、提交前才严格combine，原检查转绿。codebase-design把新/旧合同选择、真实治疗和刷新留在一个NPC Module，将资源权威/上限算法留root Module，沿角色事务Seam组合。writing-for-agents按启动注入、两条shared调用点、收据/当前刷新与可判定完成范围交接。

尚未验证：新资源profile的完整GameRuntime登录/首次入场/重连（本批是实际新租约+NPC Adapter，不冒称新shared加载已接）；六槽装备改变HP/MP上限的真实角色路径（当前白名单师承武器不改caps）；共享激活策略、GUI、部署和商业数据库。profile自动激活仍由主集成最后集中接入，固定现场未变。

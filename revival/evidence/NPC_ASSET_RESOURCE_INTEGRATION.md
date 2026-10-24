# NPC资产、修理和宠物恢复的唯一资源接入

2026-10-23，NPC窗口。本批所属源码完成；shared集成方可按本页接线。只改NPC Module、所属验证和证据，人物资源/装备算法及公共政策仍由主策划维护，game_runtime/runtime_storage/accounts/serve/gateway仍由原始集成窗口维护。本批没有部署、GUI、实际角色库或战斗操作。固定现场进程不受工作区修改影响。

## 集成步骤与完成条件

1. 购买、出售/回购、仓库MOVE_ITEM使用[NPC_RESOURCE_SIGNATURES.md](NPC_RESOURCE_SIGNATURES.md)中的四参数调用。可信precommit捕获实际受理request_id，接受keyword-only `replayed: bool`；调用root `synchronize_inventory_resource_source`后，同db严格取得当前profile并编码完整刷新。完成条件：真实资产、费用、来源、领域及公共凭据在同一NPC外层事务提交；不是返回后补写source。已有领域receipt才传True，不能统一当fresh。
2. `npc_repairs.repair(accounts,inventory,intent,precommit,resource_rules=rr,equipment_rules=er)`显式注入成对启动规则。保留原三参数final precommit，纯组合当前完整属性并编码。完成条件：去掉shared已迁移角色的临时repair拒绝门控后，调用该新Interface；不要再给repair追加source-only inventory_change同步。
3. `npc_recovery.settle(...,resource_rules=rr,equipment_rules=er)`已完成kind2/3/4。完成条件：shared两条恢复分发均注入这对规则，去掉宠物kind的临时新profile拒绝门控。kind1仍是已交付的独立inn_rest计划；宠物分支自身使用source-only helper，不由shared重复补写。
4. 继续在临时库、原生逻辑消息/加密Peer执行shared验收，之后由集成方统一决定部署与profile激活。完成条件：新profile的真实Owner分发、当前完整刷新、提交失败、重放和重连均分别有证据。本文的Adapter检查不替代此步骤。

## 行为与所有权

`npc_transactions.precommit_messages`集中验证实际三类资产Adapter共同使用的可信事务回调与不可变编码结果；它不持有db/Inventory/Session。hook在实际fresh或已付重放分支之后、本地消息编码与commit之前调用，错误回滚整个事务。仓库open/query/cash不改变inventory revision，不调用此资产hook。

修理在新profile分支先读取唯一before并严格核对当前source，防止借修理接收无关待同步变化。fresh真实修理后，用当前快照的actual after_caps生成`equipment_repair`计划，再同db CAS。已付重放仅严格读当前profile；包括旧合同下已付修理、之后明确迁移profile的情况，不追补资源receipt、不重抽随机、不扣款、不再次修复。规则只传一套、缺final编码hook、旧租约或未知来源均拒绝。未迁移角色保持原兼容路径，NPC不会初始化profile。

宠物kind2/3/4实际治疗/忠诚变化会推进整个inventory revision，故在宠物、费用和NPC凭据同一事务中调用root source-only helper，传真实old标记。人物HP/MP及数字资源version保持当前值，宠物HP不会写入人物carrier；完整人物刷新也在commit前真实编码。已付重放不能再次恢复后来受伤的宠物，也不能修补无关pending source。

## 已运行验证

| 公开Interface检查 | 已通过范围 |
|---|---|
| `verify_npc_asset_sources.py` / npc-asset-sources.json | 原NPC真实证明→购买32000×2/单价150；实际出售/回购及原实例恢复；仓库存入/取出；root来源CAS及完整刷新；HP70/MP40/version0保持 |
| 同一资产检查的失败分支 | 购买、出售、回购、仓库存/取各自在真实source CAS与原生编码后受控失败，物品/现金/库内缓存/全部相关收据回滚；同一ID随后成功，重放不重复 |
| 同一资产检查的权限/读取 | 可变hook结果拒绝并回滚；仓库query不调用资产hook；实际新租约使旧购买Owner失效，新证明的历史购买/宠物请求只读现状 |
| 同一资产检查的宠物 | kinds2/3/4真实成长/照顾事务及source同步；忠诚恢复、寿命5950/5900保留；不改变人物HP70/MP40/version0；历史重放无写 |
| 同一资产检查的真实晚期错误 | 已知level21人物命中16777217可完成合法资源迁移；实际完整growth_refresh因float32精度拒绝，宠物HP/忠诚、非零费用、source及全部相关凭据回滚；未mock编码器 |
| 同一资产检查的pending source | 故意在隔离库产生无关待同步资产变化后，历史购买/出售/仓库/宠物请求均拒绝且不修补来源 |
| `verify_npc_repair_resources.py` / npc-repair-resources.json | 普通修理费40、同事务equipment_repair、HP70/MP40/version0保持；后来HP50/MP30保留；重放不抽随机；晚期回滚后同ID可成功；实际新租约/旧Owner拒绝 |
| 同一修理检查的历史迁移 | 旧合同已付修理后明确迁移profile，再重放不生成equipment_repair资源过渡或资源receipt，余额960及后来HP55/MP35保持 |
| 同一修理检查的真实晚期错误 | 实际命中16777217导致原生编码失败，耐久、扣款、唯一资源/source与所有修理凭据回滚；缺final hook/半套规则拒绝 |
| 必要旧路径回归 | verify_npc_shop_runtime、verify_npc_sale_runtime、verify_npc_depot_runtime、verify_npc_repair_transactions、verify_npc_pet_recovery_runtime、verify_npc_inn_resources均通过，含原生加密Peer、完整实例、费用/背包满回滚及既有客栈新合同 |

## 方法与未验证范围

codebase-design：在NPC自有角色事务放置真实precommit Seam，三个资产Adapter复用小Interface，资源来源和上限算法留root；修理保持其专用原因，宠物只推进来源。tdd：本批沿实际NPC公开购买/settle/depot/repair Interface纵切验证，独立算例来自原单价150、出售75、修理费40；通过实际晚期codec错误检验原子性，未把内部mock结果当成功。writing-for-agents：先固定精确Interface，再列shared门控解除条件、实际产物和运行范围；当前入口从NPC_RECOVERY_HANDOFF触发本页。

上述新profile检查是独立真实SQLite/租约/NpcScene/领域Adapter与原生编码，并非新profile完整shared分发或GUI证明。六槽增血cap的正式白名单、自动激活、真实部署、商业数据库及容量均未由本批验证。普通新旧HP不因购买/宠物恢复而增加；普通修理上限保持/裁剪仍统一遵循root政策。

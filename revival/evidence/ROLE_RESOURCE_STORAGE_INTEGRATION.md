# 唯一人物资源存储Interface

2026-10-23，根数值窗口。适用于role-resources-v1，先读ROLE_RESOURCE_TRANSITION_DECISION、ROLE_RESOURCE_EQUIPMENT_SEAM_AUDIT和ARCHITECTURE。已交单记录存储、最终profile组合及显式成长入口。当前共享已接分支与剩余消费者统一查RESOURCE_SHARED_RUNTIME_INTEGRATION，不在本页缓存接线状态。新创建授权另见ROLE_RESOURCE_CREATION_AUTHORIZATION；**自动激活与旧角色隐式迁移仍关闭**。

## 启动、来源与一次转交

`prepare_attribute_storage(db)`现同时调用`prepare_resource_storage(db)`，只建空metadata和receipt schema，不初始化角色。`role_resource_profiles`只存policy、投影来源、origin和迁移身份/指纹；当前HP/MP/上限/version仍只在原`role_attribute_snapshots.vitals`。`role_resource_receipts`仅存请求指纹、原因及前后version，没有第二本当前资源。

启动加载冻结`load_resource_rules()`，后续由调用方注入。可信显式迁移先在当前角色租约事务取得真实已知旧VitalState、当前裸身/资产/装备基线并计算最终装备投影，使用`resource_caps_from_projection`提取ResourceCaps。服务器最终投影提供数值，客户端不能提供caps。`current_resource_projection_source`用实际角色/基线/成长/资产/装备基线版本校验来源；它本身不计算未知装备效果。

```python
migrate_role_resources(db, account_id, role_id, epoch, expected_vitals, final_caps,
    origin='explicit_migration', migration_id=trusted_stable_id,
    rules=resource_rules, equipment_rules=equipment_rules)
```

事务必须已开始。低层新建origin校验持久`role_restoration_origins`；这不单独授权自动激活，正式新创建调用还须ROLE_RESOURCE_CREATION_AUTHORIZATION的独立许可。不得从字段缺失推定。完整旧资源对比后按迁移政策保留当前量/必要时裁剪，资源载体及metadata同事务；相同迁移身份/意图重试返回**当前**资源，不重置或重新治疗，冲突拒绝。缺旧资源、缺装备基线、旧source或未知policy均拒绝。

## 当前读与资源写

`read_role_resources(db,account_id,role_id,epoch,rules)`只读已转交profile的唯一资源，返回冻结RoleResources，未知抛ResourceNotInitialized。其source记录上一次已提交资源投影；业务改变资产/成长时先保留这个完整before，再计算同事务真实after_caps。读取/登录不执行caps调整或治疗。

裸身属性独立读`read_naked_attributes`。一旦profile已转交，旧`read_attribute_snapshot`混合快照、旧vitals写和旧成长caps同步会抛ResourceProfileRequired。这样半接线会明确失败，不让两种contract同时写同一角色。共享已迁移profile使用下述最终profile Interface；源码验证、默认激活与部署分别见共享交单。

```python
transition = plan_resource_values(before_resources, trusted_hp, trusted_mp,
    'medicine', resource_rules, current_caps=after_caps)
# 或 plan_resource_caps(before_resources, after_caps, 'equip', resource_rules)
result = apply_resource_transition(db, account_id, role_id, epoch,
    transition, resource_request_id, rules=resource_rules,
    equipment_rules=equipment_rules)
```

`current_caps`只用于同上限的资源操作，允许消耗/获得携带物品导致的资产revision更新；不能把新装备或成长上限变化藏进药品操作。穿脱、耐久和修理先用各自caps原因计划；普通成长使用独立原因。输入必须来自当前服务端实际投影，不得把旧裸身上限换个source标签后当final_caps。

存储重新校验当前租约、完整before、当前after source和原因政策，执行载体及source的条件更新并登记收据；外层还应合并物品/费用/任务与原生预编码，最后统一提交。任何异常整体回滚。**显式迁移不能作为普通mutation重复调用。**

同一已受理transition及request_id重试只读当前结果；不同transition复用该ID拒绝。调用方保留原受理命令，或先按自身领域凭据确认已经支付/消耗，然后仅读当前资源刷新；不要在已付重试中重新按当前HP生成一份不同transition，再假装它是原操作。新的相同客户端线包由角色所有者另分配内部身份，仍需真实物品/余额限制。

## 后续接线顺序与完成条件

1. 属性-only最终计算与新profile已交，见下节。当前10武器v1路径不因新metadata存在而自动改语义；显式普通六槽v2及1240前提另见ORDINARY_EQUIPMENT_V2_INTEGRATION。
2. 显式成长事务与GrowthAction最终编码已交；TaskWorkflow/任务奖励仍须接入并处理EXP前后资产来源变化。不要绕过迁移围栏去覆盖裸身caps。
3. 药品/客栈改读新唯一资源，用自身物品/费用/重复凭据约束真实效果；共享加载/任务/穿脱/耐久/修理统一用同次最终profile编码，提交后发送。
4. 显式新建/可信旧档迁移开关最后接入，验证新profile从创建、药品、成长、穿脱、修理到重连全流程。只在这些路径同事务和原生编码通过后扩大六槽。

本批tdd实际纵切：缺Interface红→真实师承装备来源迁移/重读；旧混合read仍接受红→旧writer围栏；缺CAS写红→完整before/历史当前值重试；携带资产revision变化不支持红→同caps资源写source更新。`verify_role_resource_storage.py`通过已知70/40迁移不回血、旧读写拒绝、85不被旧操作重置、真实背包/现金/资源/收据晚期失败全回滚及后来同键成功90；还执行未知profile、冲突迁移、伪装脱装回血、stale source、实际换租约后旧回调拒绝。

必要兼容回归已过：自然嘉兴120XP/装备成长、原人物药品、已装备NPC修理。它们仍属未迁移旧profile路径，不冒称新消费者已接。codebase-design用于把资源权威和裸身属性分开，保留角色调用方事务Seam；research沿用原字段/转换证据和端游未知处理；规范/需求双轴审查以固定发布源码与本批冻结快照比对，项目非Git的流程差异记在reviews/role-resources-20261023。未部署、无真实角色/GUI/战斗操作，商业数据库和容量仍未证明。

## 最终profile与资产来源同步

`project_equipment_totals(naked_attributes, inventory_snapshot, basis, equipment_rules)`返回冻结`EquipmentTotals`，没有vitals；不再为计算装备属性虚构满血、0HP或裸身上限资源。`current_equipment_totals(db,account_id,role_id,epoch,inventory_snapshot,equipment_rules)`从当前持久裸身数据和实际资产来源调用该纯计算。默认规则为10件师承武器；显式普通六槽v2已交纯计算/隔离事务，尚未成为共享默认，范围与资格见ORDINARY_EQUIPMENT_V2_INTEGRATION。

`resource_caps_from_projection(totals)`已移至纯`role_equipment`，旧`role_equipment_storage`导入路径继续有效。`combine_equipment_resources(totals,resources)`只在完整source与数值caps完全一致时组合真实资源，返回现原生编码使用的`EquipmentRoleSnapshot`。现有编码的“资源上限=最终属性上限”检查保留。

`current_resource_profile(db,account_id,role_id,epoch,inventory_snapshot,*,equipment_rules,resource_rules)`严格当前读，既不补来源也不治疗。登录先精确检查`read_role_resources`的`ResourceNotInitialized`分支，不能先调用会拒绝已迁移角色的旧混合reader再补新profile；其他异常不可伪装成未迁移。

领物品、整理、任务扣物、购买等也会推进整个inventory revision。它们若数值资源caps与裸身成长不变，在同事务先计算实际最终caps，再用`plan_resource_source(before,after_caps,'inventory_change',resource_rules)`和同一个`apply_resource_transition`结算来源。该原因只推进资产来源，HP/MP/version保持；成长、装备基线或数值caps变化拒绝。不要将这些业务写成medicine/inn，也不在重连时补transition。ResourceRules新增`source_causes`，由启动`load_resource_rules()`取得。

自开外层事务的通用Inventory/NPC操作，统一使用`role_equipment_storage.synchronize_inventory_resource_source(db,account_id,role_id,epoch,inventory_snapshot,request_id,*,resource_rules,equipment_rules,replayed)`，放在真实变更后、原生回复编码及提交前。领域先校验自己的持久请求payload，并明确提供replayed布尔值；False才允许来源同步，True只严格当前组合读取，pending source也拒绝；不能按后来状态重建已付transition。新profile返回当前RoleResources，精确未迁移返回None且不要求未知旧装备基线；策略/租约/类型错误均抛出。内部来源凭据有独立哈希namespace，完全无来源变化不写receipt。调用方负责共同事务/最终编码及异常回滚；这不是读取时修复或跨事务补写Interface。

## 显式成长资源事务

`GrowthResourceContext(inventory_snapshot,equipment_rules,resource_rules)`是一次角色事务的冻结上下文。`apply_growth_plan`、`auto_credit_profile`、`request_manual_level`、`request_potential_allocation`新增keyword `resource_context=None`；默认仍为旧契约，已迁移角色漏传context会拒绝并要求调用方回滚。显式context分支先验证当前final profile，写成长和裸身属性，再以**同一资产版本**计划ordinary_growth并写唯一资源。`sync_growth_naked_attributes`是该流程内部公开接缝，只写裸身属性；调用方须在同事务完成资源及编码，不能将其单独提交。

`role_growth_actions.manual_level_transaction`、`allocation_transaction`同样接收keyword `resource_context`；显式分支前后直接取最终profile，内层原生编码不再读取裸身混合快照。未迁移旧入口保留。任务窗口负责将context经`progression.credit_experience`传入并处理objective扣物、EXP、奖励物品的阶段；共享集成最后统一load、穿脱/任务/修理和新建授权。

成长资源凭据键使用实际前后growth revision；完全零变化的0XP不写资源凭据，避免同revision在后来资产来源变化后冲突。历史成长/加点凭据只阻止重复执行，最终动作刷新重读当前profile。EXP外层仍需自己的唯一结算凭据，`auto_credit_profile`不是独立可重复支付命令。

`verify_role_resource_growth.py`实际红→绿：缺Context→完整成长入口；auto_credit不支持context→捕捉0XP/后续资产来源的真实receipt冲突→完全no-op不写资源；加点动作不接context→最终profile编码。临时库实际49009穿戴、已知70/40经120XP到L2/31/free5、80/110HP46/106MP、49/38/8；体质加点保缺失量、晚期调用方失败回滚属性/点数/资源/凭据，同键后来成功100/130/version3，旧加点回当前。控制XP夹具到10后实际手动升级11，190/220HP100/160MP/free48；这不是自然主线到10的声明。缺context、旧资产、冲突键及旧lease拒绝。实际原x86普通map及角色详情同源已验证，GUI/共享消费者/自动激活仍未验证。

## 普通物理终局资源

`ResourceRules.combat_causes`由启动policy显式冻结；旧四参数规则默认空集合不授权战斗。可信普通消耗终局使用`plan_combat_resources`及同一`apply_resource_transition`，详细入场/版本前提、fixed caps/source、paid当前值与实际资源Seam验证见ROLE_RESOURCE_COMBAT_INTEGRATION。本接缝没有自动迁移或运行战斗。

# Spec 独立审查

缺失0、额外行为0、错误0；未读取Standards。

`NPC_REPAIR_RESOURCE_ACTIVATION.md:15`明确“去掉…临时…门控”“传入启动的…两规则；原三参数final precommit保持”，并要求“不应另补source-only同步，也不引入资源迁移”。候选 `runtime_storage.py:693–699`逐项落实，仅改此函数，真实Owner原method2入口得以进入既有深Module；未扩大855、Inventory/PetStone或特殊修理范围。

`NPC_ASSET_RESOURCE_INTEGRATION.md:8/16`要求fresh专用equipment_repair与paid当前只读。准确candidate/source的 `npc_repairs.py:70–117`在同一当前租约连接事务内先查共同receipt并严格读取before/source；fresh才实际draw、修理/费用、按actual after_caps计划equipment_repair、完整before CAS及共同receipt。`inventory.py:937–943`仍只准owned普通装备；底层费用/condition/Inventory凭据共用该db。无数值/caps变化时 `role_resource_plan.py:132–135`保留数字resource version，10/20伤势不会被治疗；上限变化仍依原保持/裁剪政策。

paid分支跳过L89–103的draw、扣费、repair及资源transition，包括legacy已付之后显式迁移；L104–116严格读当前profile/耐久/钱包并执行原final precommit。shared L832–841同db读取当前profile、实际native编码；任何末端异常退出原事务会回滚费用、condition、来源及所有关联receipt。ResourceNotInitialized仅保留原兼容路径，不初始化profile、不追补历史transition。

方法：沿用完整code-review/codebase-design及项目单Owner/调用方事务约束，以实际公开修理Interface追到CAS与最后编码；只读candidate及其release/source依赖。非Git：候选/BASE runtime_storage两SHA、npc_repairs不变SHA、diff、manifest/candidate记录及seal均核对；两manifest仅runtime_storage不同，其余1441登记SHA相同。scope前后 `31d2805294b1fe47e5bd07747c1698d2bbf9b572d286433c7a137d2ae77efb87`稳定；最终源码 `9cdcc5cd708f9cc03441e85c393830151ebd7a0814ccedf6f7ed25237b546b43`再核一致；seal `8f112fa854689f2735679e258316bcc16d74734eedcd3bbc05a426a8fdaa2ea4`。

仅静态，未执行Owner/care/legacy测试、DB、服务、GUI或战斗。准确红转绿及必要回归由集成方另闭合；不以此报告宣称已部署或现场完成。

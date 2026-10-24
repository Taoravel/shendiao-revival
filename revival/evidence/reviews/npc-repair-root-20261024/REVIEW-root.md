# ordinary NPC repair 主策划固定复核

## Standards

Standards：硬违规0；heuristic可行动发现0。

方法：实际沿用code-review逐hunk核对唯一生产差异，并逐项判断完整12种Fowler启发；用codebase-design沿公开RoleOwner→storage→NPC外层事务Interface追踪所有权与final编码Seam。依据AGENTS、ARCHITECTURE“角色单写者、有界异步持久化、资产与凭据同事务、启动冻结配置”、DESIGN_AUTHORITY及ROLE_RESOURCE_STORAGE_INTEGRATION。未读本批Spec结论。

证据：runtime_storage.py:693–699保留原三参数final precommit，只向npc_repairs.repair成对注入accounts启动规则，未另开事务、热读配置或新增全局锁。game_runtime.py:655–673保持当前地图证明及角色所有者有界self.io调用；规则在runtime_storage.py:144–145、182–183启动准备。

候选依赖npc_repairs.py:70–117在同一BEGIN IMMEDIATE中校验租约/旧receipt，读取完整before，fresh修理/费用后以equipment_repair结算唯一资源及来源，再写领域receipt、编码当前bag/钱包/final profile；final hook异常由外层统一回滚。old分支不抽随机、不扣款、不重放历史资源过渡，只严格读取当前source/caps，未迁移精确ResourceNotInitialized保留兼容。未增加第二份HP账、自动迁移或第二资产写者。没有为临时guard解除引入空转发或虚构抽象。

审前后BASE/candidate/diff与scope相符；candidate与实际release/source相同。BASE=d23d811cfaa24fb5250fba1683c4ff3b14c199620d9d0ca7ba8f9a3fb7ce7187；candidate=9cdcc5cd708f9cc03441e85c393830151ebd7a0814ccedf6f7ed25237b546b43；diff=b2f1832184fb74e82c3a9364d35ffc60defd26b5f2000b699ed6912f2035d1bd。manifest/candidate记录匹配scope，两个manifest登记1442输入且仅runtime_storage变化；npc_repairs实际SHA=3cc4ff7dc2a956946fd31debb18b1a3773d6ca472b93b218fcc257e5aaf86884未变。记录绑定seal=8f112fa854689f2735679e258316bcc16d74734eedcd3bbc05a426a8fdaa2ea4。

只读冻结候选及其依赖，未运行测试、服务、正式/临时DB、GUI或战斗；不把root的Owner红绿当本轴执行证据，未证明现场修理、真实断线或容量。只新增本报告；无Git/提交列表。


## Spec

# Spec 独立审查

缺失0、额外行为0、错误0；未读取Standards。

`NPC_REPAIR_RESOURCE_ACTIVATION.md:15`明确“去掉…临时…门控”“传入启动的…两规则；原三参数final precommit保持”，并要求“不应另补source-only同步，也不引入资源迁移”。候选 `runtime_storage.py:693–699`逐项落实，仅改此函数，真实Owner原method2入口得以进入既有深Module；未扩大855、Inventory/PetStone或特殊修理范围。

`NPC_ASSET_RESOURCE_INTEGRATION.md:8/16`要求fresh专用equipment_repair与paid当前只读。准确candidate/source的 `npc_repairs.py:70–117`在同一当前租约连接事务内先查共同receipt并严格读取before/source；fresh才实际draw、修理/费用、按actual after_caps计划equipment_repair、完整before CAS及共同receipt。`inventory.py:937–943`仍只准owned普通装备；底层费用/condition/Inventory凭据共用该db。无数值/caps变化时 `role_resource_plan.py:132–135`保留数字resource version，10/20伤势不会被治疗；上限变化仍依原保持/裁剪政策。

paid分支跳过L89–103的draw、扣费、repair及资源transition，包括legacy已付之后显式迁移；L104–116严格读当前profile/耐久/钱包并执行原final precommit。shared L832–841同db读取当前profile、实际native编码；任何末端异常退出原事务会回滚费用、condition、来源及所有关联receipt。ResourceNotInitialized仅保留原兼容路径，不初始化profile、不追补历史transition。

方法：沿用完整code-review/codebase-design及项目单Owner/调用方事务约束，以实际公开修理Interface追到CAS与最后编码；只读candidate及其release/source依赖。非Git：候选/BASE runtime_storage两SHA、npc_repairs不变SHA、diff、manifest/candidate记录及seal均核对；两manifest仅runtime_storage不同，其余1441登记SHA相同。scope前后 `31d2805294b1fe47e5bd07747c1698d2bbf9b572d286433c7a137d2ae77efb87`稳定；最终源码 `9cdcc5cd708f9cc03441e85c393830151ebd7a0814ccedf6f7ed25237b546b43`再核一致；seal `8f112fa854689f2735679e258316bcc16d74734eedcd3bbc05a426a8fdaa2ea4`。

仅静态，未执行Owner/care/legacy测试、DB、服务、GUI或战斗。准确红转绿及必要回归由集成方另闭合；不以此报告宣称已部署或现场完成。


## root准确运行验收

准确BASE204238与candidate023920完整manifest比较，只runtime_storage.repair_role_equipment变更，其他1441输入完全继承；NPC领域3cc4...未动。root独立同104bef21公开Owner探针对BASE实际RED精确guard、候选GREEN，fee20、当前10HP/20MP/vitals版本保持/condition+1/paid current-only。另care-all七组actual encrypted Owner通过：later30/40、legacy-paid明确迁移后70/40/cash960无回溯transition、最终map编码故障全回滚和同ID成功重试、重登/旧Owner拒绝及无关pending source拒绝。root并未把workspace绿当候选。

main准确11项均exit0/same8f112...seal，root逐result和actual imports/hash复核，源码1442/harness422/workspace1208/runner完整前后稳定；BASE探针为明确补充测试，不伪称原46项之一。预检正式库只读备份→丢弃副本启动110旧表全行保持/quick_check ok/无新表，root仅读报告。

两轴全0，host r2原优化绕过/EOF无界已闭合且root普通/-O独立五组绿，下一发布必须用签过的79c055 launcher/1d032 health helper和b0 controlled proof，BASE实际16276，现服不因工具复验重启。待最终deployer仅单一发布者、Established0/at-stop一致备份/正确job/source/startup/601/110表postgate核完再签。无自动profile迁移、无特殊855或鉴定/会员AOI/整份Inventory扩权，不宣称GUI/商业容量。


最终deployer已只读核：精确023920/当前BASE16276、root runtime与host r2 receipt及所有报告/3工具+b0 SHA、唯一进程和最终Established0、at-stop一致备份；使用已审detached launcher，不含Start-Process，再独立601/表/实际previous-pid postgate。现签精确单次main协调发布，发布后root做新PID/完整源码/445启动/恢复报告和跨tool/turn复核，禁止连续第二发布。

# 已知资源角色的NPC修理接线缺口

2026-10-24T02:55Z已上线并独立验收：`npc-repair-20261024T023920Z`/PID7456，由main唯一切换，root签发11项/补验及双轴0。NPC另核原same-probe在准确BASE红→候选绿、精确一函数AST差异、正式OS/1442源/runner/445启动SHA/601/未认证心跳、110表全行及结构与本次at-stop一致/quick_checkok，以及真实当前tool/saved launcher job中不含目标。证据npc-repair-deployment-owner-verification.json及npc-runtime-recovery-owner-20261024T025504Z.json；旧16xxx/35568均为历史，不改旧封签。仅普通已知资源修理解闭，field/费用/特殊855/GUI及全NPC范围不因此完成；后续BASE为023920/7456。

2026-10-24准确repair候选已由NPC独立转绿：`npc-repair-20261024T023920Z`以204238为BASE，1442生产输入只改runtime_storage.py（9cdcc5cd708f9cc03441e85c393830151ebd7a0814ccedf6f7ed25237b546b43），NpcRepairs仍3cc4...不变。`staging/verify_npc_repair_candidate_owner.py`严格核AST：只移除原临时guard、注入既有两规则；原final precommit及全模块其余导入/常量/函数保持。原冻结harness中的同一真实Owner探针SHA未变，fresh fee20/10HP20MP/condition版+1及paid-current-only通过；全部生产/助手/配置前后SHA与实际导入来源一致，只重定向报告sink。证据`npc-repair-candidate-owner-npc-repair-20261024T023920Z/owner-acceptance.json`。这是准确候选归属验收；main11项、root双轴和正式发布仍另等，不以该绿例推GUI或全NPC完成。

2026-10-24T02:36Z后续准确BASE更新：`world-collision-20261023T204238Z`/实际PID16276已完成NPC独立OS/1442源/445启动SHA/601/心跳及恢复前110表全行/结构核验，独立即时job观察与受控宿主关闭proof分开保存。修理候选须继承本版，不回退193742。旧修理门控及其它47个非prepare函数在此版与193742 AST相同；19个NPC输入亦未变。NPC已用下述原探针对准确204238独立重现同一门控，证据目录`npc-repair-published-base-diagnosis-20261024/world-collision-20261023T204238Z`，1442生产/421harness/1207配置前后保持。复跑`staging/diagnose_npc_repair_published_base.py --release world-collision-20261023T204238Z`；driver exit0代表准确复现红例，不是修复。

2026-10-24，NPC窗口。本批仅新增所属验证与只读诊断，未修改shared、真人库或服务。准确发布源BASE为`npc-loyalty-20261023T193742Z`，首次进程48572；02:17Z同批准源恢复后实际进程为3396。NPC独立核1440源/runner/444启动SHA与本次恢复前110表全行/结构一致，见npc-runtime-recovery-owner-20261024T021748Z.json。下文冻结源红例保持，不把历史PID当在线进程。

## 实际反馈与所需改动

`staging/diagnose_npc_repair_published_base.py`在该不可变BASE的全部生产、harness及原配置校验下运行新的单角色公开回归。临时明确L21/已迁移10HP/20MP/当前source/已穿49009，真实RoleOwner收到原method2请求，在进入修理结算前准确抛出`repair resource contract awaits its receipt-aware Interface`。1440生产输入及导入来源前后保持；实际存档/GUI/监听未操作。原始结果与来源清单在`npc-repair-published-base-diagnosis-20261024`。

同一个`verify_npc_repair_resource_runtime.py`在已接线工作区通过：普通费20、原完整20项map、人物10/20及数字资源版本保持、耐久版前进、已付同命令只读当前而不再收费。此为对照反馈，不将整个工作区当发布候选。关键NPC领域`npc_repairs.py`在工作区与实际BASE字节相同，SHA256均为`3cc4ff7dc2a956946fd31debb18b1a3773d6ca472b93b218fcc257e5aaf86884`。

主集成方应从准确BASE只修改`runtime_storage.repair_role_equipment`：去掉该临时`_require_unmigrated_operation`，向既有`npc_repairs.repair`传入启动的`resource_rules=accounts.resource_rules,equipment_rules=accounts.equipment_attribute_rules`；原三参数final precommit保持。NPC领域自身已有fresh equipment_repair/caps计划、paid当前只读及最终编码，不应另补source-only同步，也不引入资源迁移。既有批准契约见NPC_ASSET_RESOURCE_INTEGRATION步骤2、RESOURCE_NPC_NEXT_BATCH_PLAN及RESOURCE_SHARED_RUNTIME_INTEGRATION。

完成标准：main单写准确shared候选/独立审查，原发布BASE红例原样转绿，补原`verify_resource_npc_care_runtime --case repair`及legacy-paid、旧装备修理/宠物恢复/当前已发布功能必要回归，再按统一发布流程处理。NPC窗口不自行移除门控或将已有workspace绿外推该候选/现服；碰撞或其它shared未审变更不能随整文件混入。

## 本批方法

diagnosing-bugs沿真实RoleOwner Seam建立约8秒的确定性反馈，从相同fixture取得准确临时拒绝原因，再以同字节NPC领域和已接线工作区作为对照。异常直接命名临时门控，且其批准的替代Interface已存在，因此不再发散3–5个无区分度假设或做历史bisection；仍由main的准确单函数差异与同例转绿证明实际修复。tdd新增实际BASE失败的公开回归，保留原症状；codebase-design复用NPC拥有的外层事务和角色source/final编码Interface；writing-for-agents把必要共享接线、证据和完成条件共置。未宣称完整六槽容量、自动profile激活、GUI或全NPC功能完成。

# NPC忠诚报价v2接线与验收

2026-10-24T02:17Z恢复更新：同一已批准193742不可变源现由main恢复为PID3396；NPC独立核实际OS/唯一28993、1440源/runner/444启动SHA、601/未认证心跳及本次恢复前110表全行/结构一致，见npc-runtime-recovery-owner-20261024T021748Z.json。首次发布48572及原candidate/ready/seal保留历史，不改写成3396；后续集成基于同源193742和新实际进程3396。未借恢复发布未签碰撞、修理或鉴定。

2026-10-24。单一费用配方为[设计裁定](NPC_PET_LOYALTY_V2_DECISION.md)及`design/npc-pet-loyalty-v2.json`；原公式证据见[NPC_LOYALTY_QUOTE_NATIVE_RESEARCH](NPC_LOYALTY_QUOTE_NATIVE_RESEARCH.md)。此页负责实现与交单，不复制完整政策。领域及实际Owner隔离验证通过，固定双轴分别0，两个独立审查者各重放六组/34坏配方及Owner六组成功。完整三输入候选另经root r2双轴0、main及NPC独立exact接受，现已发布193742/PID48572；准确输入及状态为`npc-pet-loyalty-v2-ready.json`，原生GUI仍另验。

## 启动与生产输入

NPC所属增量为`npc_recovery.py`与新费用JSON。既有`npc_gameplay.prepare`仍调用`npc_recovery.prepare`；该方法在原care/blood快照之后严格加载新配方，冻结在`accounts.npc_recovery_rules.loyalty`。没有新增路由、注册、DB表或第二份资源存储。新loader显式支持`path`仅供启动检查；热路径使用同一care/blood对象，不读取文件。

准确BASE接线更正：本窗口及两审的六组Owner验证使用工作区已去临时guard的`runtime_storage.npc_recover_resources`，不是14480副本。main构建exact候选时发现14480仍有`kind!=1 → _require_unmigrated_operation`两行，已迁移角色会被挡住；此前“两输入无需shared”的表述只适用于工作区，不能外推新BASE。完整后续发布还需main从14480准确副本仅删这两行，保留其它BASE差异，作为第三生产文件单独复审并让同一Owner测试在exact候选转绿。修理guard或其它shared变更不随之带入。既有source契约见RESOURCE_SHARED_RUNTIME_INTEGRATION及RESOURCE_NPC_NEXT_BATCH_PLAN；NPC窗口未修改共享文件。

历史private14480组合保持BASE恢复模块；本片完成独立复审、candidate/hash与必要回归后，以三输入增量单独发布并继承其全部既有功能。单一集成窗口统一发布，NPC窗口不自行操作真人或重启。

准确候选`npc-loyalty-20261023T193742Z`以14480为BASE。NPC窗口独立按manifest核恰三输入变化、无删除，shared原字节仅上述两行删除；实际执行冻结domain六组/34坏配方及Owner六组均通过，1440生产和实际import来源前后保持，seal为`e89add66f12a15daf2dea77163162ab85e9ec49fb722480d8aa866e4a34b6e4f`。独立输出在`npc-loyalty-candidate-owner-20261024`，只把外部报告写入重定向到本窗口目录，未覆盖mainchecks或修改冻结源。root r2两轴分别0后由main统一切换；NPC随后独立核48572真实runner/唯一28993、1440生产/runner/全部启动Python SHA及原601/未认证心跳，mode=ro比较110表全行与at-stop一致、无新表、quick_check ok。结果在`npc-loyalty-deployment-owner-verification.json`，未认证真人或操作GUI/战斗，未重启服务。后续准确BASE为48572/193742。

## 结算Interface及兼容

仍使用公开`plan`及`settle`，请求为原CRecovery，训练师资格和kind含义不变。新报价只进入kind3和kind4的忠诚项。事务当前快照验证care，known blood复核当前原色上限，读取`PetBlood.power`，每宠各算其原个位单价；缺失blood使用明确旧兼容来源。没有growth的旧宠另经公开`pet_blood.load`区分真正缺失与孤立/损坏的present数据，后者拒绝。

新凭据保留原list及before字段，每个变更宠物新增`loyalty_quote`，含`fee_recipe/power/remainder/unit_fee/source/deficit/contribution`。原`npc.1`以及`('recovery',revision,npc_id,kind)`指纹完全保留。先查旧共同/领域凭据，命中时不执行新报价或恢复，只编码当前状态。不会补扣900与1260的差额，也不会复原旧忠诚。原kind2、inn、现金npc_shop和单一source同步契约沿用。

## 实际反馈

- 原整段报价80例由研究者及NPC主窗口各原样运行，四份研究产物SHA相同；独立记录为`npc-loyalty-quote-native-independent.json`。
- 最初真实公开领域差例保留在`npc-loyalty-quote-domain-baseline.json`：power9/1139均扣900，原报1260；修正后三例0/9/1139为900/1260/1260。
- `verify_npc_loyalty_quote.py`六组、34坏启动配方通过。含原个位0..9与异色多宠13例、未知旧blood两种形态、20/21门槛、kind2/4、无宠/全满、余额不足、坏known/orphan、真实晚期SQL与标准库编码分配失败全回滚、同失败ID重试。历史兼容实际加载冻结的旧恢复Module扣900，再公开defeat和血脉道具令power209；新Module重放旧ID全表只读，新ID才扣1260。10项关键输入前后SHA稳定，此范围不是发布完整闭包。
- `verify_npc_loyalty_quote_runtime.py`六组通过。真实加密Peer原295菜单→kind3扣1260；实际回包经原SRefreshPet decoder及原blood消费，确认loyalty100/lifetime6000与power9/cap1139/颜色1/level0。当前单一人物资源10/20及vitals版本保持。paid后伤势只读、真实source SQL故障及晚期编码故障回滚，失败同ID后成功一次，重登与旧epoch拒绝通过。均为临时已知L21 fixture，无实际战斗。
- 原两个训练师恢复、inn资源12项回归通过，血脉个位0仍保留原收费。当前冻结review见`reviews/npc-loyalty-quote-20261024`；最终结论以其中双轴报告及ready为准。

## 本批采用方法与剩余范围

diagnosing-bugs以实际900对1260的最小差例建立因果；research追原Pet scalar→1140→原取余→逐宠累加，而非颜色或派生等级。tdd在已有NPC角色结算公开Seam保留真实RED后逐纵切转绿，预期金额来自独立原指令字面量；故障只注入外部SQLite触发器、标准库分配/文件读取，不替换领域、dispatcher或自有编码函数。codebase-design把费用留在既有角色事务Module，并复用公开资产读取与source Interface；code-review固定字节base/current双轴；writing-for-agents共置生产输入、执行条件和可判定验收。

尚未验证真人/GUI报价和恢复交互、完整异常原存档处理、商业容量或全部NPC恢复。原客户端公式client_verified，服务端采用、旧档兼容及现金用途由主策划designed；本片不更改原服未知规则的来源状态。

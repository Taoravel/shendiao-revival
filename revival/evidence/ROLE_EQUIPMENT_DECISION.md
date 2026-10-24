# 师承武器与人物当前总属性接线

2026-10-23，主策划。穿脱、耐久变化、成长后刷新或重登入场涉及师承武器时，先读EQUIPMENT_ROLE_ATTRIBUTE_RESEARCH，再用design/role-equipment-v1.json。原modifier81/811/1231→人物总键80/810/1230的映射与25/15/8来自客户端；相加公式、裸身加强封印0及成长不追加封印为明确设计，只支持已列10件未增加高级修饰的师承武器。

## Interface与提交顺序

1. 启动加载`load_equipment_attribute_rules()`，并调用`prepare_equipment_attribute_storage(db)`建schema。读取原描述表、10模板及30形象映射完成后注入只读rules。准备不创建任何角色基线。
2. 角色有效租约事务下，可信创建流程取得原新手来源后，显式构造`EquipmentAttributeBasis(role_id, character_id, 0, rules.revision, rules.new_role_seal_strength, source_id)`，source_id引用该持久创建操作；`initialize_equipment_attribute_basis`保存一次。已存在但有明确本地创建模板/创建操作的恢复新角色，也可按这项设计显式补该辅助基线；授权来自来源证明，不来自字段缺失。无明确新建来源的旧角色只接受已知裸身封印值及来源的基线，不由旧九项属性、XP或等级推0。相同重试不重置，不同值/来源拒绝，政策变化另作迁移。租约允许有效opaque字符串及63位正整数；字符串原样比较，00007不归一成7，bool拒绝。
3. 在同一个调用方事务完成任务/装备/耐久/成长变化后，调用`Inventory.immutable_snapshot_transaction(db)`读取当前冻结资产，交`current_equipment_projection(db,account_id,role_id,epoch,snapshot,rules)`。它验证当前租约、原角色形象、资产版本，重读当前裸身成长和显式封印基线，再调用纯`project_equipment`。基线不存在会明确报EquipmentBasisNotInitialized；调用方可保留已登记的旧兼容路径，不能悄悄造0。
4. 纯投影从裸身快照重新算，返回冻结`EquipmentRoleSnapshot`，同时带inventory_revision/basis revision/policy。只接受slot0、原roleNeed兼容、已知耐久和已鉴定clean EquipmentDetail且base_properties恰为原三项；缺详情、未知模板/修饰/数量/槽位拒绝。耐久0按已登记装备政策移除贡献。投影不能再次作为裸身输入，不将历史装备凭据或上次总值当基准。
5. 提交前以`growth_refresh(current_growth, projection)`验证/编码20项当前总值，含1230；`role_detail_equipment_fields`提供同一投影的32i索引8/12/14。生命、真气、伤势及其版本保持原对象，不因武器展示恢复。signed32/float32不精确全部拒绝，装备、任务和其凭据随外层事务回滚。成功提交后才按角色顺序发布/发包；重试、用药、任务升级、重登都须用当前组合快照，避免后来普通裸身刷新覆盖已装备总值。

角色/共享存储Adapter负责上述接线和来源证明；根窗口维护纯数值、基线存储与协议映射；库存窗口提供当前同事务资产及真实装备事件；世界窗口消费同一入场投影。没有新的世界锁、全服执行队列或第二份增量总属性账本。

## 必要验证与边界

`verify_role_equipment.py`已运行：裸身L2外伤24/内伤23→装备49/38/封印8；重算/替换不重复加，穿脱/耐久0恢复裸身，显式已知旧封印11→19；HP80/110、MP46/106及资源版本对象保持。20项map匹配原x86序列化/解码，入场索引8/12/14同源；角色/重复/已投影输入、未知详情/高级修饰及溢出/float不精确拒绝。原`verify_role_growth_protocol`19项裸身检查仍通过；当前运行时import也成功。

`verify_role_equipment_storage.py`已运行：临时旧角色没有默认基线；显式11保存一次、不允许重置；真实Inventory.equip_transaction后在同一事务读资产，20+25=45、20+15=35、11+8=19，HP70/MP40不变。旧资产版本拒绝，历史装备命令不重新穿戴，受控外层晚期失败使替换与凭据回滚；float不精确使新基线、穿戴和凭据一起回滚；新租约读回而旧租约拒绝。该检查不包含真实TaskWorkflow/type59或共享Owner接线。

方法：research限制为原numid关系及绝对值消费者，未知百分比顺序留在范围外；codebase-design以公开不可变快照为Seam，投影Module隐藏属性族/重复加算/精度约束，持久化Adapter隐藏租约与基线幂等；writing-for-agents共置初始化、事务、刷新和恢复分支。产物见role_equipment、role_equipment_storage、政策、两个验证入口及相应verification.json。尚未接共享角色创建/任务加点用药/入场的总投影，未宣称原版完整装备公式、战斗效果或GUI；用户已授权部署的intro进程继续保留，本批后续源码不自动部署。

世界入口字段已由其窗口消费同一profile，并由root独立运行verify_world_equipment_entry_native通过：装备49/38/8、损坏24/23/0，HP80/110和MP46/106、真实EXP61及intro1保持；显式growth参数另核五维11和潜能5。root的非对称五维/潜能7真实world encoder→原decoder也通过，见ROLE_ATTRIBUTES_DECISION。仍待共享Owner初始化basis和所有刷新路径采用当前总投影；当前进程不自动重启。

后续共享接线已在独立自然师父反馈转绿：创建来源授权辅助basis，实际选中实例穿脱、任务完成和入场重连使用同一当前投影；load传完整growth。root增强并执行verify_first_master_runtime，20/20/0→45/35/8→脱下20/20/0→重穿45/35/8，重建Runtime原entry保持，物品仍唯一且任务/经验不重结。具体自然前置和限制查NEWBIE_MASTER_CARD_DECISION；现运行8724固定副本仍未包含此后源码。

修理的shared `equipment_projection_messages`已由root新增verify_role_equipment_repair_hook独立调用验证。复用NPC真实Inventory/租约/损坏/修理故障夹具及其独立oracle，在同一事务中执行实际shared hook：损坏0→修复45/35/19（显式旧封印基线11），HP70/MP40保持；真实全map编码后注入晚期错误使耐久/现金/凭据一起回滚；同键再试及提交后重试不重抽；最终16777217不能精确float32时实际shared投影拒绝并回滚。它只证明实际shared precommit Seam，不冒称已装备profile的NPC线包端到端；自然穿脱Owner另由上项覆盖。

普通六槽扩大范围先读ORDINARY_EQUIPMENT_ATTRIBUTE_RESEARCH及全量审计JSON：1038=875非空flat且属性ID可映射+98缺1240封印抗性基线+1百分比49192+64缺基础列表。六部位为武器/护腕/项链/衣服/腰带/鞋，当前生产白名单仍10件。HP/MP上限及伤势的组合/存储尚需版本化恢复政策和事务迁移，不能直接套本政策“不动vitals”扩全装备；未知百分比、实例附加项及缺表不默默当0。

本批追加两项独立复跑已通过：`verify_equipped_growth_runtime.py`使用明确已知旧角色成长/经验/装备/基线夹具，经真实Owner得到登录45/35/8→手动升级49/38/8→力量+1为51/39/8，脱装26/24/0、重穿/重连仍51/39/8；实际全map编码错误使已执行穿戴与命令凭据一起回滚。该受控夹具与自然新建链分开，不声称自然升级到10级。`verify_npc_equipped_repair_runtime.py`则补闭此前hook范围：真实加密连接EQUIP及NPC method2/column4修理，经实际repair_role_equipment发一份完整20项45/35/19，HP70/MP40保持、现金1000→960，正常随机修理的状态与重连一致；没有替换生产dispatcher或projection。两项均临时库，无GUI、在线库或部署。

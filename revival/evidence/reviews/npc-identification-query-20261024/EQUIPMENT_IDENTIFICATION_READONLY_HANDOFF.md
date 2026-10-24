# 装备鉴定：当前详情能力与事务交单

2026-10-24，应主策划鉴定政策收口请求，只读核对所属实现与原解析器；未实现收费动作、修改shared、运行服或真实实例。495/496、10890及费用配方由主策划/NPC窗口裁定，本文不推NPC授权。

## identified的精确边界

当前EquipmentDetail.identified是显式0/1字段；本地工厂的1表示设计的“已鉴定干净基线”，0表示本地模型尚未鉴定。原generic详情首个BE32在107d9db..107d9ef原样写EquipObject+58。research_equipment_identification.py执行六槽各一个实际原完整107d960解析器，分别输入0和1；除该字段外字节、当前/上限耐久、prefix/score/color和全部已提供基础map均不变。结果equipment-identification-readonly.json，来源client_verified，范围仅原解析器对已提供详情的读取。

**unknown：原服在生成物品时已抽好随机属性、还是鉴定时抽取；原客户端未鉴定提示具体隐藏哪些属性；是否允许未鉴定穿戴及所有业务资格。** parser能读取0状态的非空map，只证明线包可以携带这些已给定属性，不能证明原服的隐藏属性机制或生成时机。本地EquipmentDetail没有尚未揭示随机种子/抽样结果、附加属性map、宝石或强化权威；当前encode把相应高级容器置空。因此不能收费后凭模板新造“原有隐藏随机属性”，也不能把unknown详情套工厂后视为鉴定完成。

## 可供政策限定的干净实例

可信持久origin仅restoration_grant或explicit_known_clean_instance，revision须2026-10-23.equipment-detail.1；模板必须在启动DetailRules.templates。该集合依据原itemtype低四位8、槽位高四位0..5，排除CGodWeapon。数量1、所属角色、物品实例key/当前栏位、binding及quality从同事务读取；binding0/1与鉴定独立，不擅自解绑定、改绑定或合堆。

若政策只允许“揭示既存干净基础map”，建议判据为：identified0、prefix_quality1、score0、base_properties与该模板原有效配对完全相等、无食品quality、已知EquipmentCondition且颜色1，持久来源明确保证无高级扩展。仅这四个数值本身不能证明任意旧实例没有高级属性。评分/颜色不同、未知来源/版本、非空高级内容尚无模型、神兵、原套装语义、百分比/未知修饰均另行拒绝或恢复。

普通六槽v2最终投影还要求当前角色持久basis精确选中v2、原template收录、roleNeed/sexNeed/人物等级/槽位合法、无未恢复套装等。默认v1仅已授权师承武器，不能因详情支持1038模板就自动开放全部装备属性。identified0的已穿装备目前会被role_equipment.project_equipment_totals拒绝；最小可靠纵切应限**自有携带栏、未穿戴、已知干净0状态**，不要绕过投影门禁给已穿未知物品收费。

## 当前Interface与尚需实现

已存在只读Interface：Inventory.immutable_snapshot_transaction(db,epoch=...)校验活动租约/角色并冻结当前实例；equipment_detail(db,key)读取明确revision/origin的详情；equipment_condition(db,key)读取当前条件；equipment_bag_messages(db,epoch)生成当前两栏；ITEM_TIPS通过详情encode与原完整解析器。读取详情本身只有角色归属检查，不替代外层活动epoch校验。

**当前没有0→1鉴定写入Interface或鉴定凭据。** initialize_equipment_detail只能一次初始化明确干净旧实例，已有详情拒绝覆盖；不得拿它重置鉴定或属性。EquipmentDetail没有数值version，只有存档revision；EquipmentCondition.version专属耐久，不是详情修改版本。若实现，应新增所属调用方事务操作，接受稳定命令ID、有效epoch、实例key、期望当前详情/资产版本及已裁定政策；按原detail JSON和持久来源做CAS，唯一修改identified并保留完整基础map，推进inventory_revision，记录意图与前后状态凭据。所有者/当前携带位置/数量/binding/条件及政策复核均在同一事务。

NPC资格和扣费须由其可信服务凭据及已裁定货币配方加入**同db事务**，不能先独立扣款再鉴定。既有precommit契约(db,inventory,current_frozen_assets,*,replayed)用于root唯一resource source同步；即便携带详情改变不影响人物caps，也须更新资产来源而非留下pending。若未来允许已穿实例，使用当前持久equipment policy重算最终属性，按role-resources政策处理HP/MP并原生完整刷新，禁止另建装备资源副本。

paid只验证意图并读取当前详情/物品/钱包/人物source，不再扣费、不把历史map或identified写回；后续销毁、转移等状态按对应当前资产协议处理。费用、详情、资产revision、source及共同/领域receipt均须原子回滚；原生编码在提交前完成。完成条件为实际同Owner命令的双击/重试、扣款/详情/source/回复故障回滚、重登与原客户端提示验收，当前只读查询不代表这些收费链路完成。

方法：codebase-design定位已有事务Seam和缺失鉴定写入Interface；research沿原首字段存储与完整解析器作0/1差分，六槽独立字段保持一致；writing-for-agents将可用接口、明确unknown及下一纵切完成条件集中于本文。未改任何生产实现，不做随机生成或收费承诺。

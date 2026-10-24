# 固定结果鉴定：公开资产CAS与现金用途

稳定交付：`equipment-identification-assets-ready.json`保存三个生产文件SHA、四个验证文件SHA及1,272项固定依赖。双轴R1的一处P3重复判据已集中，R2独立复审Standards0/Spec0，完整报告见[固定R2审查](reviews/equipment-identification-assets-20261024-r2/REVIEW.md)。消费此ready期间保持三生产文件/公开Interface稳定；只集成本片差异，完整inventory.py所含此前进化/灵石不由此默认夹入shared。主集成继续按实际发布BASE核对依赖闭包。

2026-10-24。接NPC收费结算前读本页；NPC授权/报价唯一政策仍为`design/npc-equipment-identification-v1.json`与`NPC_EQUIPMENT_IDENTIFICATION_DECISION.md`。所属资产CAS、调用方事务内当前详情回复、cash purpose与实际root source组合已实现；NPC窗口随后提供的真实settle已使用这些公开接口，本窗口独立组合复验通过。共享收费路由、发布/GUI继续待验。只读调查`EQUIPMENT_IDENTIFICATION_READONLY_HANDOFF.md`中“没有写接口”是此前阶段。

## NPC调用顺序与完成条件

1. NPC Module负责当前可信495查询ticket、所选key在冻结vector中、原mode1/aux0、NPC与完整地址/连接地图世代、非战斗、期限和唯一受理身份。开始当前角色租约事务，先核对专用NPC凭据的完整意图；paid分支跳到第5步。原线包没有重试ID，ticket的已付确认不能作为另一笔新费用。
2. fresh在**同db**调用`inventory.equipment_identification_basis(db,key,epoch,expected_inventory_revision=ticket.query.inventory_revision)`。关键字参数须传原查询版本，不能仅重取当前版本代替旧报价。返回不可变`EquipmentIdentificationBasis(inventory_revision,item,detail_revision,detail_origin,detail_json)`；item是完整ItemState。读取不写状态、不提供NPC权限或价格。可在query阶段不传expected参数取得原始basis，但确认仍须按原ticket复核。
3. 按已冻结CItemAttr.level精确查原16档费用；NPC自己以`CurrencyChange(stable_fee_id,'npc_equipment_identify',stable_source_ref,(('cash',-quote),))`调用现有apply_currency，再调用`inventory.identify_equipment_clean_transaction(db,basis,epoch,precommit=source_hook)`。返回`EquipmentIdentificationChange(before,item,inventory_revision)`。该方法无内部commit、连接、RNG、发送或鉴定receipt；它是一次CAS，**paid不得再次调用**。稳定费用/专用鉴定意图凭据由NPC唯一持有，避免两套鉴定去重来源。
4. CAS重新检查当前有效role/account/epoch、完整ItemState和库存版本，SQL按item key+detail revision+origin+原完整JSON更新，只改identified0→1，随后库存revision做expected→expected+1 CAS。precommit沿既有契约`(db,inventory,current_snapshot,*,replayed=False)`在同事务可见费用和新详情，接现有唯一root source。NPC可将共同凭据/领域记录及当前消息编码放在同一个外层事务；任何失败由外层回滚。
5. 当前回复使用`inventory.equipment_tip_message(db,key,epoch)`和`inventory.equipment_bag_messages(db,epoch)`，返回逻辑消息，前者是实际当前栏位1/4的SItemTips。两者支持读到本事务尚未提交的鉴定结果，不能改用Inventory.receive(ITEM_TIPS)另开连接。钱包另读read_wallet后投影当前绝对余额。paid核对自己的历史意图后，root source使用既有replayed=True严格当前只读分支，跳过资产CAS/扣费；物品后来穿戴则tips当前column4，后来删除/不在当前携带与装备表则只按当前存量回复，不复写历史详情。编码完成后才commit，再由当前连接所有者投递。
6. NPC片完成条件：真实专用凭据、新确认与同ticket重复区分、费用与完整CAS/source/凭据/当前编码全部同事务、失效proof/旧版本/旧epoch无扣费、晚期故障回滚、重登及加密Owner路线；随后独立审查/共享接线/发布/GUI。本批直接调用方组合验证不替代这些NPC条件。

## 资产资格与来源

当前只接受携带未穿、量1、有效背包位置、DetailRules已支持的普通六槽非神兵，排除fullkind0x1c8/0x2c8/0x3c8。详情revision必须当前equipment-detail.1、origin必须**explicit_known_clean_instance**；不是凭四个值把任意旧实例当作已知干净结果。identified0/prefix1/score0、完整基础map与原模板精确相同、已知color1 EquipmentCondition。支持保存中的binding/quality/slot/耐久原值，CAS不变更它们。

默认restoration_grant继续生成identified1；未知旧详情/条件/来源/修订不初始化、不迁移。已鉴定1新请求明确拒绝，已付由NPC凭据只读处理。普通携带50级装备可按其装备level报价，人物级别不代替物品level；鉴定不授予穿戴资格或切role-equipment.v2。未恢复的高级随机属性、宝石、强化与附加技能不由此生成。原完整解析器接受0/1及既存非空基础map，只证明这些已给定数据布局，不证明原服随机结果的生成时机。

## cash用途增量

`design/currency-v1.json`仅在cash.spend_purposes追加`npc_equipment_identify`及说明，既有`2026-10-23.currency.1`、币种映射、钱包基线、旧指纹/凭据不变。其它三个币种没有该扣费用途；余额不足整笔拒绝，无绑银替代、混付或欠款。Currency只管理可信账本，不验证NPC价格；NPC须保证delta为负的原精确quote并证明授权。没有改currency.py或默认运行时注册/路由，也没有自动创建未知钱包。

## 实际验证与方法

- `verify_equipment_identification_cas`：公开接口先红后绿；六槽真实50级模板经原完整详情解析器，首个SItemTips另过原codec；只改identified，库存恰+1。完整JSON/origin/政策/绑定/quality比较、移动再移回的旧查询版本、已1/自造0下restoration_grant/外物/已穿/缺详情/缺条件/未知来源修订/非法epoch/key拒绝。四真实写入点、source回调、晚期tip/bag编码故障回滚费用/详情/库存/钱包凭据；失败ID重试一次。只读当前tips/bags/paid费用、无热配置读取、重开与真实opaque换租约通过。
- `verify_equipment_identification_currency`：按原50级15000算例，30000→旧shop29000→鉴定14000，其它余额90000/300/700不变；不足cash即使绑银富余也拒绝。非cash/混付无部分扣款，无新凭据。用旧允许集合实际创建的历史指纹/正文在新增用途后不变，旧/新paid均SQL禁止写，UI投影当前14000。
- `verify_equipment_identification_source`：已知显式资源fixture，调用真正runtime_storage._synchronize_source与root source存储；未改共享代码。实际来源receipt写入失败、source CAS后抛错、晚期详情编码均回滚资产/cash/source/所有相关凭据；同失败ID后仅一次生效。HP10/MP20/version0及最终上限保持，资产source版本更新；replayed=True/current tips/bags/paid cash全程SQL只读。
- NPC窗口`verify_npc_equipment_identification`已由本窗口原样独立运行通过，真实query→confirm→settle→公开CAS/cash/source及原完整详情解析器闭合。另新增所属`verify_equipment_identification_npc_compat`只调用其公开Interface：真正NPC专用receipt、NPC共同receipt、resource-source receipt三写入点和晚期tip编码故障全部回滚；同失败ticket后每类凭据恰+1、cash2000→1900。保留真实FencedConnection，在底层SQLite authorizer禁止数据写入，paid成功只读；fresh已鉴定1拒绝再收费，后来合法移动和source变化保留当前位置。未修改NPC生产文件，未替换确认dispatcher；这仍不是共享加密c4276验收。

tdd沿已约定Inventory调用方事务/原生Seam，先缺公开basis红，再cash purpose拒绝红，随后旧query版本关键字红；每片实现后验证实际行为。codebase-design将完整来源读取与CAS留在资产Module，NPC只持授权/报价/专用receipt，避免复制设备私SQL；当前详情消息可在同一Seam预编码。writing-for-agents把调用顺序、分支和完成条件集中本文。原证据沿用已完成客户端研究，不声称本批进行了新的官方检索或原服随机公式推导。

尚未验证：NPC全部proof/期限/并发分支的独立最终审查和shared加密c4276接入、实际确认UI/隐藏属性表现、正式发布、完整随机鉴定及高级装备、商业数据库与容量。此前阶段/源码、当前集成、正式发布、实机分别验收；全量恢复目标保持active。

# 普通装备宝石：有序来源、原生详情与事务基础

恢复镶嵌/摘除请求、保存宝石列表、编码非空详情或接角色装备投影前读取本页。2026-10-24。本批实现完整普通未培养210行规则、纯计划、显式来源CAS及原详情扩展；**尚不是收费镶嵌/摘除action ready**。全量恢复目标不变，后续必须补实际资产/评分/颜色/人物资源/paid共同控制器和共享入口，不能把纯计划或单独列表保存当可玩验收。

## 原依据与设计的分界

`GEM_SOCKET_SOURCE_MAPPING_RESEARCH.md`从原SGetBagInfo→Item复制/容器赋值→实际发送闭合column1→source0、column4→source1。新decoder只接受这两个来源，`request_basis`在当前角色租约事务精确比较真实容器，不跨栏兜底；单摘是宝石**模板**，全摘为-1，c0533不是普通摘除。

`EQUIPMENT_GEMS_SOURCE_RESEARCH.md`的槽位、等级等于孔位、最多三族、15封顶、普通钻36949/高级钻39649及逐行费用/返还由客户端验证。该旧报告的合成技能602053已被`GEM_COMPOSITION_RESOURCE_SOURCE.md`纠正为600005；本批孔数技能另是装备特技410006无限/410007精致，不能混作杂学等级。

规则单一政策`design/equipment-gems-v1.json`：新等级追加，原等级替换保持所在序号、被覆盖旧石不返还、验证替换后的族集合、成功后装备binding取装备/材料OR、摘下全绑定、检查通过后确定成功，均为designed。本批保留原服务器具体顺序/返还/概率未知标签，不将原parser可读当成服务端授权。

每个等级只一颗，最多三族；孔数普通min(15,有效等级//10)，精致多一且封顶，无限15。费用50×(装备原有效等级+10×宝石等级)，40级镶一级2500。高级摘除按原Diamondid降一级，费用用superremovegem；同次返还同模板合并数量，例如猫眼6+7+15全摘，普通钻32、高级钻514，返还六级2颗及十四级1颗。五行吸收和治疗量原效果全部保留在独立map，暂未具备战斗消费时不得删除。

## 可调用的Interface

启动读取`GemRules.load()`一次；`gems/equipment`为不可变配置快照。Inventory表准备好后调用`equipment_gem_storage.prepare(db)`，创建本Module唯一所有的gem来源表与实例删除/模板归属变更清理触发器。没有热路径DDL/配置加载、网络、内部连接或提交。

`GemState(version,templates,policy)`是有序不可变模板tuple，独立于EquipmentDetail.base_properties。`embed(rules,equipment,state,material,equipment_skill,flags=(known_equipment_nonbinding_flags,known_material_nonbinding_flags))`返回一次扣料/现金/绑定/替换计划；`remove(...,selection,equipment_skill,flags=known_equipment_nonbinding_flags)`返回工具总量和有序合并的绑定产物计划。两者不扣料、不扣钱、不保存、不生成score，不提供NPC/战斗/期限或连接准入。

`equipment_gem_storage.initialize(...,key,GemState(0,...),known_equipment_skill,'explicit_known_socket_profile')`只供可信完整导入，含明确已知空列表。当前四字段旧详情不证明没有宝石或装备特技；缺档保持None，不以0补齐。已存在相同baseline返回当前，不回滚后来的宝石；不同baseline拒绝。

`read`返回冻结EquipmentGemBasis：完整当前ItemState、库存revision、当前GemState、明确装备特技、gem原JSON/来源，以及detail/condition完整原始来源。`request_basis`另按原请求严格定位当前栏位。`replace_state(db,inventory,rules,before,after)`仅下一版本CAS，完整basis重新比较，按原policy/origin/raw state/skill更新，并CAS提升库存revision；没有第二份paid权威。物理字段相同但移走移回、原JSON仅空白变更也会拒绝旧basis。调用方任何后续错误均须回滚整个事务。

`encode_detail(rules,current_item,current_state,known_equipment_skill)`在已有公开干净encoder的原gem vector处扩展；检查布局长度/空容器哨兵以拒绝将来结构变更。基础map、其余标量/扩展、耐久、prefix与输入score/color保持各自来源。空列表与现有encoder逐字节相同。它不是通用完整随机附加属性encoder；未来有序附加triples升级时必须集中扩详情模型，不能继续依赖固定空附加容器偏移。

## 原生与存储验证范围

`research_equipment_gem_detail.NativeGemEquipmentDetail`复用原完整构造107cf80/解析107d960到自然返回，实际执行原scalar/container、gem链表、基础map、独立gem effects清空与累计。配置row查询终端、cd0b30复制及a00730析构用静态原表Adapter；没有注入最终gem map。不是完整GUI、资源配置对象生命周期或真实装备穿戴验收。

四个verify覆盖：210原行/14族与双工具全返还、孔数/类型/顺序/四族拒绝、原六个请求codec和容器映射、原完整非空详情/清空/独立score颜色阈值、真实SQLite初始化/CAS/两写入失败/原详情编码后外层失败回滚、旧epoch/库存版本/原JSON/未知来源/重开/严格只读。worn栏正例使用明确临时存储fixture，仅证明精确栏位定位，不证明角色穿戴资格或人物最终属性生效。

## 收费动作接线前的强制闭包

1. 评分仍unknown：新研究发现cequipscoreconfig的七个直接消费者全部在强化预览，输入不是gem列表。400/420等token不能冒作普通宝石系数。由主策划按原装备score、明确裸宝石基准、旧/新有序列表及原effects集中定义可替换的designed策略；历史基准不能靠减估计宝石分反推。
2. 提供装备详情/condition同事务公开CAS更新score与color，保留当前/最大耐久及已知附加结果。现有`reconcile_color`只迁移实验v1，不能滥用为普通宝石换色。冻结鉴定provider本批保持原SHA，不借保存gem列表绕写其私有JSON。
3. 原始详情分发/背包/物品查询、穿脱/磨损修理、登录/重连和root属性投影必须都消费gem来源。旧role-equipment v1/v2明确不支持gem，不能保存非空后仍拿旧投影称完整；本批新表和低层CAS未接任何生产路由，真实数据库未导入。
4. 新最终装备策略需要一次加入全部已支持gem效果，未知五行吸收/治疗量保留到完整消费者；不能丢弃后报告完整。绿松141影响HP上限，接root唯一资源过渡保持绝对HP/MP、下调裁剪、死亡不复活；无第二套资源存档。非空gem不能只改tips而让人物无加成。
5. 控制器同事务验证可信准入/role+epoch/固定command ID/deadline、原料与工具flags来源、cash独立purpose、扣料/绑装备/返还/两类凭据/gem CAS/score-color/root source及当前原编码。已付跳过CAS、收费和工具，严格读当前；满包或任一写入/编码失败全回滚。未知产物堆不得借通用grant洗成flags0。
6. 共享逻辑投递、准确BASE集成、发布及真实GUI另外实测。资产/详情Module由本窗口维护；根/shared与人物资源仍由原集成写者单写。

本批方法：TDD沿已授权纯规则、调用方角色事务、原native接缝完成缺Module/缺encoder/缺storage/缺request decoder的red→green；codebase-design使状态/规则与调用方资产结算分层，删除没有实际生产差异的CAS回调参数，外层直接组合编码/资源；research实际纠正容器映射并排除把强化评分当宝石公式；writing-for-agents把可调用合同、完成标准与动作未完成条件共置；code-review以非Git新增文件固定清单做独立Standards/Spec审查。当前审查与最终hash/实际检查以本批batch记录为准。

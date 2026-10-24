# 荷叶羹品质寿命接线

2026-10-23。原32007荷叶羹现可从 owned carried 实例品质计算寿命并在同角色事务扣一件。沿PET_LIFETIME_ITEMS_INTEGRATION的固定寿命食品链路恢复，当前为源码、临时数据库与原生指令验证；没有部署、GUI或实际战斗验收。

## 来源和设计

pet-lifetime-source-audit.json已直接原PFS验证citemattr、cfoodanddrugeffect、cfooddrugeffectformula全部attributes/lists。32007原maxNum1，needLevel1，outbattleuse2，物品文本明确指定宠物物品界面使用；烹饪35级是制作门槛，不替换角色使用needLevel1。原效果funtionid0，原品质公式ai=[0.5,0,0]、bi=[0,0,0]。品质与模板level、使用等级、包中字段分开保存。

当前服务端设计为floor(abs(真实实例quality×原ai0+原bi0))，由精确十进制转有理数计算，无浮点误差；95→47、96→48。系数是client_verified，服务端应用/取整是designed。quality必须为已知非负signed32整数；None不猜0。已知0/1产生0效果时拒绝且不扣物。寿命signed32溢出同样拒绝；初始模板life不作封顶。可信补全集中design/pet-care-v1.json.food.lifetime_quality；不改变旧状态语义或自动迁移care.1。

本批定向检索未找到官方端游更明确的荷叶羹服务器取整或最大寿命公式，没有使用不相关搜索结果。后续32004/32009的3%副作用已单独恢复，接口与设计资质损失见PET_TOXIC_LIFETIME_INTEGRATION，不能沿本无副作用路径放行；还童状态重置仍待恢复。

原帮助也有内部冲突：bookanswer10007将荷叶羹效果写“生命”，但具体32007物品、效果表及bookanswer36001/36002的寿命食品清单共同指向寿命，因此当前按更具体证据恢复寿命，不增加HP。原帮助2123行已直接PFS全表attributes/lists比对，CRC db4543ec；见source audit新增help_audit。其他食品的制作门槛差异不扩展为本批烹饪实现。

## 接线与Interface

原生仍使用`receive_pet_consumable(body,epoch,request_id,now_ms=None,precommit=None)`；已有共享共同凭据的鲜请求也可沿`receive(USE_ITEM,body,precommit)`，paid分支保持INVENTORY_CURRENT_MUTATION_MESSAGES的严格当前只读。body仍为16字节`>iiQ`，只有实例key、kind1、pet key，客户端没有quality字段。禁止由调用方在包后追加品质或用模板默认值代替未知实例品质。时钟、资格和来源hook要求同固定食品/血脉交单。

启动prepare新增冻结CareRules.quality_lifetime_food，元素为原公式的不可变(numerator,denominator,offset)。热路径不读文件。低层可信care事务可沿现有`change_pet_care(db,pet_id,request_id,expected_version,'feed_lifetime_quality',(32007,quality))`；仅该operation支持二整数tuple，其余care操作保留严格整数值。实际原生Adapter自行读当前owned实例quality；上层不复制公式。低层操作不负责扣物，组合调用必须同事务加入物品、来源及共同凭据。

验收条件：一次增加实际品质对应的寿命并精确扣一件；care/物品/两份凭据/资产版本和root source同事务；任何保存、hook或native编码失败均回滚。只改变care.version/lifetime，原有HP/MP、忠诚、颜色、基础及血脉有效资质、潜能和技能均保留，HP0不复活。已付重试按request_id/body fingerprint只回当前寿命；原实例删除仍可读当前，后来死亡损失不补回。原maxNum1意味着新食用请求必须使用另一件真实实例，不能通过重用删除key来产生新效果。

## 方法、产物和实际验证

tdd沿既定Inventory事务/快照/原生Adapter Seam，先复现另一效果handler缺失，再加入品质操作；红→绿覆盖95/96、None/零效果、真实保存失败与原生晚期编码。最初多件食品测试错误假定可叠加，读取原maxNum1后将fixture改成合法独立实例，保留删除key重试和真实另一件食用的断言。codebase-design沿唯一care账本扩展，不新增寿命表或调用方公式；writing-for-agents记录品质来源、事务责任、历史重试和完成条件。

verify_pet_quality_lifetime及pet-quality-lifetime-verification.json通过：6000→6047原decoder、后来死亡损失到5997的paid重放保持、另一件+47→6044、96品质+48、None/0/1不消费、bool/负数/超界/可变list/非白名单拒绝；真实care receipt abort、晚期bag溢出和同失败键随后成功；HP0、signed32寿命上界、禁止热文件读取、原生额外quality拒绝、actual opaque LeasedAccounts及重开保持。

verify_inventory_resource_hook加入真实95品质食用False与已删除实例paid True，根source helper同事务完成，角色70/40和resource version0保持。固定食品、养护、HP/MP药、血脉精华、通用当前只读和共同Owner命令回归通过。此前共享NPC新资源回复缺完整人物map的缺口已在当前源码复跑verify_resource_npc_care_runtime(all)通过，覆盖repair/pet鲜请求、已付后来伤势、编码失败回滚和重连；旧NPC宠物恢复Owner也绿。这些是当前离线连接结果，不代表已部署验收。

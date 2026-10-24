# 固定寿命食品32036恢复

2026-10-23。福寿糕32036已接原宠物用物事务：每件实际增加1000寿命并扣一件，完整原生宠物刷新与当前cash背包在提交前编码。当前为所属源码/临时数据库/原客户端指令验证；共享部署与GUI、商店/奖励渠道及其余寿命食品另验，全量目标active。

## 原证据与补全范围

本批直接只读原artres/config.pfs，验证本地头/目录、解压长度和CRC，解BXML后逐条比对citemattr12280行、cfoodanddrugeffect122行、cfooddrugeffectformula38行的全部attributes/lists，与catalog一致。CRC分别a3add081、51e9855e、956924d2；详细行与SHA256见pet-lifetime-source-audit.json。比较不将XML排版text/tail当作业务字段。

32036原itemtype82、needLevel1、outbattleuse2；物品描述明确增加1000寿命且无副作用，原效果表funtionid0/effect[1000]相互支持，故走care而非HP/MP计算器。原Pet寿命bean+b0的布局与语义沿verify_pet_care原消费者证据，完整刷新decoder本批实际读到7000。

原模板life是初始值，当前没有证据将其当最大值。允许6000→7000；服务端signed32表示上限之外明确拒绝并不扣物，不凭空引入另一套玩法封顶。这个溢出处理是designed，原服最大寿命未知。角色1级按原needLevel限制；HP0可补寿命但HP保持0。只改变care.version/lifetime，忠诚、颜色、基础/有效资质、血脉、自然成长、已分配潜能和HP/MP均保留。

定向官方端游检索未找到本版最大寿命公式；[历史异士录资料](https://sdxl.wanmei.com/info/play/rut/20120728/133477.shtml)仅支持福寿糕作为可能奖励存在，[2022商城公告](https://sdxl.wanmei.com/news/gamebroad/20220428/237455.shtml)属于后期销售旁证，均不用于猜本版封顶、概率、价格或直接发奖励。未采用其他游戏或手游寿命规则。

32004岁寒三友和32009蟹黄汤包原文另有3%资质降低/中毒描述，后续真实品质、固定受理draw与明确设计资质损失已恢复，见PET_TOXIC_LIFETIME_INTEGRATION，不能沿固定1000或无副作用路径调用。32007荷叶羹已按真实品质/原0.5系数和明确设计取整恢复，见PET_QUALITY_LIFETIME_INTEGRATION。还童丹同时重置多套状态，不混进补寿命分支。

## 接线与完成条件

沿现有`receive_pet_consumable(body,epoch,request_id,now_ms=None,precommit=None)`，原body仍`>iiQ`且kind1；共同上下文与限时技能时钟要求同PET_BLOOD_ITEMS_INTEGRATION。原`receive(USE_ITEM,body,precommit)`鲜请求及旧`use_pet_consumable(key,pet)`也共用此效果分支；共享Owner若已有共同稳定命令凭据，应按INVENTORY_CURRENT_MUTATION_MESSAGES对paid分支严格只读，避免重复治疗/补寿命。没有共同命令管理的调用应使用带request_id的Adapter。

Inventory.prepare启动冻结CareRules.lifetime_food，单一数据源design/pet-care-v1.json新增固定寿命食品，不改变既有PetCare存档/历史feed或defeat语义，保留care.1版本；旧状态无需重写或补历史寿命。当前care与扣物、资产版本和care/common消费凭据同db原子提交。根source/common受理仍通过当前precommit同事务加入；提交前任一保存、hook或native编码失败均完整回滚。已付重放只发送当前寿命，不补回后来战斗损失；实例已耗尽删除也可回当前。

验收条件：明确owned live pet、当前lease与物品真实等级限制；一次+1000/扣1；跨过初始life仍正常；0寿命可恢复而HP0不复活；signed32溢出无消耗；已付同键不重复；错误事务无副作用；根来源保持当前资产版本且人物资源不治疗。真实购买/奖励、部署和现场客户端仍另验。

## 方法、产物、验证与当前阻挡

tdd在已约定Inventory事务/快照/原生Adapter Seam先实际复现“Consumable effect requires another handler”，加入care寿命操作后绿，再覆盖真实故障、重试和原字段。codebase-design沿单一care账本和已存在命令Adapter实现，不另造寿命表；writing-for-agents按来源、接线和验收给出完成条件。原PFS对照的格式差异已收窄到业务attributes/lists，不放宽1000实际值或数据身份。

verify_pet_lifetime_items及pet-lifetime-items-verification.json已通过：原7000显示、之后死亡损失到6950的历史重试保持、鲜命令到7950、删除实例历史读取、care/item/两份receipt真实abort、hook晚期失败、原bag溢出与未知cash全回滚、同失败键随后成功、已知0与溢出边界、HP0保持、禁止热读文件、他人/旧lease/畸形拒绝、实际opaque LeasedAccounts及重开。

verify_inventory_resource_hook加入实际福寿糕鲜False/已付True与根source helper，人物70/40及资源版本0保持。养护、药品、血脉精华、技能到期及当前只读消息回归通过。共享并行批次曾有任务导入与NPC完整人物map缺口，均保留了当时失败记录；后续荷叶羹批次当前源码已复跑verify_inventory_command_runtime、verify_resource_npc_care_runtime(all)、verify_npc_pet_recovery_runtime通过，具体范围见PET_QUALITY_LIFETIME_INTEGRATION。运行时通过仍不替代部署和GUI。

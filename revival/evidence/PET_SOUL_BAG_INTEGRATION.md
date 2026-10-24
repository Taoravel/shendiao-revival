# 元魂背包与独立详情刷新

本批为可选当前消息Adapter，未接共享入口或发布。原参数类型与消息接收补证见 `PET_SOUL_BAG_TIPS_SOURCE_RESEARCH.md`，它更正旧 `PET_SOUL_ITEM_SOURCE_RESEARCH.md` 中107fe20的“背包工厂”归类；旧封签报告的四字段codec、SItemTips和六→四赋值证据仍有效。

## 正确消息顺序

普通Item是固定48字节九项scalar，+0x10是位置，不含元魂四项Octets。107fe20的实际输入是TradeItem，其布局不同；不能向现有普通Item插入四项。原Bag创建容器/key对应对象后，SItemTips通过现存ItemRef虚调用107a020补四项；错容器或错key不会创建/覆盖对象。完整宠物元魂map由独立SendPetSouls负责。

`pet_soul_bag.current_messages(db, inventory, orb_rules, currency_rules)` 在同角色有效租约事务里重读当前背包、钱包和每个原28珠的实例来源，冻结返回 `SGetBagInfo(column1)` 后逐珠 `SItemTips(column1,current_key,16字节四项)`。全部元魂珠必须具有当前完整来源；未知记录整体拒绝，不隐去物品，不补零经验/魂技。其他物品记录调用现有公开Inventory.item_record保持一致。

对于已知珠，基础Item旗标是明确nonbinding_flags与实际binding的按位并，按原uint32 bit pattern编码，保留161和最高位0x80000000等值；它不把高位裁剪成0/1，也不据其授权使用。四项单独经已核原SItemTips发给准确key。其余未命名Item scalar沿用现有恢复编码器输出，本批不把恢复中的0当作历史原值或原服恒零；完整旧原生Item档案仍未验证。

此函数严格只读，不建表、读配置、开连接、提交或发送。资产控制器须先同事务完成元魂与道具/材料/费用/凭据及人物唯一资源来源结算，再调用此Interface编码，任何编码异常回滚全部变更；提交成功后由连接所有者按返回顺序投递。上线前须同时替换登录、重连、背包查询、整理、奖励、交易等所有包含元魂珠的消息生产路径和详情路由，不能只把当前存档接给旧通用Bag。此处只处理携带列1，不授权仓库，也不解释或迁移NPC/内部装备列3/4。

## 方法与验证

TDD 在既有角色事务/原生Item、Bag、SItemTips Seam实际经历缺少Module红灯，再实现。临时真实Inventory、钱包现金123、两颗带独立源的珠和普通药品验证：48字节原Item独立marshal/fresh decoder精确保留flags161/0x80000000及实际key/位置/数量；完整非空Bag原decoder逐项核对内存字段；两条独立tips包含当前四项；普通药品record逐字保持；重复读取在SQL禁止写入下通过；新授予但来源未知的珠明确拒绝。外层SItemTips的原码验证由既有orb4 driver覆盖。

research后台沿原RTTI、TradeItem/GivenItem与基础Item的实际调用参数消解矛盾；原Bag decoder、原copy/位置、原SItemTips decoder、完整原两层map查找及parser消费者已独立执行，命中和两种错目标均有证据。宿主仅隔离等级/配置等文档列出的依赖，不认证完整factory/GUI。

codebase-design复用公开基础Item、当前OrbSource和钱包Interface，在单Adapter隐藏按类型补flags与独立详情顺序。writing-for-agents将读取、资产控制器前置、编码失败、提交与全消费者切换条件并置。code-review对固定清单按Standards/Spec独立复核；本工作区无Git/tracker，不制造提交或issue。

未验证：完整历史Item未命名scalar、所有物品类型旗标/详情升级、真实穿戴/38045摘除/融合材料费用/凭据控制器、完整宠物属性/战斗、全部共享消费者/列适配/加密投递/发布/GUI/容量。来源存档和消息可用均不替代已付动作与现场验收；此前25个生产文件和共享入口保持不变，全量目标active。

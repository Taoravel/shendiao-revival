# 普通装备详情：当前实例、原解析器与接线

鉴定495收费接入前读[EQUIPMENT_IDENTIFICATION_CAS_INTEGRATION](EQUIPMENT_IDENTIFICATION_CAS_INTEGRATION.md)：公开完整来源CAS、事务内当前tips与cash用途已交付；NPC授权/费用及专用receipt继续由NPC模块接线。原parser接受两状态不证明原服隐藏随机属性时机，只读调查保留为历史依据。

2026-10-23，端游1.6.1/网络版本601。普通六槽的干净、未强化恢复实例已实现详情存档与generic SItemTips回复。来源规则为 `design/equipment-detail-v1.json`，实现为 `equipment_detail.py`；高级玩法与原客户端画面尚未验收。

实际穿戴现已补原sexNeed门禁及原武器roleNeed分支，沿同一事务Interface、原字段及启动冻结元数据，见EQUIPMENT_ELIGIBILITY_INTEGRATION。资格通过不代表高级详情或全部最终属性已恢复。

## 接入步骤及完成条件

1. 启动时 `Inventory.prepare` 加载只读DetailRules并准备inventory_equipment_details表。新普通装备发放在原奖励事务内建立耐久和详情；识别、品质1、评分0、原baseEffect及空高级容器是明确designed基线。神兵CGodWeapon集合和其他槽不进入此详情工厂。完成条件：物品、耐久、详情、资产版本及公共奖励回执一起提交或回滚。
2. `Inventory.receive(ITEM_TIPS,body)`解析栏/key，仅允许自有实例实际所在的栏1或4。详情与当前耐久来自同一个读取事务；完整Octets交已有SItemTips0xc03fe，沿原物品类型选择EquipObject解析器。完成条件：完整原解析器消费全部字节，字段和属性map与当前存档一致，错栏/他人/未知类型拒绝。
3. 旧实例缺详情时保持未知。可信、已确认干净未强化的旧实例可在当前角色fenced事务调用 `initialize_equipment_detail(db,key,EquipmentDetail(...))`；要求已有实际耐久、评分/品质推导颜色与条件颜色一致，禁止覆盖已有详情。此Interface不适用于带未知宝石、强化、技能或其他扩展的旧装备。完成条件：显式初始化、版本推进及其他同事务变化一起提交；拒绝和回滚不改变旧状态。
4. 装备/任务/人物属性联动使用下列事务Interface；共享入口由集成窗口维护。完成条件：装备事实、任务进度、人物投影和逻辑回复编码来自同一事务，成功提交后由连接所有者发送。真实GUI另行验收，本批未部署或操作现场角色。

## 公共事务Interface

`equip_transaction(db,key,equipment_slot,epoch,request_id)`已有冻结EquipmentEvent，历史重试replayed=True不产生新事实。

`immutable_snapshot_transaction(db, *, epoch=None)`新增：返回与immutable_snapshot相同的冻结InventorySnapshot，读取当前事务尚未提交的inventory_revision、全部自有物品、条件、详情及未放生宠物/成长/养护。epoch默认使用Inventory从LeasedAccounts接收的可信值；普通AccountStore调用方应显式提供。要求活动事务、角色归属及当前有效租约；过期或已停用租约拒绝。它不新开连接、不提交、不写库、不编码或发送。读取到的是当前事实，不是历史回执投影；外层回滚后不应发布已丢弃的快照。

`equipment_bag_messages(db,epoch)`已有：在同一事务返回当前栏1/4逻辑消息，携带栏含实际cash。无钱包或编码失败应使装备/任务/属性事务全部回滚。

`ItemState.detail`新增冻结EquipmentDetail(identified,prefix_quality,score,base_properties)；缺失为None。现equipment_attributes对已知详情采用实例的原修饰ID/值；旧未知详情保留原template兼容值，不能因此宣称可用于完整人物投影。prefix品质、食品quality、binding、颜色、评分各自独立。

根窗口的role_equipment窄政策只支持未改造49001..49010/slot0。**显式初始化的详情可能含不同于原模板的已知属性、品质或评分；集成方必须按该窄政策核对/拒绝，不能因为template在集合内就无视实例详情而重新套原模板25/15/8。** 尚未恢复的高级修饰不应由任何未知值默认成零。此处未修改根窗口的人物投影Module。

## 原生证据与设计范围

`research_equipment_detail_full.py`实际执行原EquipObject构造107cf80、解析107d960并自然返回107fd97；使用原树容器、插入/清理、流读取、颜色计算及两个固定扩展bean解码。宿主Adapter只提供配置查找、分配/释放、引用计数、空UTF16赋值、memcpy和cookie；配置采用原目录的颜色阈值、品质cap、itemtype以及完整CGodWeapon ID集合。零强化分支虽查询CEquipMakeUpConfig，但不会读其内容；未执行非零强化/神兵分支。

| 顺序 | 原布局 | 当前确认/处理 |
|---|---|---|
| 1 | 7×BE32 | 鉴定、未知、当前耐久、上限、特殊级、未知、未知；干净基线未知值0 |
| 2 | UTF16 Octets | 空文本；不擅自命名为制作者 |
| 3 | 3×BE32 | prefix品质、评分、输入颜色；普通装备颜色由原阈值/cap重算 |
| 4 | BE32数量+若干(i32,i32) | 原对象+80属性map；当前设计填原baseEffect修饰ID和值 |
| 5 | BE32数量+若干三元组 | 原对象+8c容器；干净基线为空，非空业务未接 |
| 6 | BE32数量+若干i32 | 原对象+98列表；干净基线为空，非空宝石玩法待接 |
| 7 | 3×BE32 | 原+b0、+104、+100；干净基线0 |
| 8 | UTF16 Octets | 原+108文本，空 |
| 9 | 4×BE32 | 原+144内嵌bean的原d991e0；干净基线0 |
| 10 | 2×BE32 | 原+124、+d4逻辑标志来源；干净基线0 |
| 11 | 6×BE32 | 原+158内嵌bean的原d995f0；干净基线0 |
| 12 | 2×u8 | 原+194、+195启用标志；干净基线关闭 |

普通基线总长116+8×属性数。原parser存在部分历史可选EOF分支，但两个末标志必须完整；不借EOF省略中段而误将标志解释成其他字段。原SEquiptips0xc0419是另一种消息/bean，本实现没有混用。

上述布局与字段读取为client_verified；将原baseEffect放入首属性map、评分0/已鉴定/普通品质、空高级状态的工厂规则为designed。原强化分支会以首map值进行修饰计算，尚不能称原服所有属性生成算法已恢复。[2013-08-30官方端游装备解析](https://sdxl.games.wanmei.com/news/gamenews/20130830/149369.shtml)仅作六部位、六色、评分与颜色及基础/附加属性区分的guide_supported旁证，没有给出本地工厂初始公式，未用手游或其他游戏数值。

## 本批方法、产物与验证

codebase-design把配置、详情存档、当前耐久和协议表示集中在装备Module，跨模块只传冻结值；调用方事务Seam复用现有资产所有权。diagnosing-bugs采用原构造器+原完整消费者差分，并以原parser拒绝缺末标志、完整消费拒绝额外字节和真实SQLite保存abort作为可重复失败信号。writing-for-agents把步骤、字段来源和窄范围限制集中于本文，INVENTORY_INTEGRATION仅保留接入摘要。

产物：equipment_detail.py、equipment-detail-v1.json、完整原解析器研究及结构化证据、verify_equipment_details.py、verify_inventory_snapshot_transaction.py，以及Inventory局部接线。

验证通过：完整generic消息codec与EquipObject读取；六槽模板详情；原map第二次解析替换旧值；绑定/食品quality不成为prefix/评分；穿脱后的实际栏校验；磨损后的当前耐久；重开存档；缺旧详情保持未知；显式初始化及颜色冲突/他人/重置拒绝；真实详情保存失败回滚物品、条件、版本和奖励凭据；同事务快照含成长/养护/详情且无嵌套连接；实际旧/停用租约拒绝。

回归通过：inventory、inventory_transactions、equipment_events、equipment_wire、equipment_condition、equipment_color_reconciliation、inventory_cash、item_tips、inventory_arrange。新详情工厂覆盖1038个符合当前范围的原模板；这是工厂配置范围，不是1038种玩法验收。共享运行服、GUI完整提示/绑定、type59自然流程、NPC修理、神兵/强化/镶嵌/附加属性、商业容量仍未验证或未实现。

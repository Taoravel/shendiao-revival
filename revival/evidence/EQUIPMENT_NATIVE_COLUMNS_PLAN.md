# 自身装备原生列与内部归属：最小适配方案及RED

2026-10-24，所属资产窗口只读核对并建立临时实际反馈环。内部存档、封签Inventory、共享入口和当前服务保持不变。原客户端本人装备列3、商店回购列4的新直接来源以 `NPC_REPAIR_COLUMN_RESEARCH.md` / `npc-repair-column-native.json` / 父独立27组合重放为准；旧“4就是本人已穿”的解释不能继续作为授权依据。单字节宝石source1不是原容器号4。

## 已复现的准确症状

命令：指定项目Python运行 `staging/verify_equipment_native_column_red.py`。脚本位于staging，**预期exit1**，不混入当前顶层绿灯验证。临时AccountStore/真实Inventory公开穿戴49001至slot0，当前钱包和租约明确。原query `(column3,target0)` 抛 `Unconfirmed inventory column`，旧 `(column4,target0)` 返回column4。原角色实际装备slot0仍存在，故不是装备丢失。公开 `equipment_bag_messages`、`equipment_refresh`、`equipment_tip_message` 的当前已穿投影也分别返回4；说明只改入参还不足。完整实测值见 `equipment-native-column-red.json`。

diagnosing-bugs先建立数秒、确定、无人参与的真实公开Interface反馈环并两次复现；原NPC27组合是输入症状已有的独立第一方反馈，随后才在本窗口复现服务器。按顺序核对三种可证伪假说：H1请求分流拒绝3（预测3会报未恢复但4同角色同资产可读）；H2出参仍使用内部4（预测绕开query的公开消息生产者也发4）；H3旧4被误当本人装备（预测原本人UI用3而原服务2回购用4+NPCkey）。本环和公开只读生产者证实H1/H2，NPC原码27组合支持H3。未加临时生产日志，无全服锁、进程或真人操作。修复和最终原UI回归仍待集成，RED未宣称绿。

## 提供给main/NPC的具体最小片

1. 保持 Inventory/equipment_slot、当前不可变快照、来源/CAS和资源上限Seam的现有内部归属。当前内部装备视图4不迁库、不重编号。shared由main单写；鉴定最小封签3文件不整份重并。
2. 新建所属协议Adapter（建议 `equipment_native_columns.py`）显式区分“本人原wire列1/3”和“内部自有视图1/4”。Interface按用途提供自身query/tips/endure解码与当前自有装备消息，拒绝NPC列4，不做通用4↔3字节替换。它须从当前owned Inventory读取后编码，不能接受任意NPC帧并改首字段。
3. main在真实本人query3+target0/本人role范围经当前角色/地图成员许可后进入该Adapter；调用当前内部已穿读取或公开自有快照，产原Bag column3。query4+NPCkey保持NPC回购服务/距离/当前菜单授权路由，由NPC维护，不映成本人装备。query4+0的历史读取兼容由root另行裁定，不由本片默认扩大为新请求许可。
4. 同一自有物品的当前详情、耐久、最大耐久在wire分别使用3（背包仍1）；根内部判定继续用当前ItemState.equipment_slot，原评分/耐久/基础来源及唯一HP/MP存档不改。返回消息须先编码、后提交、再由连接所有者投递。
5. 普通宝石source0/1只表示原发送分支的携带/非携带来源。本人的已穿分支须用原CEquipDialog列3及实际当前已穿实例闭合后才接入；现有 `SocketRequest.source_column=4` 至多作为**内部已穿归属标记**，不能再称原wire4或授权NPC/仓库。新增Adapter给wire3、内部4及source1各自命名和测试，保持所属存档CAS不变。原修理fresh只允许1/3，历史已付4只current-only兼容及防重复收费由NPC/root单独裁定，资产不代写该逻辑。
6. 必须覆盖登录/重连、CEquipDialog查询、公开穿脱/任务穿戴、修理/损坏、tips、耐久查询与宝石详情/操作的实际角色调用链；不能只让刻意构造的4请求过测试。原NPC3/4命名空间不能据一张表全局alias。

最小验收：上述RED通过新Adapter变绿，旧内部slot/source/HPMP逐字保持；真实原本人EquipDialog列3取得已穿ItemRef，原修理列表3及其确认wire3贯通；服务2的NPC回购列4不会读取或改本人装备；旧paid4不再扣材料/费用；未知列、错误NPCkey、错角色/epoch和待结算来源拒绝。原客户端点击、共享发布、历史兼容政策尚未实现/验收，本方案不是迁移完成声明。

2026-10-24 后续原生16链/父独立来源纠正：列4仅描述商店**回购**；普通购买由客户端本地 NpcSellItem 模板→CItemAttr→CBuy(template)，回购为 CRepurchase(instanceKey)，不创建 stock4 实例。以 `NPC_SHOP_CATALOG_NATIVE_RESEARCH.md` / `npc-shop-catalog-independent.json` 为准。c0434为原ItemBag+price map；具体价格显示另研，不凭数值直觉改政策。本人wire3、内部持久4保留及shared单写原则不变。

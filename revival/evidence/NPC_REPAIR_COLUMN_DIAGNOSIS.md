# 普通修理栏目：发布版对照与原窗口来源调查

2026-10-24。本批使用diagnosing-bugs建立单变量反馈，再用research核原请求来源；复用已经采用的真实Peer、角色/资产公开Interface和原codec Seam，未改生产源码、共享入口、政策、运行服务或真人数据。此页为定位记录，不是发布或GUI验收。

## 可重复反馈

`staging/diagnose_npc_repair_column_runtime.py --expect-missing`在准确`npc-repair-20261024T023920Z`导入生产源码和冻结harness，每次前后核1442生产/422助手/1208配置输入。复用原已穿修理fixture的自然认证、实际穿戴、正常服务513、同事务属性及重连检查。两个新临时库只改变测试调用方最终CRepairEquipItem的column字段：4原样通过，现金1000→960、耐久提交及重连保持；3收到空回复，公开Inventory snapshot和钱包前后完全相同。没有替换生产dispatcher、投影、随机算法或编码器。

同一角色另经原CGetBagInfo公开输入对照：column3/target0为空，column4/target0返回当前已穿装备，column4/target真实NPCkey为空。这里只记录发布版行为；没有凭这些服务端结果给原客户端枚举重新命名。精确请求、公开前后状态和导入路径见`npc-repair-column-runtime-baseline.json`。`--expect-missing`的成功表示发现缺口；脚本默认会以该缺口失败，不能当修理功能通过。

最初探针读取了不存在的RoleOwner.role_id，已改用测试Peer保存的真实role ID；这是观察器设置错误，发生在实际修理请求前，不计游戏故障。

## 待反证的假说与检验

1. 请求栏目枚举与服务器解释不一致。如果成立，原修理真实点击应产生3，而当前decode在同一资产输入上拒绝；已有点击尾段与发布Peer对照支持这一边界，但完整原物品来源仍须另证。
2. 新追到的3只属于某类特殊装备或不同窗口。如果成立，普通513应能找到另一条真正已穿栏目4点击链；不能因两个尾段就假定所有窗口只有1/3。共同开窗及类型筛选的112例已有明确范围，完整构造未验证。
3. 更上游把商店栏目4误当自身装备。如果成立，原service2应打开该column4 sender所属窗口，而自身装备消费及修理列表应使用3。本批27组原生组合现已由主窗口独立原样复跑：支持本假说；真实bag3来源保留到原ItemRef、选择、点击和repair3，4两列表不选；另service2→CNpcSellItemDlg原字段复制→query4/NPCkey、CEquipDialog槽事件3均闭合。原map安装/浅copy、CEGUI与配置依赖边界保留，完整证据见`NPC_REPAIR_COLUMN_RESEARCH.md`和`npc-repair-column-independent.json`。

以上排序在变更实现前向用户说明；每次探针只改变明确输入，不先把3映射成4。状态所有权按ARCHITECTURE保持：NPC只维护所属修理授权/领域，资产栏目归资产窗口，真实路由和部署由main统一；root已收到潜在跨模块影响。首场100107正式PVE仍优先，本调查不夹入其候选。

## 接续条件与未验证

原生链的独立复跑条件已完成：27组合、四原产物SHA完全一致、旧证据/生产/两ready保持，见上述独立报告。下一步由资产Module集中定义自身装备/商店栏目Interface，NPC采用该含义维护修理与商店授权，main统一接真实路由。修正须沿本页同一Peer反例转绿，并保留错误NPC/资产归属拒绝、历史已付凭据兼容和同事务费用/编码失败回滚；固定版本双轴及发布验收后才关闭接线问题。

NPC所属最小准备已完成：staging候选E648与真实旧Owner付款记录做跨进程/新租约重放，原生3收费/完整属性/重连、fresh4拒绝、已付当前恢复及物品变化冲突均通过；携带事务/回滚与known-resource原生3也通过。固定两轴各0及准确范围见`NPC_REPAIR_COLUMN_CANDIDATE.md`与ready9e297b；尚未接Asset消息Interface或共享路由，工作区/运行模块仍3cc。

商店来源的后续16链已独立原样复跑：query4明确属于tab11“回购”，普通购买货架为本地NpcSellItem→CItemAttr模板；见`NPC_SHOP_CATALOG_NATIVE_RESEARCH.md`和`npc-shop-catalog-independent.json`。原服对query4实际选择通用SBag4还是专用c0434尚未知；后者已验证为包含真实卖出实例和price map的完整回购载体。当前4查询缺失只能定位回购入口，不能据此说普通货架缺失或伪造stock实例。默认回购显示还会用map值×数量×1.1，随后有配置覆盖；实际恢复端整叠price口径已采真实SALE/REPURCHASE帧另研，最终金额未闭合前保持当前policy。

当前普通修理保持正式已验代码，特殊855仍按独立政策和资产资格恢复。旧column4服务器Fixture只证明当时输入下的服务器行为，完整原UI语义另按来源链判断。codebase-design将栏目解释集中在所属Module的Interface，避免调用方各自转换原始数字；writing-for-agents把阶段、所需证据和关闭条件放在同一接续入口。

尚未验证：完整原GUI点击、实际商店货架回复、资产栏目纠正及全部消费者兼容、修正候选双轴、部署与真人装备/修理显示。本批已经形成可红的真实Peer反馈，没有把发现缺口写成功能完成。

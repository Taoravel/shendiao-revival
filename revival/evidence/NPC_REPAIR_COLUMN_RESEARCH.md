# 修理栏目：本人装备3与原NPC商店4的原生证据

2026-10-24，原端游1.6.1/网络601。使用 research 方法从第一方原映像和PFS核对，新增独立脚本、JSON、反汇编及本文。只读生产/历史研究/两个ready，未改共享、政策、真实库、服务或客户端；没有运行战斗。

## 直接影响接线的结论

**不能将原column3请求简单映射成现有column4。** 原装备修理界面精确枚举管理器的容器1和3；实际来自SGetBagInfo column3的物品，经原复制、原容器查找和原点击，发送CRepairEquipItem的column3。相同输入改为column4时，两个修理列表都不选入，没有4→3转换。当前恢复服务若只向4投影本人已穿物品，虽然人工column4请求可以在服务器通过，仍不能据此证明原修理界面能取得它。[N1–N3]

原column4的已查字面量请求属于 **CNpcSellItemDlg**，由原服务2打开，目标64位值来自NPC菜单key。它不是本次证明的本人装备查询：原请求为CGetBagInfo `column4 + NPC key`。先前宝石调查“column4→source1”的数值执行仍成立，但那条发送判断是`column!=1`，不能由其反推“4就是本人已穿”；该分类解释应由资产/集成方依据本证据修订，不能继续作为扩大服务器授权的依据。[N4]

本人装备方向另有原CEquipDialog的已注册槽位事件：回调10cf2d0从十二个槽控件找出槽序号，真实向ItemManager的10aa3d0传`cell, column3, slot`。本批完整运行回调入口至该调用，槽0和5均得到3及各自原序号；未运行后续移物网络/服务器结算。原10977b0的物品安装后路径也仅在column3进入1098070分支，并分发相应物品UI更新。这些路径与NPC商店的4分别存在。[N5]

## 新执行范围：27条组合检查

单一原模板49009“师承的油纸伞”，原itemtypeid为2312，其低4位8、分类位0，属于原直接普通分支。citemattr全表按PFS长度/CRC读取、BXML解码，全部attributes/lists与缓存逐行一致；没有根据名字手造装备类型。另直接重读ui.pfs的`layouts/equipmentrepairsmiple.layout`和`layouts/npcsalemore.layout`，核长度/CRC并XML解析。前者真实文案区分“包裹中的装备”和“装备栏中的装备”。原条目散列和文案保存在JSON的sources。

组合为column `{1,3,4}` × position `{0,5}` × binding `{0,1}`，共12份原SGetBagInfo完整解码；每份分别走两个原修理列表，共 **24条容器→修理组合**。选择成功的8条继续运行原点击入口、原确认发送及原marshal。另有一条service2→原开窗参数→原字段复制→原column4请求，以及两条装备槽事件，合计 **27条新组合检查**。12次decoder、8次点击属于24条内部步骤，不能再相加冒充更多独立组合；旧112/96/656未重跑。

| 原消息column | 原Object+4c | 原列表1 | 原列表3 | 选中后真实修理wire column |
|---:|---:|---|---|---:|
| 1 | 1 | 选入 | 不选入 | 1 |
| 3 | 3 | 不选入 | 选入 | 3 |
| 4 | 4 | 不选入 | 不选入 | 无修理请求 |

每种position/binding组合结果一致。position5只是受控来源保持检查，不单独证明所有装备槽及完整穿戴资格。

### N1：原消息与来源字段

原SGetBagInfo constructor ef6220 / marshal ef62d0 / decoder ef6350完整执行并消费整包，观察真实解码Item vector。原process片段10a9054..10a9067直接从消息+8取column，调用10a4840时仍是1/3/4原值，未换号。原10a4840中的10a4957..10a4979静态链将同一column分别交10a1c10外层容器和10977b0物品安装。

实际执行原CItemAttr id/type整数复制1080720→1072890，到wstring复制前停止；原Item bean复制81a760执行；原10817bc..10817cc真实将来源column写Object+4c、position写Object+48。实例key701来自原消息bean复制，不另写最终key/column。完整wrapper后续初始化未执行。

### N2：两个容器保持独立

原109c810从管理器+a4查key3，109ca00查key1；两者原完整108dca0查找实际运行，不替换查找返回值。每次内存中只构造一份按真实解码column命名的外层map与一个该来源ItemRef，column4测试中没有另造3别名。

原类型谓词和append之前的选择执行。适配了空输出vector清理，以及已经按原查找取得的单项内层map复制；该复制只提供原节点布局，不选择其他容器或替换类型谓词。未运行完整STL插入、复制析构和排序生命周期。真实选中返回同一ItemRef；未选中停在空列表终点。

### N3：真实点击到修理包

原回调从入口10ddb30（列表1）和10ddcb0（列表3）开始。选中CEGUI cell携带N2输出的同一ItemRef；原10733f0及原getter89d6a0执行，但其ConfigManager+570 lookup明确适配为missing，不能当真实物品资格证明。tooltip/highlight/icon等UI依赖适配，原代码实际把该ItemRef写入确认控件+278。

然后跳过名称/label字符串绘制，运行各自原column赋值尾段10ddc78/10dddf8，保存1/3。原10dda40确认回调真实构造c0413、从同一已选ItemRef取原key701，提交捕获后执行原e4cf30 marshal，线体为`BE32 method2 + BE64 NPC key + BE32 column + BE32 key701`。没有直接填写最终column或以Python代替原发送分支。NPC key使用高32位非零的受控值，完整保留；网络仅内存捕获。

### N4：服务2、商店类与column4请求

原1636d38是服务2分支：读取NPC菜单+d0/d4完整key与+d8，调用10ecaf0，再调用110a690。本批实际运行该分支并捕获原参数。工厂10ecaf0静态加载/建立global294acdc，经1108280构造；原1108320写实际vtable2290118，RTTI为`.?AVCNpcSellItemDlg@@`，singleton vtable228ffe8的RTTI也明确同类。不是仅因地址邻近猜名字。原服务2到工厂/开窗的联系为原指令直接调用。

为避开完整CEGUI，实际捕获的开窗参数放入原callee frame对应槽位，执行原110b9bf..110b9e6，将NPC key存入同一UI+e8/ec。再执行原1103df3..1103e3b：它真实构造c03f2、固定column4、读取刚才的+e8/ec并提交。原e4c430 marshal得到`000000041234567800000042`，即4及完整受控NPC key。没有人工写最终UI key字段/请求column。

捕获参数→原callee frame是明确的离线桥，未声称完整运行开窗过程中所有UI、模式或计时事件，也未证明每种商店都走这段分支。此证据足以否定把该column4字面量本身作为“本人已穿”的来源；不授权任意NPC key通过查询，更不恢复货架结算。

### N5：装备槽3

原CEquipDialog constructor10ce6e0写vtable228dce0，该类RTTI明确；其设置代码10d3289把10cf2d0装入槽事件。回调在10cf345..10cf356检查十二个槽控件，10cf6d4..10cf6e0把实际匹配的槽号和字面量3传给10aa3d0。两个新native例从完整回调入口开始，实际匹配槽0和5；只把事件/cell、Ctrl未按和当前拖动UI状态作为依赖，停止在真实ItemManager调用。未将其描述为已执行移物或服务器穿脱。

## 方法、边界与复跑

在项目根运行指定Python `-X utf8 -B revival/research_npc_repair_columns.py`。脚本会核历史12文件、NPC修理/Scene/Lifecycle、Inventory/condition、两个ready及native helper前后SHA，不同则拒绝输出。四份新产物分别为本报告、脚本、`npc-repair-column-native.json`、`npc-repair-column-disassembly.txt`。

research用于同时检验两种假说：不能仅将缺少column3视为NPC局部decoder问题，也不能仅凭现有服务器4纵切推原UI语义。结果支持进一步修订资产容器投影与NPC修理入参，同时保留原1/3/4命名空间差别。应由所属Asset与main单写者制定精确接线/版本兼容；本批不改旧存档或将4全部重解释为3，不扩大特殊855权限。

未验证：完整UI/原map安装与STL生命周期、真实玩家装备资格、所有其他容器、原服历史授权/结算、已保存4回执的兼容政策、共享路由和GUI。修理费用、概率、root人物资源、NPC证明/距离/租约/版本仍须原有权威校验，不能因栏目匹配而放宽。

所有地址来自`evidence/native-image.bin`，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。方法与状态如上记录；服务端实现/部署/真人画面均未由本批完成。

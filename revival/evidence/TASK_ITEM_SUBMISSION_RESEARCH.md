# MissionType12 交物任务原生研究

日期：2026-10-23。范围：本项目原端游1.6.1/网络版本601的 `native-image.bin` 与 `artres/config.pfs`。没有启动或控制客户端，没有运行在线服或战斗，没有修改任务、Inventory、生产codec或共享入口。

## 方法、产物与强度

本批重读 `D:/User/Documents/Codex/.codex/skills/research/SKILL.md`，沿原始来源追溯协议、字段和UI调用；本子任务已是主任务委派的独立研究，不再递归委派。沿用已在上下文的 codebase-design：把协议布局、交物资格和角色事务消费分别记录，避免把客户端选择器当作资产事务授权。已重读 `../ARCHITECTURE.md`、`../DESIGN_AUTHORITY.md`，消费与奖励应由角色所有者在同一事务内处理。

产物仅本报告，以及可复现的隔离原代码布局探针 `../research_task_item_submission.py`。本报告中的 `client_verified` 指原配置/原代码可直接观察；`inferred` 指由UI用途推定的领域含义；未确认项单独列出。没有把客户端代码外推为已恢复原服消费算法。

## 关键结果

1. **MissionType12 的物品交付上行是 CSubmit2Npc `0xc2340`**，携带具体物品实例 key 和数量；不能把普通 CCommitScenarioQuest 当成无物品参数的完成授权。CCommit仍用于此前的接取、菜单状态流程。
2. 原任务交物UI使用 submitType **1**；普通给予/交易型 submitType0 的绑定拒绝不能复用于该路径。绑定物品不因“绑定”这一项就被此任务UI一律拒绝。
3. `ActiveInfoTargetID` 明确用于原模板ID筛选。`ActiveInfoTargetNum` 存在且大多数为正，但本轮没有取得其至原服扣除/精确数量校验的代码；原UI可以选择单个或全堆数量，不能信任客户端自行恰好选到任务需求。
4. 原表236条type12中，232条 targetID>0且targetNum>0；其余4条不能当成普通静态单目标交物启用。
5. 已接state2在NPC菜单走进行中提示；state3才走本地对白→专用交物UI。独立下行 SSubmit2Npc `0xc233f` 可以直接打开原提交UI，其空targetIDs路径按本地原任务配置构建候选列表，不经过上述state3菜单分类。

## 原配置逐字段

本轮直接使用 `PfsArchive('artres/config.pfs').read(...)`，读取时检查PFS本地/中央记录、解压长度和CRC；随后用既有BXML解码器解析。目标条目 `autoconfig/knight.gsp.task.cmainmissioninfo.xml` 解压内容 SHA256：

`ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706`

筛选条件是原 `MissionType==12`，共236条。

| 原字段 | 原读取证据 | 观察与限制 |
|---|---|---|
| ActiveInfoTargetID | UTF16名 `0x226c308`；parser `0xbb5fa5..0xbb5fd1` 存配置 `+0x180` | 提交UI `0x168a689..0x168a6a5` 查已接任务原配置，在submitType1将 `+0x180` 放入候选模板列表 |
| ActiveInfoTargetNum | UTF16名 `0x226c2e0`；parser `0xbb5fe4..0xbb6010` 存配置 `+0x184` | 数量字段身份、整数值直接确认；精确消费算法未取得 |
| ActiveInfoOtherType | 236条均0 | 不凭该0推导品质/绑定额外规则 |
| ActiveInfoGiveBackMoney | 236条均0 | 本轮不从此字段推导费用 |
| ActiveInfoUseItemID | 236条均0 | 不是该交物路径提交的实例key |

TargetNum分布：1×200条、5×13条、3×9条、10×6条、0×4条、2×3条、99×1条。存在不同明确需求量，不能把type12统一扣1。

典型原任务101101：ActiveInfoNpcID10527、MapID1006、TargetID50062、TargetNum1；原任务文字要求将机关鸟零件交给门派传送人。原 `autoconfig/knight.gsp.item.citemattr.xml` 的50062名称“机关鸟的零件”、type41、maxNum1、outbattleuse0、`bCanSale=0`、`bCanSaleToNpc=0`、givetype0，并写作主线任务物品。这支持 **交任务与允许交易/卖店不同**，不能因为普通转移权限为假就拒绝所有任务交物。

其他目标原物品例：50067“师父的密信”；50327“山羊的笼子”；38436“变身糖果”的usemethod明确提示交给千幻使者完成任务；64557“万圣节糖果”说明5个可兑换礼包，maxNum99。已对这些条目直接重读原config.pfs，不仅引用已有目录JSON。

### 四条不可按普通静态数量处理

| 任务ID | 原名 | TargetID | TargetNum | 原任务目的 |
|---|---|---:|---:|---|
| 221112 | 二次蜕变·侠义之心 | 0 | 0 | 将阵法元素交予郭靖 |
| 221117 | 二次蜕变 | 0 | 0 | 将三种凭证交予司徒南 |
| 232003 | 锦书谁寄 | 33040 | 0 | 将小还丹交给郭靖 |
| 812001 | 玉牌的证明 | 0 | 0 | 收集各色玉牌交给云中翳 |

这些记录提示动态/多物品/特殊规则，但本轮未恢复完整规则；不能把0数量视为免费完成、也不能默认改成1。其中221112/221117的UI特判在 `0x168a608..0x168a684` 可见：前者从任务bean.value1查另一张配置的候选列表，后者硬编码加入模板50261/50262/50263（`0xc455/0xc456/0xc457`）。这只确认其不是普通单静态目标，不能据候选列表推测三种凭证各扣多少。

## CSubmit2Npc 原布局及来源

RTTI `.?AVCSubmit2Npc@npc@gsp@knight@@`，虚表 `0x2284a94`。构造 `0xf15850` 在 `0xf15884` 写 type `0xc2340`。marshal `0xf16270`、unmarshal `0xf16320`。

| body顺序 | 类型 | 原对象偏移 | 含义证据 |
|---|---|---|---|
| 1 | BE i32 | +8 | 本链的questID；UI保存于+0x60，发送 `0x1684757..0x1684760` |
| 2 | BE u64 | +0x10/+0x14 | NPC实体key；UI保存于+0x58/+0x5c |
| 3 | BE i32 | +0x18 | submitType，本type12路径为1 |
| 4 | compact_uint | vector+0x1c | SubmitUnit元素数量 |
| 5 | count×(BE i32, BE i32) | 每个SubmitUnit+4/+8 | 具体物品实例key、选定数量 |

外层没有额外bag字段、任务进度字段或quality/binding字段。未确认的其他submitType不能按1处理。

SubmitUnit RTTI `.?AVSubmitUnit@npc@gsp@knight@@`，虚表 `0x2284ab8`；marshal `0xf16160`、decode `0xf15b80`；两个成员都是固定BE i32。CSubmit vector factory `0xf15d90` 写虚表 `0x2284acc`，其marshal `0xf16440`，decode `0xf85530`。

原客户端scalar/container constraint `0xf161f0` 只要求外层第1字段≥0、NPCkey≥0、submitType≥0，逐个SubmitUnit要求key>0且quantity>0。原函数允许空vector；服务端不能因此接受空清单完成任务。UI通常最多5个选择格（`0x1684887..0x16848a3` 以步长0x138循环至0x618），协议编码器本身未显示该5项上限是wire硬约束。

### 从UI选择到实例key/数量

类型分派 `0x1643679` 比较MissionType12，压入submitType1，`0x16436ad..0x16436bf` 将questID和NPCkey交专用提交UI `0x168a1e0`。此函数分别保存NPCkey、questID、submitType于UI `+0x58/+0x5c`、`+0x60`、`+0x64`。

拖入/点击物品的原选择函数在 `0x1683512` 从实际物品内部 `+0x14` 取得实例key，经 `0x168351d` 找现有/空选择格，在 `0x168353a` 保存key；随后从物品内部 `+0x28` 取得当前堆叠数量。选择格前两个dword就是key/count。

确认按钮 `0x1684710` 在 `0x1684757..0x1684779` 写外层quest/NPC/type。`0x168483d..0x1684882` 把选择格前两个dword复制到SubmitUnit并push进vector，`0x16848a9..0x16848ba` 调连接发送。故SubmitUnit第一字段是**实例key，不是模板ID或背包槽位**；第二字段是选定数量，不是quality或任务状态。

选择行为 `0x1683552..0x16835aa` 有两个直接分支：来源事件字段`+0x1c==1`时选当前全堆，==0时选中量加1；最大值与原堆叠数量比较。该代码未使用原TargetNum。由此只能证明UI可能发出1..当前堆叠量的正数，不能认为它一定等于原任务需求。原服是否容忍超额、按需求只扣部分、限制合并多堆或逐次交付，本轮未知。

## SSubmit2Npc 原下行：可直接打开专用UI

RTTI `.?AVSSubmit2Npc@npc@gsp@knight@@`，虚表 `0x22818f8`；构造 `0xe6fd00` 写type **`0xc233f`**，marshal `0xe6fe10`、unmarshal `0xe6fec0`，Process `0x168bed0`。

body：BE i32 questID + BE u64 npcKey + BE i32 submitType + compact count + count×BE i32 targetIDs + BE i32 tail。

构造 `0xe6fd47` 显式将tail对象 `+0x2c` 置0。Process检查targetIDs vector：

- 空列表：`0x168bef9..0x168bf09` 仅读取questID、NPCkey、submitType，调 `0x168a1e0`，**不读取tail**。该路径用原默认tail0是有原代码支持的；不是猜字段含义。
- 非空列表：`0x168bf13..0x168bf28` 将tail和列表一起传 `0x1685430`；本轮未确认tail业务含义，保持opaque，不套用上述默认结论去推断非空路径。

因此普通静态type12可以研究使用submitType1、空targetIDs、tail0按原配置打开UI。UI又会检查已接任务与实际NPC；收到此消息不等于服务器已经批准扣物或完成。原客户端实机能否完整显示仍待后续集成验收。

## 选择限制：已确认与未确认

### 模板、背包和装备

普通已接ScenarioQuest路径 `0x168a5f0` 查已接bean；`0x168a689..0x168a6a5` 按questID取配置并只把ActiveInfoTargetID放候选模板列表。候选高亮 `0x1681f00` 经背包管理器 `0x1091600(1)` 分页遍历实际背包UI槽，比较实际物品模板ID与该列表。原物品的模板ID在选择路径取自内部 `+0xc`，与提交实例key `+0x14`分开。

本轮可确认其从背包格选实际拥有实例；没有看到从装备栏直接交付的同一路径。服务端核对owner、当前未装备、数量、版本等是合理的资产安全条件，但不能据本轮UI遍历将其全部标为原服实现已核验。

### 绑定与原状态flags

候选筛选 `0x1682047 / 0x1682192` 和点击校验 `0x1683476` 调 `0x1072e80`。该小函数只判断实际物品内部flags `+0x10` 的 `0xa0` 掩码（0x20或0x80），命中则拒绝。精确两bit的命名本轮未确认，不能用它代替binding布尔。

绑定检测函数 `0x1072e70` 读同flags并 `and 1`。选择代码 `0x16834de..0x16834f9` **仅在submitType==0**（普通给予）执行该绑定拒绝；submitType1直接跳过。因此对type12一律拒绝binding=1没有原UI依据。普通任务物品本身也经常不可交易/不可卖店。

选择代码还有 `0x1072ee0` 检查两个内部dword `+0x40/+0x44` 是否均为-1，命中时再走 `0x1682f30` 对照检查；本轮未确认这两个成员的业务名。不可把它直接称为品质阈值或默认忽略后声称完全还原原物品资格。

### 品质与其他限制

普通候选模板过滤路径没有观察到直接quality数值比较；这只表示本轮读取范围未见，不证明原服无品质要求。type12配置attributes中没有独立bind/quality/equipment_slot字段，仍可能有物品类别细则、实例额外状态或特殊任务ID规则。

不能把人物/宠物交互、通用交易、NPC卖店的限制跨场景搬进任务交物；也不能因为缺少显式列就清空实例绑定或品质元数据。原确认上行只携key/count，相关元数据必须由服务器从该角色真实实例读取，不能由请求方填写。

## ScenarioQuest value/state：不要用数量猜ready

既有原证据：SAcceptScenarioQuest内bean `+4`任务ID、`+8`state、`+0xc/+0x10` value1/value2、`+0x18` NPCkey。SRefreshScenarioQuestValue `0xc4a49` 的Process `0x1258c90` 直接覆盖value1/value2，非index/value增量。

普通type12的候选模板取自配置TargetID；本轮没有证明value1=已拥有数或value2=需求数。特殊任务221112在 `0x168a615..0x168a637` 用 **value1作为另一张配置的查询key**，已经足以否定“对所有type12把value1当count”的通用假设。普通type12的两个value与追踪文字数字的精确对应仍未确认。

UI状态查询 `0x1257b20`：ScenarioQuest类型12不属于type40例外，只有bean.state==3返回可交付分类3，其余已接state2等返回进行中分类2。NPC点击 `0x1636b08` → `0x164d780`：分类2在 `0x164b405..0x164b4b3` 针对type12显示本地任务物品的进行中提示；分类3执行本地对白后进 `0x1643360`，继而type12打开专用提交UI。

因此本地NPC菜单路径需要state3才能进入可交付对白/选择UI；“拥有够物”并不会在该UI分类函数自动修改state。也可由上面已确认的SSubmit2Npc空目标列表路径直接打开选择器，但服务端仍必须检查任务已接、可信NPC/位置ticket、指定实例及数量。

对重登的限定结论：普通静态type12可先按SAccept state2/value1=0/value2=0恢复“已接进行中”，在服务器核对真实库存满足后另发state3与菜单。上述普通选择器构建路径从原TargetID和实际bag取候选，不依赖这两个bean计数，因此无需为打开它伪造数量。此结论不覆盖四条特殊任务，也不证明任务追踪栏全部数字都忽略这两个value；完整显示映射仍未确认。

state1是既有完成/移除路径；在扣物与任务/奖励同事务成功前，不能因为客户端发了CSubmit就先广播state1或删除服务端任务。

## 小型原生布局探针

`../research_task_item_submission.py` 直接执行原CSubmit2Npc::marshal `0xf16270`，原vector marshal `0xf16440` 和原SubmitUnit marshal `0xf16160` 均实际访问。只适配CRT memcpy与进程cookie检查，不替换协议writer或容器序列化。

输入：quest101101，NPCkey `0x1122334455667788`，submitType1，一项key12345/count3。输出25字节：

`00018aed112233445566778800000001010000303900000003`

与手工预期逐字节一致，原函数正常返回。此探针只证明布局、字段顺序和单位宽度；count3不是任务101101合法需求的断言。没有运行选择UI、库存、任务状态机、原服消费、战斗或在线客户端。

## 给领域/事务模块的接入范围

可以据原证据建立 CSubmit2Npc 专用入口、submitType1路由、实例key/count解析、静态原TargetID匹配与原TargetNum保留。可用SSubmit2Npc的原配置空列表路径展示选择器；提交后按当前角色库存的真实数据处理，不复用禁止绑定的一般转移规则。

精确扣除“等于TargetNum”、拒绝超额/不足、排除已装备、拒绝重复key、限定请求项数、过期ticket、版本/epoch校验和同事务奖励/完成属于服务端应明确的政策与安全约束。静态配置支持按TargetNum恢复需求，但本轮没有原服务端消费代码，若实施精确消费需分开标 `inferred/designed`，不能由本报告背书为原服已验行为。

未确认：所有flags语义、品质/特殊状态资格、TargetNum0规则、动态/多模板组合数量、跨堆优先级、超额交物的原服行为、两个value完整显示语义、非空SSubmit列表tail含义、真实客户端显示/确认回路。未实测部分保留；不因此扩大本批为在线验证或通用交付实现。

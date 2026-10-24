# 普通NPC修理支付：显示证据与旧凭据兼容

2026-10-23。适用本地端游1.6.1/网络601；research后台窄查，重读research、codebase-design、ARCHITECTURE及DESIGN_AUTHORITY。生产源码/政策只读；仅新增本文。没有运行客户端、服务、GUI、真实账号/库、战斗或修理事务，也没有重跑既有96例。

## 可交付结论

1. **client_verified：既有4组付款显示动态执行全部固定method1，不是method2。** 它们实际执行了等级getter、钱包读取和原确认回调，但报价是声明的夹具，文字绘制跳过。不能将这4组改称普通修理支付动态验证。
2. **client_verified（静态）：普通method2/服务513进入同一CEquipRepairDlg，同一余额显示函数在报价之后没有按method分流。** 人物属性490与选中装备原level都严格小于60时显示绑银；任一≥60显示现金。这是普通方法的客户端显示依据，不是原服最终扣款证明。
3. **unknown：原服余额不足时拒绝、改扣现金、混合付款，以及选中项变化至确认期间如何重验。** 所查本地显示分支仅选择一个钱包并着色，没有发现不足后另取现金的逻辑；这不能排除服务器侧fallback。
4. 普通`condition.2`现金策略仍是当前明确设计。若root采用低级绑银的新支付政策，应独立标designed并限普通method2/513；不改变method1家族声望规则，也不开放特殊tag6..11。
5. 旧paid回放已有三层身份。最小兼容方案必须保留其原指纹和跳过随机数/扣款的路径；不能仅在旧函数中把`cash`替换成`bound_silver`，也不能给原指纹追加新参数后要求旧记录通过新比较。

## 原显示证据的精确适用性

原映像[evidence/native-image.bin](native-image.bin)，BASE `0x400000`，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。本轮用[native_inspect.py](../native_inspect.py)独立反汇编下列函数；既有动态结果来自[npc-special-repairs-native.json](npc-special-repairs-native.json)，原脚本[research_npc_special_repairs.py](../research_npc_special_repairs.py)，说明见[NPC_SPECIAL_REPAIRS_NATIVE_RESEARCH.md](NPC_SPECIAL_REPAIRS_NATIVE_RESEARCH.md)。未重跑96例，未重写其脚本或结果。

| 证据 | 可确认范围 |
|---|---|
| 原4组fixture | `payment_display`将anchor+0x1b8起连续写NPC low/high、**method1**、column4；报价hook断言第二参数=1；确认对象与原marshal也固定1。4组等级59/59、59/60、60/59、60/60均不是method2。 |
| 普通513入口 | `0x1638029..0x1638040`读取NPC key高低字，push **2**，经`0x16299a0`取同一修理UI，再调`0x10de1e0`。 |
| 同UI刷新 | `0x10de1e7`将参数method存对象+0x1c0，`0x10de1f4`调`0x10dd800`；后者`0x10dd930`调用`0x10dc090`，此前为共用控件清理，无method1专用条件。 |
| 方法只参与报价 | `0x10dc0e0..0x10dc0ea`读取对象+0x1c0，把method和选中item传给`0x10dbb20`。此后到余额选择/额度比较没有method判断。 |
| 低级选择 | `0x10dc0fd`调原人物level getter`0x1135590`，`0x10dc102..105`以有符号jge判断60；仅小于60才`0x10dc109`调原装备level getter`0x1074d10`，`0x10dc10e..111`再次有符号jge判断60。两次均不跳才读wallet+0xc8/+0xcc，并选文案ID0xc4c6。 |
| 其余选择 | 任一等级≥60到`0x10dc12f`，读wallet+0xb0/+0xb4，并选文案ID0xc37e。绑银/现金名称来自已闭合[CURRENCY_UI_BRIDGE_RESEARCH.md](CURRENCY_UI_BRIDGE_RESEARCH.md)，不是猜偏移。 |
| 额度显示 | `0x10dc20a..0x10dc22a`执行64位比较，余额不足为0xffff0000，足够为0xff00ff00。没有再读另一个钱包或拼接余额。其后控件可点击资格未由这4例执行证明。 |
| 确认上行 | `0x10dda40..0x10ddacf`从同对象保存字段搬运method/NPC/column/itemKey并发送CRepairEquipItem `0xc0413`；原marshal`0xe4cf30`布局为BE32 method、BE64 NPC key、BE32 column、BE32 itemKey，共20字节，无钱包字段。 |

这里装备level来自原getter，不是needLevel；当前普通Inventory从citemattr的`level`取修理等级，见下文。人物getter的490是原人物等级，不能拿临时显示级别或客户端传参替代。严格“<60”包含59但不包含60；对负数的机器分支行为不能当作合法人物/装备等级资格。

既有4组余额有不同高32位：cash=8589934609、bound=4294967551、quote夹具=6442450944。59/59实际读c8/cc且不足，其余读b0/b4且足够。它证明选择了哪个64位余额，没有证明family实际应扣绑银：2012官方家族修理另说家族声望，两类证据不得混成同一业务扣款结论。

普通费用函数`0x10dbb20`在普通tag分支按method选择表字段：method0 skillrepair、method1 familyrepair、method2 npcrepair。该报价字段选择与显示的钱包选择是两件事。原tag6..11走特殊报价；既有12个真实模板被当前`Inventory._ordinary_equipment`拒绝、49009放行的证据沿用，不据855也用method2就开放。特殊报价继续unknown。

## 官方同款端游窄查

检索日期2026-10-23，仅官方端游`sdxl.wanmei.com`，没有使用手游、神雕2、后期化境/怀旧活动数据作为1.6.1原规则。

- **guide_supported**：[2012-06-23《装备打造》](https://sdxl.wanmei.com/info/intro/20120623/131855.shtml)，本轮成功打开，修理段原页面第121–138行：NPC修理消耗金钱且可能失败；家族铁匠修理成功率较高并消耗家族声望；失败降低10点最大耐久，最大耐久≤10不可修理。没有说明人物/装备60阈值、绑银还是现金、不足切换或混合付款。它不能反向覆盖本地UI显示，也不能证明原服会扣哪种钱包。
- 同站[2012-07-05《装备打造》](https://sdxl.wanmei.com/info/newplayer/50to69/20120705/132376.shtml)的检索正文包含相同修理规则；本轮直接打开超时，故不增加独立确认或扩大其效力。无需借其打造熟练度中的“60”证明修理支付阈值。
- 定向检索组合：`修理+绑银`、`修理+60级以下`、`修理+60级+绑银`、`修理+储备金`、`修理+银两不足`、`修理+绑银不足`、`修理+优先+银`及`/info/修理+绑定/60`。命中前述打造说明及无关后期公告；未找到可确认低级绑定银/60阈值/不足fallback的历史官方条目。此处是本轮范围内未查到，不是断言所有历史页面都不存在。

因此低级支付阈值只有本地客户端**显示**证据；新服务器扣款、fallback和失败是否付费仍须root明确designed，不能标成guide_supported原式。

## 当前真实调用与三层旧凭据

行号对应本轮只读工作区；并发后续变更以函数和指纹字面量定位，不表示发布文件已同版。

| 所属Module / 位置 | 实际Interface与持久身份 |
|---|---|
| [npc_repairs.py:25](../npc_repairs.py) `decode_repair`、`plan` | 20字节只接受method2；解析后保留NPC/column/item，服务授权固定513且handler=`equipment.repair`。现`RepairIntent`只有service、column、item_key，没有支付政策/人物等级/币种。 |
| [npc_repairs.py:43](../npc_repairs.py) `repair` | 参数`accounts, inventory, intent, precommit=None, *, draw_source, resource_rules, equipment_rules`。单角色事务读当前lease/wallet，查`npc_command_receipts(role_id,request_id)`；旧指纹精确为SHA256(JSON compact `('repair',accounts.npc_gameplay.revision,service.npc_id,intent.column,intent.item_key)`)。没有支付policy/币种/level。 |
| 同函数89–103行 | **仅无外层old**时取一次`draw_source(1000)`；生成`identity='nr:'+sha256(service.request_id.encode()).hexdigest()`；传`item.condition.version`和draw调用Inventory。paid重放不再调用Inventory、不重新取随机数、不重做资源caps transition；仍校验当前租约/来源及执行当前刷新/precommit。 |
| [inventory.py:984](../inventory.py) `repair_equipment` | 参数`db,key,epoch,settlement_id,expected_version,draw,currency_rules`；查询当前所属template并要求普通六槽guard；`level=int(self.items[template]['level'])`，再传condition rules/上述参数/level给下层。没有人物level或付款计划入参。 |
| [equipment_condition.py:208](../equipment_condition.py) `repair` | 参数`db,account_id,role_id,key,rules,currency_rules,epoch,settlement_id,expected_version,draw,level`。先当前钱包/租约，再查旧domain receipt。指纹精确为SHA256(JSON compact `[rules.revision,'npc_repair',key,expected_version,draw,level]`)；当前rules.revision=`2026-10-23.equipment-condition.2`。 |
| 同函数222–231行 | domain old存在则反序列化RepairReceipt并直接return；不加载当前condition版本、不扣钱。无old才校验before.version，算报价/成功结果，执行固定cash扣款，再写condition与receipt。RepairReceipt字段仅settlement_id/item_key/before/after/cost/success，没有payment或币种。 |
| [currency.py:140](../currency.py) `apply_currency` | wallet settlement=`'equipment-repair:'+settlement_id`；purpose=`equipment_repair`；source_ref=`item:{key}`；deltas=`(('cash',-cost),)`。钱包指纹是sort_keys compact JSON `{'policy':currency_rules.revision, **asdict(change)}`，包含真实deltas。相同settlement改成绑银会冲突。 |
| [npc_repairs.py:107](../npc_repairs.py) 当前回复 | 重读当前装备、当前wallet，只发送cash余额；不是历史receipt内余额。若新增绑银，回复必须覆盖实际涉及币种的当前绝对余额，不能读历史余额或用0补未知币种。 |

`condition.2`的费用字段/耐久存档版本与支付策略目前耦合在同一rules对象。`equipment_condition.load`第135–139行要求存储revision精确等于rules.revision；**只为改变支付就升condition revision会令现存耐久读档拒绝**，不是最小兼容修改。`currency.read_wallet`第104–110行同样要求钱包policy精确匹配；直接改currency revision会触发显式迁移要求，不能静默变基线。现currency-v1只允许cash的equipment_repair，bound_silver只允许npc_shop_bound，新增用途必须由root明确授权。

## 供root裁定的最小接线缺口

以下是**建议设计输入，未实施、未发布**：

1. **分离支付政策与耐久存档规则。** 为普通method2/513明确新支付policy身份；将原报价/成功率/耐久`condition.2`继续作为已持久化版本，避免付款切换暗中重建耐久。是否低级只扣绑银、余额不足直接拒绝还是允许fallback/混付，必须逐项定案。当前证据不足以替root选择fallback。
2. **同一角色事务中计算可信付款计划。** 由当前角色权威等级、当前owned template原level、当前钱包和冻结新policy形成不可变支付输入；Inventory/condition Interface当前缺人物等级/支付计划参数。不要从客户端method自行读钱包授权，也不要把家族93并入普通513。普通资格、报价和draw保留所属Module，不把SQL散到NPC调用方。
3. **新执行与旧paid明确分支。** 外层旧`npc_command_receipts`先按原指纹验证后只返回当前状态，不能要求它具有新payment元数据；不重新采样、不补扣绑银、不把历史cash费用退款重付。对直接调用下层的历史domain receipt也保留原六元组指纹的明确兼容读取；其成功历史来自当时cash-only Implementation，不能随当前人物等级重新判币种。无法识别版本/历史格式时应显式拒绝核对，不自动猜币种。
4. **新凭据记录可重放的支付决定。** 至少能识别支付policy、采用的资格等级快照、选中币种/实际deltas和费用；新指纹与旧指纹应有可辨认版本，保持同一稳定command去重。不能先改变裸旧hash再声称兼容。domain RepairReceipt若增加必填payment字段，旧`RepairReceipt(**old)`将失败，须保留旧格式解析或版本化DTO。
5. **钱包动作仍同事务且单次。** 新purpose须列入对应币种允许集合，真实deltas与耐久/资源transition/外层receipt一起提交。若未来允许两币分摊，现CurrencyChange支持多个同号非零delta，但如何选择与余量顺序没有原服证据，仍须明确设计；不能通过先扣一个、失败另开事务扣另一个实现fallback。
6. **保持当前资源/回复行为。** 新成功或失败尝试仍使用现有同事务caps/precommit；paid重放只读当前资源，不重放历史治疗或修理transition。原`messages`只刷新cash是明确缺口，接入绑银后须补当前bound_silver刷新；是否同时刷cash由最终支付策略定，未知钱包不置零。

最小后续验证应围绕这些真实Interface：59/59、59/60、60/59、60/60；政策选中余额不足但另一币足够；原cash paid在新政策下重放不扣款/不重抽/不改耐久；新支付同command冲突拒绝；condition.2旧档不因支付升级拒绝；late precommit错误同事务回滚。这里只列验收输入，本批未运行这些事务或恢复任何玩法。

## 本批方法与范围记录

- research：核对原probe写入参数和JSON，不把method1实验扩大为method2实验；回到原映像检查共用consumer，并用同款端游官方历史页面限制结论。
- codebase-design：将付款策略与耐久状态版本作为不同Interface事实，追到实际三层幂等Seam；最小建议集中在所属Module，保持一个角色事务和权威状态，不引入世界锁、第二钱包或平行耐久账本。
- 决定影响：root可以用“共用客户端显示阈值+未证实原服扣款”制定新designed普通支付政策；必须保留旧cash-only paid，不以家族入口的动态4例给普通原服规则背书。
- 产物：仅本文。验证：既有96例的脚本/JSON只读复核，定向原函数反汇编，当前调用/字面指纹静态核对，官方页面访问与窄检索。没有执行96套、费用/概率回归、SQL迁移或实际修理。
- 未验证：原服最终扣款、fallback/混付、method2的新增动态付款实验、完整GUI按钮资格、真实修理支付/资源显示、部署及商业并发。当前工作区cash-only实现不代表用户现场已验收。

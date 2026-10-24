# 原 NPC 商店：本地货架、回购第 4 栏与响应契约

2026-10-24。采用 research 方法：以原 1.6.1 客户端映像和 PFS 为第一方来源，把原指令观察、离线依赖适配和未知分开记录。本文对应同批脚本、JSON、反汇编；不实现服务器，不改生产、政策、共享入口、真实数据库或服务，不启动游戏界面或战斗。

## 影响接线的结论

**不能把 `CGetBagInfo(column4, NPCkey)` 当成普通商店货架请求。** 原商店的“购买”页从本地 `NpcSellItem` 配置取模板；发 column4 查询的是“回购”页。旧 27 条研究中的服务 2 → 商店类 → column4 发送观察仍成立，但当时发送段前的 tab 条件没有执行，不能把它补解释成普通货架。

原专用回购消息 `SGetRepurchaseItems 0xc0434` 包含 **ItemBag + 实例 key→价格值的 map**，原 handler 明确先清容器 4，再安装到 4 并通知回购界面。`SGetBagInfo 0xc03f3` 的 column4 也可以进入通用 ItemBag 安装入口，但没有价格 map。这两条消费者同时存在；缺少原服务器或网络捕获，**不能证明原服务器收到 query4 后一定选择哪一种响应**。专用回购包是本批原生验证过的完整价格载体，不能反推它授权了哪些 NPC。

## 原类、布局和模式依据

原 `CNpcSellItemDlg` 使用 `NpcSellItemDlg.layout`：方法 `1103060` 引用字符串 `2290078`，方法指针位于类 UI vtable 的 `2290104`。PFS 的 `layouts/npcsellitemdlg.layout` 真正包含下列控件；不是按另一个布局文件名字推断。

| 控件与原文案 | 原初始化写入 | 原分支 |
|---|---|---|
| `NpcSellItem/tab1`，购买 | `11088cd` → UI+34 | 普通本地商品展示、购买路径 |
| `NpcSellItem/tab11`，回购 | `1108928` → UI+38 | `1103cc7` 检查该控件 +530 的选中状态 |

`1103cc7..1103cd0` 未选回购时跳 `1103e55`，设置第一页并走 `1103730` 本地展示；选中时进入回购分支，`1103dad..1103dc6` 查管理器容器 4，缺失才进入 `1103df3..1103e3b`，发送固定 column4 和当前 UI+e8/ec 的完整 NPC key；已有缓存则调用 `1103440`。本批新增两条原指令条件分支验证；查询 sender 本身沿用已存在的原 27 条证据，不重复运行或计数旧案例。

服务 2 原分支 `1636d38` 的开窗参数分开传递：菜单+d8 是首参数；菜单+d0/d4 是 NPC key；另有独立 mode 参数。原 `110a690` 从 callee stack+120 读取 mode，`110a9b5` 放入 EBP，`110aa0b` 写 UI+78。首参数则来自 stack+114，`110b9e6` 写 UI+f0。它们不是同一字段。原 `cnpcconfig` 的 NPC10004 `npctype=1` **不构成 UI mode=1 的证明**；旧 27 条里的菜单+d8=7 也是合成 fixture，不是 NPC10004 的真实首参数证明。

本批普通货架案例明确进入已定位的 mode0 分支，不声称已经证明 NPC10004 在真实菜单中一定以这些参数打开。菜单+d8 的真实赋值来源、每种 NPC 的实际 mode 仍未知。

## 本地货架与 CItemAttr 的关系

`110bd17` 调原 getter `89dc80`，它返回全局 ConfigManager+860；原 ConfigManager 析构 `c9894e..c98959` 对同一成员调用 `8780b0`，该函数写 vtable `2259044`。这个 vtable 的 RTTI 直接是 `knight_gsp_item_NpcSellItem_table_implement@XMLCONFIG`，不是靠相邻字符串猜类型。`878130` 将 lookup 转发给后台表。

原代码用首参数作为该表 lookup key，取返回记录+4 的模板 vector，经原 `f441c0` 复制到 UI+88，并按每页 10 个计算页数。原 PFS `npcsellitem` 共 210 行；本批完整核对全部 attributes/lists，与当前缓存一致，读取长度和 CRC 均通过。NPC10004 同名 key 行的 items 为：

`40103, 40203, 40303, 40403, 40503, 40603, 40703, 40803, 40903, 41003`。

这里只证明该配置行与客户端 lookup 形状，不把“同名 key”补成未经追踪的菜单首参数来源。

原普通页循环 `11039ff..1103b66` 从同一 vector 取模板，传给 `11020c0`；后者调用原 `89d730`（ConfigManager+5b8）及原 CItemAttr table wrapper `86ee90`，以该模板查配置。原指令读取记录+70 的 icon，并在 `1102132..1102137` 把记录 id 传给原 `464dd0`，由原 setter 写 cell+26c。

本批六条链保留完整 10004 vector，分别给原循环体的 page1/slot `{0,4,9}`，以原 PFS CItemAttr id/icon 为后台返回。原 getter、wrapper 转发、id/icon 消费和 setter 均执行；名字/图像绘制依赖适配。随后同一 cell 供原 `1106580` 使用，数量 `{1,7}` 的 `CBuyItemFromNpc 0xc232c` 实际发送的是 `BE64 NPCkey + BE32 template + BE32 quantity + BE32 mode0`，没有传商品库存实例 key。数量 7 是请求构造 fixture，不证明该模板可购买 7 件或真实库存无限。

普通货架的恢复所需展示数据已经在客户端配置中；本批没有发现需要服务器为它生成库存实例 ItemBag 的证据。`CItemAttr.maxNum` 等字段不等于 NPC 库存数量，也不能把 99 或 0 解释为无限库存。价格、币种可用性、绑定、限量与权限需要另外核实。

## 回购响应的最小可验证表示

原 `SGetRepurchaseItems` constructor `ef64e0`、marshal `ef65b0`、unmarshal `ef6640` 全部执行；非空和空包均完整解码并重新编码相等。外层不是 SGetBagInfo：

`ItemBag(cash:u64, capacity:i32, compact-count, Item...) + compact-price-count + (item-key:i32, value:i32)...`。

共享 ItemBag **没有** SGetBagInfo 最后的 flag；专用消息紧接价格 map。价格 map 的 key 是实例 key，不能用模板 key 替换。

| 字段 | 本批原指令消费与界限 |
|---|---|
| template | 原 Item bean+4；最终回购格子从 Object+c 取模板以查配置 |
| 实例 key | bean+c；price map 原 `5f08c0` 按此 key 查找；回购请求取 Object+14 |
| position | bean+10；Object+48 供回购网格定位；测试位置 0/4/9，不证明任意位置有效 |
| quantity | bean+20；Object+28 供展示与价格计算；保持真实卖出实例的数量，不造库存数 |
| flags / binding | bean+8 原样保留；测试 0/1；本批不是新的绑定位资格研究 |
| expiry 与剩余字段 | wire 的三个 u64 和另一个 i32 在 fixture 中为 0，语义未定位；0 不等于“永久”或“无限” |
| cash、capacity | 测试值分别 123456、20；仅为原 codec 可接受输入，不是原服务器或设计数值 |

Item 的本批 wire 形状为 `i32 template, i32 flags, i32 key, i32 position, u64 opaque0, i32 quantity, u64 opaque1, i32 opaque2, u64 opaque3`。回购库存应来自当前拥有方保存的真实卖出实例；本地普通货架无法推导这些实例字段。

原 handler `10a90c0` 调 `108f9f0(4)`，然后把消息+8 的 ItemBag 和 +30 的价格 map 交给 `10a49f0`。本批在两个调用边界捕获，不假称完成全套容器插入。安装函数的静态原链创建 ItemRef、以真实 key 安装，再经原 `5f08c0` 查 map；本批直接使用原 decoder 生成的真实 STL tree 执行 `10a4b44..10a4b92`，确认 map 值写到 wrapper+7c，未替换价格查找 getter。

安装尾段 `10a4c6c..10a4c76` 在商店存在时调用 `1103440`。原回购展示先枚举容器 4；从 Object+48、+c、+28 取网格位置、模板、数量，之后把同一 ItemRef 写 cell+278。原按钮回购分支 `1109d6c` 检查 UI+38，`1109ddf..1109e3c` 从该 ItemRef 的 Object+14 取实例 key，构造 `CRepurchaseFromNpc 0xc232e = BE64 NPCkey + BE32 item-key`。本批执行此发送段，刻意让模板与实例 key 不相等，并以原 marshal 核线体；完整资金/背包/按钮前置检查没有执行。

回购原 `1103506..1103517` 的默认展示计算为 `map值 × 1.1 × quantity`，随后 `1103520..1103540` 还允许 ConfigManager+b28 的配置覆盖。本批只执行并验证覆盖前的默认计算，不能宣称最终原价、单价语义、手续费或收费设计已经恢复。现 `npc_shop_sales._listing` 将保存的整叠 cash_price 放入 map，因此可能发生显示口径或扣款口径不一致；需要独立定价研究，本文不修改结算。

## 上下文、失效与接入限制

请求读取 UI+e8/ec 当前 NPC key；原开窗也比较 mode/key/首参数是否相同。两个响应的 envelope 都没有 NPC key 或请求代号，原专用 handler直接作用全局 ItemManager 容器 4；因此这不是可用来确认当前 NPC 的接收身份。原清理方法 `110a510` 中 `110a55a..110a665` 对容器 key4 查找并删除，随后清 global294acdc；本批仅静态追踪该清理方法，不宣称已验证所有关窗、换 NPC、地图或断线触发。

今后 NPC 所有方接入 readonly query4 时，应先由现有会话/场景归属、可达性、当前 NPC 服务资格和当前菜单上下文确认该请求确实属于回购；拥有方准备不可变的真实回购快照，再由现有投递边界发送。上下文更换、离开或关闭后的响应失效需要拥有方保证；原包本身无法携带额外 fence。这里是接入约束，不是新增代码、网络授权或完整并发验证。购买服务 2 与恢复端 sale policy 服务 214 的 NPC 集合不能自动视作同一集合。

## 本批验证、产物和未验证范围

新执行 **16 条独立 fixture 链**：3 条原配置货架向量/分页；6 条完整源 vector 的格子模板→CItemAttr→cell→购买请求；2 条原 tab 条件分支；3 条非空回购完整 codec→价格 map→默认展示计算→实例 key 回购请求；2 条空 SGetBagInfo4/专用回购响应对照。内部 decoder、marshal 和子调用不另加计数。旧 27/112/96/656 四批脚本均未执行，16 份历史产物 SHA 保持。

PFS 另核 citemattr 全 12280 行、cnpcconfig 全 4127 行的完整 attributes/lists 与缓存一致；原 BXML 不保留提取时的缩进 tail，格式空白不参与比较，并断言没有嵌套或带属性的子列表被遗漏。所有条目 CRC/长度/SHA 与缓存 SHA 见 JSON。两个原 archive、三个缓存、原映像、读取的 helper、生产相关模块及 ready 等实际输入/保护项共 39 文件，前后 SHA 一致。ready 的 9b05/761c 完整 SHA 也分别硬性核对。

在项目根运行指定 Python `-X utf8 -B revival/research_npc_shop_catalog.py`。脚本只写本批 JSON 和反汇编，并在发现保护输入变化时拒绝输出。host/dependency adapters 逐项列于 JSON：后台原行的内存布局、CRT 分配/复制、名字图像绘制、选择桥、捕获发送、清/装调用边界；原 getter、wrapper、协议 codec、价格查找与被测分支不由 Python 替代。

仍未验证：原真实服务器响应选择；NPC10004 的真实菜单首参数/mode；所有服务/NPC 权限；普通商品价格、币种/限量/绑定规则；回购最终配置覆盖价格与过期政策；完整原容器安装、GUI 和交互时序；运行中服端或部署效果。本文不把原商店能接收一个包解释成某 NPC 已获授权。

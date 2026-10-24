# 原生货币槽到背包显示的桥接证据

2026-10-23（Asia/Shanghai）。本地端游1.6.1 / 网络601，沿用同一`native-image.bin`。仅只读研究及本文件写入；未启动/注入客户端、未在线发包、未操作手动测试现场、未修改任何运行时或配置。

## 已闭合的两路接线

| 业务钱包名 | 原生槽/余额 | 可接消息与body | 显示链结果 |
| --- | --- | --- | --- |
| cash | `money_1`，wallet+0xb0/+0xb4 | `SRefreshMoney 0xc03fa`：BE32 kind=1 + BE64绝对余额，共12字节 | 背包`MainPackDlg/money`；同栏图标Xianjin、tooltip“银两” |
| bound_silver | `smoney`，wallet+0xc8/+0xcc | `SRefSmoney 0xc0012`：BE64绝对余额，共8字节 | 背包`MainPackDlg/reserve`；同栏图标Chubeijin、tooltip“绑银” |

**以上是原生协议槽→钱包字段→观察者→具体控件→本包UI语义的静态闭环，可标`client_verified`。** 真实屏幕显示仍未实测。消息金额必须是当前权威余额，不能发送本次奖励增量。

这不改变主策划业务裁定：`MoneyReward→cash`、`SMoney→bound_silver`仍是`designed`，见`evidence/CURRENCY_DECISION.md`与`design/currency-v1.json`。任务字段到币种，与币种到原生显示槽，是两个独立证据层；不得因显示桥闭合将任务字段映射升级为原版事实。

`money_2`（wallet+0xb8/+0xbc，SRefreshMoney.kind2）不用于本批绑银接线。它也会通知现金回调，但现金回调仍读+0xb0/+0xb4，未单独显示该槽；其完整业务用途本轮不追究。

## 原始来源与方法

- 静态映像：`D:/神雕侠侣/revival/evidence/native-image.bin`，BASE0x400000，沿用已知SHA-256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`；本轮未重新采集。使用已有`native_inspect.py`与Capstone只读定位字段引用、构造、观察者注册及回调。
- 原包：`D:/神雕侠侣/artres/ui.pfs`内`layouts/mainpackdlg.layout`，本轮直接`PfsArchive.read`校验目录/长度/CRC，再用`bxml.decode`读取控件及同栏图标。展开17453字节，CRC32 `dd6eff96`，展开SHA-256 `7a18b09600f8e36a863f7aa6217a59a677b9b42ea712ac0251db4ef974b73a30`。
- 可读布局镜像：`revival/decoded/ui/layouts/mainpackdlg.layout`；本轮语义来自重读原包，不仅凭widget名字推断。
- 前批基础：`evidence/CURRENCY_RESEARCH.md`记录消息RTTI、原构造、编解码、余额覆盖行为。原报告的“尚未追通UI槽位”由本报告补充；不覆盖其任务/币种映射未知结论。

## cash 的完整引用链

1. **原生接收：** SRefreshMoney handler `0x10a1560`，kind1在`0x10a1609..0x10a161d`将协议金额覆盖`[0x2944628]`钱包+0xb0/+0xb4，然后`0x10a162a..0x10a1633`通知wallet+0x10观察者。
2. **观察者注册：** 背包构建函数`0x10f3f20`中，`0x10f3f64..0x10f3f98`取wallet+0x10并注册回调`0x10ef250`；`0x10f3f99..0x10f3fcd`还将同一回调注册到wallet+0x20。不能将“观察者有两个”解释成两个显示币种。
3. **读取实值：** 回调`0x10ef250`在`0x10ef27e..0x10ef290`读取wallet+0xb0/+0xb4；两种颜色分支均使用这两个dword格式化金额，`0x10ef2a7`或`0x10ef2ea..0x10ef30e`写入背包对象+0x3c所指的数值控件。
4. **控件构造：** `0x10f419c`取ASCII路径`0x228f52c = MainPackDlg/money`，经`0x4552c0`查控件，`0x10f41e9`保存到背包+0x3c。
5. **UI明确文字：** 原布局父控件`MainPackDlg/Back3`的直接子项是数值`MainPackDlg/money`和图标`MainPackDlg/money1`；后者Image=`set:MainControl image:Xianjin`、Tooltip=`银两`。该现金/银两栏与绑银栏分开，不是相同名字猜测。

另有本包cstringres413=`现金`，前批`0x17a2600`的UI类别1取此文字；本轮不拿该UI枚举直接推导协议kind，而以上述钱包读取和控件绑定闭合实际显示。钱包余额对应现金/银两栏的事实不意味着已还原所有现金流通规则。

## bound_silver 的完整引用链

1. **原生接收：** SRefSmoney handler `0x10880f0`，`0x1088173..0x1088185`将金额覆盖钱包+0xc8/+0xcc；`0x108818b..0x1088194`通知wallet+0x40观察者。
2. **观察者注册：** `0x10f3fce..0x10f4001`取wallet+0x40并注册回调`0x10ef340`，回调目标背包对象作为上下文。
3. **读取实值：** `0x10ef368..0x10ef395`读钱包+0xc8/+0xcc，`0x10ef39b..0x10ef3bc`把格式化后的数值写到背包+0x44控件。界面创建时`0x10f50b7..0x10f510e`也读取同一槽并写+0x44，覆盖首次开背包和后续通知两条路径。
4. **控件构造：** `0x10f42b6`取`0x228f4f0 = MainPackDlg/reserve`，`0x10f4303`把返回控件保存到背包+0x44。
5. **UI明确文字：** 原布局父`MainPackDlg/Back4`包含数值`MainPackDlg/reserve`和图标`MainPackDlg/yuanbao2`；后者Image=`set:MainControl image:Chubeijin`、Tooltip=`绑银`。虽然图标路径含yuanbao2，真实tooltip是绑银，应以完整链条确认，不按变量拼写认币种。

因此本包`smoney`槽显示为绑银；图像资源仍叫Chubeijin是历史命名线索，不足以证明所有早期官网“储备金”规则均适用于此版本。

## 元宝顺序：同批轻量追踪结果

cash/绑银闭合后，沿同一背包函数额外得到以下静态链，无需扩大账户算法研究：

| SReqYuanbaoNum `0xc659a` body字段 | handler写入 / 观察者 | 背包回调读取 | 具体控件 |
| --- | --- | --- | --- |
| 第一个BE32（对象+8） | `0x112c3ac..0x112c3c4`覆盖人物+0x330，通知+0x310 | `0x10ef6e0`：`0x10ef70d/0x10ef729`读取+0x330，再写背包+0x84 | `MainPackDlg/yuanbao`，同栏图标Tooltip说明“元宝，用于购买喇叭等元宝道具” |
| 第二个BE32（对象+0xc） | `0x112c3cb..0x112c3e3`覆盖人物+0x334，通知+0x320 | `0x10ef780`：`0x10ef7ad/0x10ef7c9`读取+0x334，再写背包+0x88 | `MainPackDlg/BindYuanbao`，同栏图标Tooltip“绑定元宝” |

控件绑定：`0x10f5135`取路径`0x228f3f8`，`0x10f5186`写背包+0x84；`0x10f519a`取`0x228f3e0`，`0x10f51e7`写+0x88。观察者注册`0x10f51f9..0x10f522f`将人物+0x310绑定`0x10ef6e0`；`0x10f5231..0x10f5267`将+0x320绑定`0x10ef780`，随后`0x10f526b/0x10f5272`主动刷新两栏。

因此**静态顺序可确认：第一个元宝、第二个绑定元宝**。前批报告未确认顺序的空白在此补齐；未进行该消息codec执行或真实客户端显示检查，本批优先接现金/绑银，不要求立刻接元宝。

## 余额宽度、范围与已完成验证

- cash/绑银原槽是64位，消息分别BE32 kind+BE64余额、BE64余额。原校验拒绝负signed64，允许0与`2^63−1`；这证明编码/原生约束工作域，不证明原服业务余额上限或UI布局能无损容纳19位文字。
- 主策划本批已提供`currency_protocol.py`的原生槽Interface及`evidence/currency-native-verification.json`。本轮只读后者：money_1金额4294967303经原serializer0xe4e9a0匹配12字节；money_2金额signed63max匹配12字节；smoney金额1099511627899经原serializer0xe40e70匹配8字节。此验证覆盖余额编码宽度，报告仍标真实显示未验证；本代理未重复运行codec。
- 元宝两字段是独立32位，不能将账本signed64金额直接塞入一字段，也不能误作BE64。显示回调使用`cdq`扩展数值，因此现有证据下非负signed32范围`0..2^31−1`是保守兼容范围；原服实际元宝上限未确认。若账本高于此范围，须显式拒绝或留待设计，不能截断低32位。
- `money_2`的金额也按signed64原生序列化，但本轮未给业务名称，不允许把它当bound_silver的替代消息。

## 接口与接线限制

按codebase-design，本研究补充的是显示Adapter的Implementation证据。外部Interface应接受已确定币种的**当前绝对余额**并返回逻辑消息；wallet内存偏移、协议kind和控件名字保持在显示Module内部，避免各任务/组织调用方重复复制。角色/连接所有者接线规则仍按`ARCHITECTURE.md`，本轮不修改这些实现。

可接两路：cash→`encode_balance('money_1', current_cash)`；bound_silver→`encode_balance('smoney', current_bound_silver)`。这是给集成方的证据建议，不声称主策划新增业务包装已写入或已上线。事务成功后重新读当前余额；重试历史奖励回执不能覆盖更新余额。0余额有效，仍应发送原0，不为展示而赠送或合并。

未证明：首次世界快照里是否必须同步初始化所有钱包槽、背包未构建时原handler观察者生命周期、其他面板与支付选项全部行为、money_2业务含义、实际消费优先级、原服货币上限和真实视觉效果。静态显示桥不证明原任务币种映射、实际发奖、交易可行或元宝购买规则。

## 方法、决定、产物及验证范围

- 技能：沿用全文仍在上下文的 [research SKILL.md](D:/User/Documents/Codex/.codex/skills/research/SKILL.md)，并本批读取 [codebase-design SKILL.md](D:/User/Documents/Codex/.codex/skills/codebase-design/SKILL.md)。研究以原生观察者/实值读取与原包控件文字闭环；codebase-design决定账本规则、任务字段映射与显示Adapter保持独立证据层和小Interface。
- 决定：cash/绑银可接现有原生槽；不复用UI编号当协议kind；任务映射继续designed；元宝顺序补静态证据但不扩大上线范围。
- 产物：仅本文件`revival/evidence/CURRENCY_UI_BRIDGE_RESEARCH.md`。
- 验证：原UI包CRC/长度/BXML及控件父子关系；背包控件构造、余额回调、观察者注册与已知handler字段的静态链；读取主策划离线codec验证结果，未自行重复执行。
- 未验证：真实客户端余额显示、运行时业务接线、任务到账、完整支付/兑换和原服上限。未启动/注入/发在线包/更改配置/操作当前现场。

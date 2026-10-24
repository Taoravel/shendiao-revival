# 任务货币与原生刷新映射调查

日期：2026-10-23（Asia/Shanghai）。目标：项目本地端游1.6.1 / 网络601。只读原包与现有原生映像，随后查官方端游资料；未启动游戏、发包、操作现场或执行玩法回归。仅写本文件。

## 交接结论

- 当前任务表 `MoneyReward` 全部2460行均为0；`SMoney`有307行非0、2153行0。可接任务表 `moneyreward` 全129行为0，`rmoneyreward`有78行非0。零是原数据，不是缺失，不补成现金。
- 当前客户端“救世狂人”领取条件27级，奖励在后继210002：Exp20000、Pet10000、SMoney5000。早期官网25级、Exp10000、储备金3500只能作历史旁证，不能覆盖本包金额。
- 原生可确认三个独立刷新机制及其字段/覆盖行为：`SRefreshMoney(0xc03fa)`、`SRefSmoney(0xc0012)`、`SReqYuanbaoNum(0xc659a)`。**字段同名不证明任务SMoney与SRefSmoney必然同币种。** 当前尚未追通任务字段→权威余额类型→UI标签的完整链。
- 客户端文本与独立UI类别明确区分现金、元宝、绑银、绑定元宝；此UI枚举与刷新消息kind不能混用。不能把储备金/绑银转入可交易现金来绕过未确认映射。

## 原包核验与任务奖励关联

读取 `D:/神雕侠侣/artres/config.pfs`，采用已有 `pfs.py::PfsArchive.read` 的长度/CRC/目录检查、`bxml.py::decode`，目标任务表经ET.indent后按`inspect_client.py::catalog_rows`与现有目录全量一致。所有操作在内存完成。

| PFS 条目（autoconfig/下） | 行数 / 字节 | CRC32 | 展开SHA-256 |
| --- | --- | --- | --- |
| knight.gsp.task.cmainmissioninfo.xml | 2460 / 2026233 | 3f7ab7b3 | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |
| knight.gsp.task.cacceptabletask.xml | 129 / 61388 | f3c31dd0 | d071fd8f9e7e73dfed0e01e93081d9ae8dcc943c8793c8ac9ac49e52493ca9e2 |
| knight.gsp.message.cstringres.xml | 2904 / 126182 | 146da741 | 269e18f659ed1ec19984714faab798d2fa8449392e5d4b5b65d566d12adb2aae |

可读镜像：`revival/decoded/config/autoconfig/knight.gsp.<名称>.xml` 与 `revival/catalogs/knight.gsp.<名称>.json`。本轮数值以原包为核验来源。

### 同名任务不可跨版替换

| 当前原包位置 | 等级/关联 | 人物经验 | 宠物经验 | 现金候选字段 | 另币种候选字段 |
| --- | --- | ---: | ---: | ---: | ---: |
| cmainmissioninfo 210001 `[支线]救世狂人` | MinLevel27；PostMissionList=[210002] | 0 | 0 | MoneyReward0 | SMoney0 |
| cmainmissioninfo 210002 同名 | MinLevel0；PostMissionList=[210099] | 20000 | 10000 | MoneyReward0 | SMoney5000 |
| cacceptabletask 210001 `救世狂人【临安】` | minilevel27；destnpcid10958 | expreward10000 | 无此字段 | moneyreward0 | rmoneyreward5000 |

210099不在本次2460条任务原表中，保持后继未解析，不替换成任意终点。原可接表的expreward10000与实际后继任务ExpReward20000不同，说明可接展示与后续结算行不能当同一奖励副本。

此例支持“可接任务展示的rmoneyreward5000与后续任务SMoney5000有关联”的 `inferred` 判断，不足以确认币种和结算规则。不能在210001领一次、210002再领一次；也不能简单对整条图所有后继求和（分支、选择与缺失ID尚需规则）。已确认每步原奖励为0时保持0，只有缺字段/不可取得的规则才进入设计流程。

### 任务字段的原生配置解析

原生 `MoneyReward` UTF16字串`0x226c534`：`0xbb5b09`取字段，经`0x409db0`后在`0xbb5b37/3d`写配置对象+0xa8/+0xac，表明该配置字段按64位读取。

原生 `SMoney` UTF16`0x226c4f4`：`0xbb5bd6`取字段，经`0x409db0`后`0xbb5c04/0a`写+0xc0/+0xc4，同样为64位配置字段。可接表`rmoneyreward`字串`0x2266ab4`：`0xa77c68..0xa77c94`经`0x409ce0`写配置对象+0xa0，为32位读取。

这些是配置字段/宽度证据，尚非货币语义。映像中另有交易/物品相关字典键也叫`SMoney`，不能仅因同一字符串被复用而认作任务结算链。

## 原生刷新消息：身份、字段与覆盖行为

来源 `revival/evidence/native-image.bin`，BASE0x400000，沿用项目已知SHA-256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。本轮未重新采集/哈希，使用`native_inspect.py`的RTTI/虚表/refs及Capstone离线反汇编。下列是静态证据，未执行codec或网络测试。

### SRefreshMoney@item：0xc03fa

- RTTI`0x289e874`；vtable`0x2277b14`；构造`0xd9e1a0`写type0xc03fa，+8类型字段0，+0x10/+0x14金额0。
- marshal`0xe4e9a0`：先将+8交BE32 writer0x770960，再将+0x10/+0x14交BE64 writer0x7709b0，body共12字节。decoder`0xd9e250`顺序一致。
- 约束`0xd9e1c0`要求kind在1–10，金额为非负signed64范围；这里是余额字段合法性，不证明十种货币的名字。
- handler`0x10a1560`在wallet`[0x2944628]`存在时：kind1于`0x10a1609..0x10a161d`直接覆盖wallet+0xb0/+0xb4，随后通知观察者；kind2于`0x10a1649..0x10a1656`调用`0x10a0da0`，后者直接覆盖wallet+0xb8/+0xbc。所读handler其他kind没有余额写入分支。
- 这是**绝对余额**，不是本次奖励差值。尚未为kind1/kind2建立足够的现金/储备金/其他币种名称链，不建议因UI枚举同为1/2就套用。

### SRefSmoney@gsp：0xc0012

- RTTI`0x2887538`；vtable`0x2270540`；构造`0xd54dd0`写type0xc0012，金额+8/+0xc为0。
- marshal`0xe40e70`交BE64 writer，body8字节；约束金额非负；decoder`0xd54e70`。
- handler`0x10880f0`在wallet存在时，`0x1088173..0x1088185`将金额直接覆盖wallet+0xc8/+0xcc，再通知wallet+0x40观察者。未把金额与旧值相加。
- 可确认这是独立余额渠道；**不能仅凭Smoney拼写就认定它是任务SMoney/储备金/绑银的刷新协议**。

### SReqYuanbaoNum@yuanbao：0xc659a

- RTTI`0x28bca08`；vtable`0x22811e0`；构造`0xdf4e00`置type0xc659a、+8/+0xc为0。
- marshal`0xe5bb70`顺序写两个独立BE32，不是一个BE64；body8字节。decoder`0xdf4e90`。
- handler`0x112c3a0`将第一个字段覆盖人物全局对象`[0x2944550]`+0x330，第二个覆盖+0x334，分别触发+0x310、+0x320观察者。
- 命名空间和类型支持元宝账户相关解释，但本轮未确认+0x330/+0x334哪个是元宝、哪个绑定元宝。不能互换或合并；字段符号/合法上限仍需后续核验。

## UI名称的确定证据与枚举隔离

原`message.cstringres`：251=现金奖励、252=绑银奖励、255=现金总奖励、256=绑银总奖励；413=现金、414=元宝、415=绑银、416=绑定元宝。

原函数`0x17a2600`按传入类别1–4走jump表`0x17a269c`，分支分别在`0x17a2621/3a/53/6c`取cstringres413/414/415/416，经`0x837060`加载文字。因此**此函数的UI类别**可确定：1现金、2元宝、3绑银、4绑定元宝。

这是局部UI类别，不是已确认的`SRefreshMoney.kind`协议枚举。尤其SRefreshMoney目前只在handler处理kind1/2，SRefSmoney则是无kind的单独消息，不能把UI类别3发送进SRefreshMoney就宣称在刷新绑银。

原界面奖励函数还在`0x15fe3e2`和`0x17c51ed`取文字251，在`0x15fe5c3`和`0x17c53c2`取252，确认现金/绑银奖励有分开展示路径。但本轮未将这些函数的全部实参回溯到任务配置+0xa8/+0xc0，故不把它们冒充`MoneyReward/SMoney`到币种的完整证据。

本轮原cstringres相关短文未出现“储备金”这一名称，早期攻略采用储备金，当前客户端常见绑银。两者可能存在历史命名关系，但**本轮未证明它们完全同义**。canonical模型应先区分明确的钱包槽/协议渠道和来源字段，待映射裁定后再命名；不能把未知槽归并到现金。

## 官方端游旁证及冲突

- [官方《剧情任务》，2012-07-28](https://sdxl.wanmei.com/info/renwu/script/20120728/133491.shtml)：本轮打开成功。早期救世狂人为25级，奖励人物经验10000、储备金3500；本包27级、Exp20000、Pet10000、SMoney5000。记录版本冲突，金额和等级优先当前客户端，不用早期同名案例证实SMoney精确币种。
- [官方《古董玩法》，2012-07-04](https://sdxl.wanmei.com/info/newplayer/20to29/20120704/132332.shtml)：元宝购买宝铲，古董涉及储备金或游戏币，正文另用现银。支持历史端游有多个货币渠道，但混合称谓不能建立本客户端刷新kind映射或汇率。
- [官方《门派系统》，2012-07-28](https://sdxl.wanmei.com/info/system/other/20120728/133515.shtml)：首席挑战消耗现银，投票奖励储备金，说明二者不可笼统视同一资产。本轮不导入其历史金额。
- [官方两周年活动，2014-09-19](https://sdxl.wanmei.com/news/gamenews/20140919/164042.shtml)：元宝卡可获得绑定元宝，支持绑定与非绑定元宝区分。不能据此确认0xc659a两个字段的顺序。

检索聚焦官方端游“绑银/现金”“储备金/现银”“元宝/绑定元宝”；手游与2025商城活动未作为本地1.6.1规则依据。官方资料没有公开本版本任务字段和协议kind的代码对应。

## 仍未知与主策划可design边界

| 项目 | 支持到哪里 | 仍需核验或明确design |
| --- | --- | --- |
| 任务MoneyReward | 原配置64位、当前全0 | 非零时对应哪个账户；当前0必须保留，不为补玩法另奖现金 |
| 任务SMoney | 原配置64位，后继有具体原金额 | 对应绑银/储备金或其他槽的完整UI/结算链；未确认前独立pending，不转入现金 |
| 可接rmoneyreward | 原32位展示；救世与后继SMoney同为5000 | 展示汇总口径、结算步骤、分支影响；不得双发或覆盖后继金额 |
| canonical钱包 | 至少存在不同原刷新槽和四类UI名 | cash/bound_silver/reserve/yuanbao/bound_yuanbao与原槽/协议逐项映射、是否历史同义；不要据同名或同编号合并 |
| 货币刷新 | body和绝对余额覆盖已静态确认 | 生产codec执行校验、登录初始化对应、合法类型/范围、客户端显示；不发奖励增量冒充余额 |
| 流通与消费 | 现金/储备类必须分开 | 哪些可交易、消耗优先级、混合支付、上限/溢出、兑换比例、商城绑定传播均未完整确认；不能默认储备金可交易 |

可将当前客户端原金额标`client_verified`；官网历史称谓标`guide_supported`；SMoney与rmoneyreward关联标`inferred`；任何未证实币种接线或消费策略由主策划单列`designed`，不得把整套标原版还原。原任务当前已保留的pending不得在缺证据时直接清账。

## 方法、决定、产物、验证与未验证

- 方法：沿用全文仍在上下文的 [research SKILL.md](D:/User/Documents/Codex/.codex/skills/research/SKILL.md)，作为主任务后台代理先一手原包、再原生引用、最后官方旁证；本批重读`DESIGN_AUTHORITY.md`。没有实现服务器状态或网络功能。
- 决定：保留0；以任务实际后继行区分奖励归属；记录早期官网冲突；区分UI类别和协议kind；不把储备类误作现金、不凭字段拼写闭合映射。
- 产物：仅`revival/evidence/CURRENCY_RESEARCH.md`。
- 验证：两张任务表原包CRC/长度/BXML与目录全量一致；全表字段0/非0统计；后继ID查找；字符串原包CRC与文本；三个原生消息RTTI/构造/编解码/handler局部静态追踪；官方端游来源核对。
- 未验证：任务字段到钱包槽完整因果链、币种可交易性全部规则、元宝两个字段顺序、货币codec执行/客户端显示、实际奖励到账。未启动/注入/发包/操作手动测试现场或执行玩法回归。

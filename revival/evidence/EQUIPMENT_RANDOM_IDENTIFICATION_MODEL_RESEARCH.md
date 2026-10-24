# 普通六槽随机鉴定：非空附加属性与完整结果模型研究

2026-10-24；本地1.6.1端游 / 网络版本601。第三批只读研究，承接 `NPC_IDENTIFICATION_SOURCE_RESEARCH.md` 与 `EQUIPMENT_IDENTIFICATION_RESULT_SOURCE.md`。本批推进非空随机结果所需模型，不以clean状态翻转代替随机鉴定。

结论：普通完整详情中的附加属性已闭合为**有序三元组序列**，三项分别进入原客户端的属性修饰ID、数值和精练次数相关消费；原内部map的key是0起序号，根本没有在wire传入。非空原完整parser、实际UI调用参数及精练次数上限分支均实际执行成功。随机条数/类型/数值/品质分布与原服评分生成仍未知，可交主策按本页完整结果Seam集中补全；不能继续仅扩identified布尔字段。

## 本批方法、输入与实际产物

已读research、codebase-design技能以及 `ARCHITECTURE.md`、`DESIGN_AUTHORITY.md`，复读前两份报告、现 `equipment_detail` 及原完整parser研究。research落实为原包CRC/原指令/官方端游原页逐项追源；codebase-design落实为将完整结果生成藏在一个纯Module的单一Interface，角色事务与连接投递继续各归已有Owner，避免把抽样、映射和评分分散到NPC、Inventory、人物属性三处。

新增可复跑程序 `revival/research_equipment_random_identification.py`，新增结果 `evidence/equipment-random-identification-native.json`，以及本文。没有修改任何既有研究输入、生产、政策、共享入口或不可变发布。无游戏进程/GUI/网络游戏连接、真实DB、真人操作或真实战斗。

原image SHA256：`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。本批JSON记录6个输入程序SHA，开始和结束逐个重算相等，含新探针自身；其他写者可后续继续修改它们，验收应以JSON固定hash为准。

## 1. 原wire到真实存储，已验证非空

来源状态 `client_verified`，证据是原 `EquipObject` 构造 `0x107cf80` 与完整详情解析 `0x107d960` 到自然返回 `0x107fd97`，不是Python自造decoder的回环。

在基础map之后，原 `0x107e0d9..0x107e1a9` 读取一个大端signed32数量；`0x107e210..0x107e3b5` 每轮读取三个大端signed32。wire形式为：

```text
BE32 count
repeat count:
    BE32 modifier_id
    BE32 value
    BE32 refinement_count_related
```

`0x107e374..0x107e3ac` 使用本地循环序号（从0开始）调用原 `0x107af50`，将三值依次写入其返回记录的+0/+4/+8。存储是 `EquipObject+0x8c` 的树，head在+0x90、count在+0x94；节点key为ordinal，节点+0x10/+0x14/+0x18为三个值。**不要编码额外ordinal，不要把modifier_id当map key，不要按modifier_id排序或去重。**

本批六槽各执行三条非空输入：`[(11,7,0),(81,9,3),(11,-3,1)]`。原存储实际为 `0→(11,7,0)、1→(81,9,3)、2→(11,-3,1)`，两个11分别保留，顺序保持。再用单条 `(141,19,0)` 重解析同一个原对象，实际旧树被原程序清除，只剩ordinal0新记录；不是宿主替换内存。

六个真实模板：40100、42000、43000、44000、45000、46000。基础map采用既有原parser研究的明确payload fixture `(120,37)/(140,21)`，用于验证原生容器，**不是这些模板原服实际基础属性或本次随机配方**。原type/prefix颜色帽/阈值等配置Adapter与既有完整parser相同；新增三元组全为明确实验输入，并非从真实角色取得。

另做四条 `(11,1,0)/(21,2,0)/(31,3,0)/(41,4,0)`，完整原parser也接受并保存ordinal0..3。因此原wire解析器没有在这里把条数硬限为3。极端 `(0,INT32_MIN,-1)/(INT32_MAX,INT32_MAX,INT32_MAX)` 也被接受，证明**编解码可表达范围不是业务合法范围**；主策与领域Module必须显式约束ID、条数、数值、计数器。截断在首条第三个整数前，原decoder实际拒绝。

## 2. 三项的真实原消费

### 属性ID与数值：已闭合到原描述器

`0x1335e5b..0x1335e6d` 从真实三元组树节点读取+0x10/+0x14，经原调用指令把二者传给描述器 `0x12fa810`，另外两个flag为0。本批对六槽×3条共18次执行该原调用片段，在真实描述器入口观察到精确 `(modifier_id,value,0,0)`，未以host Adapter构造这一步参数。

原描述器 `0x12fa87a..0x12fa938` 按modifier的十位分组，lookup `cattributedesconfig`，然后用原行numid/percentid判定平值/百分比，再按value符号选择正/负描述。已直接复核原XML字段落位：numid→row+0x20（`0x86778d`）、percentid→+0x94（`0x8678b7`）、平值正/负描述→+0x5c/+0x78、百分比正/负描述→+0x98/+0xb4。不是将字段名猜测为数值语义。

新增10次原描述选择oracle：

| modifier / value | 原查表id | 原选择结果 |
| --- | --- | --- |
| 11 / +7、-7 | 10 | 体质正/负平值描述 |
| 12 / +7 | 10 | percentpositivedes，原行该文本为空；不得伪造为已恢复百分比体质 |
| 81 / +9、-9 | 80 | 外功伤害正/负平值描述 |
| 82 / +9 | 80 | 外功伤害百分比描述 |
| 141 / +19 | 140 | 生命平值描述 |
| 142 / +19 | 140 | 生命百分比描述 |
| 811 / +11 | 810 | 内功伤害平值描述 |
| 812 / +11 | 810 | 内功伤害百分比描述 |

此oracle执行原ID分组、lookup参数传递、平值/百分比和符号分支；配置lookup与UTF16内存为Adapter，提供本轮CRC核过的原表行/原文本。停止在数值字符串替换前；**没有以字符串显示证明人物最终属性加法、百分比单位/叠加顺序或五维派生公式**。

原表另有11/21/31/41/51分别对应体质/内力/力量/耐力/敏捷；这给未来附加五维提供真实修饰ID候选，不证明每部位/每等级都可抽到这些类型。已有普通六槽基础投影只接受已设计的clean基础形状；本批不擅扩其政策。

### 第三个值：精练次数相关，已执行实际比较

原 `0x131b8ad..0x131b8d8` 从当前原对象取得prefix，查 `cequipprefixconfig` 的+0x24，再按ordinal取真实附加记录，用其第三值与该上限比较。`0x86aeea..0x86af13` 已静态闭合+0x24来自原字段字面 `maxrefinetime`。由实际原消费可命名为精练次数相关字段，不能把第三值当另一个加成数值或独立属性ID。

本批使用原prefix1实际 `maxrefinetime=3`，六槽×3条共18次原分支：第三值0/3/1分别进入 `below_cap / at_cap / below_cap`。配置Adapter提供原表上限，树lookup和有符号比较是原指令；没有执行精练动作、扣款或成长。鉴定新结果是否必须初始0、是否允许负值、精练如何改变第二值，仍需后续业务政策/原证据。

另静态观察 `0x1335db9` 在此UI区域只展示前三个位置。这是**局部UI呈现约束**，原parser已实证接受4条，不能据此宣布原服普通鉴定绝对最多3条。主策若采用0..3，应标designed并考虑该UI约束。

## 3. 评分、品质与人物属性链的实际闭合程度

| 链路 | 状态 | 本批结论与限制 |
| --- | --- | --- |
| modifier→原描述类别 | client_verified | 非空值真实进入原描述器，表中numid/percentid及正负分支实际运行，见10例 |
| modifier→人物最终属性 | 部分既有client_verified；新实例合成仍unknown | 已有11种平值numid与人物总key映射依据仍见ORDINARY_EQUIPMENT_ATTRIBUTE_RESEARCH及v2政策；本批没有原附加值→最终总属性算法。新增五维需进入角色派生重算；百分比需单独定义顺序、基数与取整，不能平加或丢弃 |
| prefix→颜色帽 | 既有client_verified，本批原表复验 | 五个普通品质的颜色帽3/4/5/6/6；prefix第6行不自动进入普通随机池 |
| score→颜色 | 既有client_verified，本批非空回归 | 原完整parser仍使用接收score与模板scorecolor，再由品质帽限制；改变附加列表而保持接收score0，原返回score仍0、color仍1 |
| 附加值→原初始score | unknown | 完整parser没有因为非空列表自行计算初始score；原server必须另供。当前score0不能拿来生成任意强度随机装备后宣称原版评分正确 |
| cequipscoreconfig实际用途 | 静态client_verified片段；完整算法未验 | 原表实现vtable2255b74在D41e2a装到配置管理器+4e0，原getter89d580，消费者12f62a5/6425/67b5/6bef/6dab/7173/74a9。12f6173取得装备部位索引，12f62c7按其索引取effectscore字符串，12f6300取分号序列元素2，后续原整数乘当前修饰值累加。12f760d后出现除100、加0.5、转整数及score增量写回。该区域还含强化/宝石/特殊kind分支，不是已确认的初始鉴定生成路径；本批未把这些数值代入host函数冒充原评分oracle |
| ceffecttype / cequipjichu | client_verified资源，普通鉴定消费unknown | 表确有评分与基础数值候选，仍没有普通鉴定生成、分布及基础上下限调用链。ceffecttype不能因也叫effectscore就与cequipscoreconfig互换；cequipjichu的48行不能直接当随机上下限 |

本批没有从advanced/refine/repair表借任何随机概率。非空容器及描述展示成功不等于原角色总属性、原初始评分或原平衡已恢复。

## 4. 原包完整性与固定证据

本批重新读PFS原条目，`PfsArchive.read` 全部核本地/中央记录、解压完整性、原长度及CRC；再BXML解码。不是只读catalog JSON。字段与具体SHA全部在新JSON `sources` 中。

| 原item表 | 行数 | 原展开字节 | CRC32 |
| --- | --- | --- | --- |
| cattributedesconfig | 195 | 19508 | 56e2ca7e |
| cequipprefixconfig | 6 | 291 | c8592725 |
| cequipscoreconfig | 36 | 10245 | 77c46054 |
| ceffecttype | 58 | 7605 | 1cb8e9e5 |
| cequipjichu | 48 | 8007 | 3c3c1af8 |
| cequipeffect | 1521 | 467441 | e354a76d |
| citemattr | 12280 | 4096369 | a3add081 |

本轮6个程序输入包括 `research_equipment_detail_full.py`、`research_npc_submenu.py`、`pfs.py`、`bxml.py`、`native_inspect.py` 和新增探针，精确SHA见新JSON。实际程序输出为：六槽非空完整parser、18次原UI传参、18次原cap分支、六次替换解析、4条序列、极端wire取值、截断拒绝和10次描述分支全部通过。不得把这些子检查相加为独立完整玩法场景数。

## 5. 本批针对性官方端游检索

本批再次使用web检索官方原站，查询组合为鉴定/附加属性/条数/三条/3条/品质/基础范围/属性上限/随机。使用同款端游原页，不以手游/2、坐骑装备、装备灵魂或后期化境神兵洗炼作为普通六槽鉴定证据。

- [2013-08-30《装备系统解析》](https://sdxl.wanmei.com/news/gamenews/20130830/149369.shtml)：`guide_supported`，支持附加属性鉴定时可能随机产生，重铸改变附加属性、精练强化附加属性。没有精确概率、条数池、部位等级池或数值范围。该文章的历史端游版本未精确标成1.6.1。
- [《装备打造》资料页](https://sdxl.wanmei.com/info/newplayer/50to69/20120705/132376.shtml)：URL日期2012-07-05，无可见发布日期/精确客户端版本。`guide_supported`，支持同等级装备属性可异、存在该等级允许范围，品质五档与颜色上限、评分受基础/附加/宝石/无双等影响。没有具体允许范围或品质生成权重。
- [2012-09-19公测说明](https://sdxl.wanmei.com/news/gamenews/20120919/135556.shtml)：`guide_supported`，明确区分冲星与改变/强化附加属性的重铸/精炼；这支持字段用途分离，不提供鉴定分布或鉴定币种。
- [2013-09-12坐骑装备资料](https://sdxl.wanmei.com/info/system/zuoqixitong/20130912/150274.shtml)检索会出现“初始一条、最多五条”，但对象是项圈/鞍部/饰带并作用宠物，**明确排除普通六槽结论**。

官方当前资料中的普通鉴定条数精确上限、各部位附加类型池、基础与附加数值区间、品质权重仍unknown。未查到不等于原式不存在；主策可以按既有授权补designed，而无需把恢复工作停在只读查询/clean翻标志。

## 6. 可承载完整随机结果的Module与Seam建议

以下为 `inferred` 的实现需求/设计建议，未发布政策、未实现domain。按codebase-design，一个深Module隐藏全部资格、抽样顺序、基础/附加生成、评分与范围校验；调用方不各抄概率表或过滤未知字段。

建议单一纯Interface的概念形状为 `plan_identification(frozen_input, rules, draws) → IdentificationPlan`。Interface须包括真实资格来源、原详情/Inventory版本、配方版本、随机输入预算、失败模式和输出完整性，不能只有一个改flag函数。配置启动冻结，参数与draws显式注入；Implementation纯计算并返回不可变完整结果，不在此开DB或访问连接。随机来源在生产/受控验证有真实不同Adapter，不为每个字段再造转发层。

为完整随机普通鉴定必须新增/扩展的持久模型：

1. **完整结果身份**：详情schema版本、generation/identification规则版本、来源或稳定生成键、item_key/template/当前详情版本、结果已生成/已公开状态。结果只生成一次；paid恢复读当前，不重复抽样、改钱或把已存结果换一套。
2. **基础属性与品质**：保留raw modifier/value有序或唯一性规则、基础值区间来源、prefix_quality、原server需提供的score；颜色是原模板阈值+品质帽的派生值，须与EquipmentCondition一致。现基础模板值可作设计基准，不能冒称原随机上下限。
3. **附加属性序列**：`[(modifier_id, value, refinement_count), ...]` 保留顺序/ordinal；不能用modifier键dict吞掉重复项。条数最大值、重复类型规则、负值许可、百分比许可、各部位/等级池及数值范围由主策给明确designed政策。首次计数0可以作为设计候选，须明写，不能由当前空clean容器推为原事实。
4. **保留未来字段**：现clean codec全部空/0的强化、宝石、无双和高级扩展仍有独立状态；随机普通模型不能默默清除已有未知修饰。新生成普通结果可明示这些功能未开启，旧未知详情应拒绝并等待显式迁移。
5. **人物属性贡献**：把基础与附加分别映射后在同一可信当前装备快照重算总值。五维影响派生、HP/MP上限、加强封印/封印抗性及百分比基线各有能力/版本条件；未支持项不得隐藏成无效果装备。需要扩现投影的严格clean限制，并给真实人物最终资源过渡，与库存详情版本一起提交。
6. **商业事务与投递**：角色Owner受理当前NPC/租约/Proof及单次命令；统一Inventory公开CAS、费用、结果快照、规则来源、凭据/版本和所需资源过渡在一个有界I/O事务提交；编码检查先于最终提交。连接Owner顺序投递原完整详情与钱包绝对值，失败/重试以持久结果恢复，不借全服锁/全服队列保护抽样。

主策现在可以据事实作完整配方裁定的最小未知集合：条数及概率、属性池与重复规则、各部位/等级基础与附加值分布、品质分布、评分初始公式与合法有界范围、首次计数/无双是否纳入，以及生成时点。必须一套版本化规则同时覆盖这些变量，避免只给属性池就号称完整随机鉴定。

## 未验证范围

本批没有证明原服随机算法/概率、完整初始评分公式、所有UI窗口的条数上限、百分比或五维的原服务端合成、特殊kind/神兵、强化/精练动作及费用、原界面渲染或真实鉴定。原指令允许某些字节与真实业务可接受是不同命题。已有收费固定基础鉴定政策与本批未来随机模型互相独立；本报告不能自动扩大其权限或影响已部署行为。

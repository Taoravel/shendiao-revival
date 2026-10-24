# 装备鉴定结果与报价level来源：第二轮只读研究

日期：2026-10-24。对象：本地1.6.1端游，原映射image SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

普通装备报价的level字段来源现已闭合至原CItemAttr.level；本批新增6组原指令组合验证。另外20组原getter边界验证发现，特殊kind的覆盖值条件是“非0且有符号值≤1000”，原指令没有“>0”检查。普通鉴定的随机配方仍未闭合；本批没有设计任何概率或生产行为。

## 方法、输入与边界

沿用并重读 `D:/User/Documents/Codex/.codex/skills/research/SKILL.md`。作为根任务的后台研究，只追第一方本地资源、原指令及已读取的历史端游官方原文；方法实际影响是把字段复制、UI显示、数值表存在和完整服务端公式分开举证。

阅读 `research_npc_identification.py`、`research_equipment_identification.py`、`research_equipment_detail.py`、`research_equipment_detail_full.py`、`equipment_detail.py`、`design/equipment-detail-v1.json`、`ORDINARY_EQUIPMENT_V2_INTEGRATION.md` 等现有输入。直接读取 `artres/config.pfs`，没有使用解包XML代替本轮CRC检查。原生实验均是Unicorn执行既有原image代码，只在独立内存填入明确fixture和Adapter；未启动客户端、GUI、监听、网络请求或真实战斗，未读写存档DB。仅新增本文，不改既有研究文件、政策或生产代码。

## 1. 普通报价level已闭合

以下均为 `client_verified`，指原客户端消费与字段来源，不是原服务端授权或扣款规则：

1. 原字符串 `0x22569b0` 内容为 `knight.gsp.item.CItemAttr`，同区域原行解析函数 `0x86e880` 依次读id、itemtypeid、name、level等字段。`0x86e95a` 压入UTF16字面值 `level`（`0x2251a44`），`0x86e97a` 调用原XML整数读取器 `0x409ce0`，`0x86e983` 将结果存到行对象 `row+0x24`。这里由实际字段字面量到存储指令建立语义，不是因偏移看起来像等级而命名。
2. 原包装初始化 `0x107fe20` 中，`0x107fe61` 取得CItemAttr管理器；用输入bean的template（`+8`）在 `0x107fe78` 调用虚表lookup，返回行；`0x107fe7b` 构造目的地址 `wrapper+4`，`0x107fe7e` 调用原复制 `0x1072890`。
3. 原复制 `0x10728af` 读取 `row+0x24`，`0x10728b2` 写到目的结构 `+0x24`，因此是 `wrapper+0x28`。同一复制同时把row id/kind映射至wrapper+4/+8。
4. 已有包装的真实刷新 `0x1072aa0` 从 `wrapper[0]->+0xc` 获取当前template，经同一CItemAttr lookup后，在 `0x1072ab8` 传 `wrapper+4` 调用同一完整原复制。普通getter `0x1074d3b` 最终读取 `wrapper+0x28`，而NPC原选择/报价 `0x16882b6`、`0x16882d5` 调用此getter。

本批实际执行了6组组合oracle：原XML `level` 字段存储片段 → 完整原包装刷新/复制 → 完整原getter。六槽各取真实50级模板，结果如下：

| 槽位 | template | 原itemtypeid | PFS level | 原row+24 | 原wrapper+28 | 原getter返回 |
| --- | --- | --- | --- | --- | --- | --- |
| 武器0 | 40105 | 1288 / 0x508 | 50 | 50 | 50 | 50 |
| 护腕1 | 42010 | 280 / 0x118 | 50 | 50 | 50 | 50 |
| 项链2 | 43005 | 40 / 0x28 | 50 | 50 | 50 | 50 |
| 衣服3 | 44010 | 312 / 0x138 | 50 | 50 | 50 | 50 |
| 腰带4 | 45005 | 72 / 0x48 | 50 | 50 | 50 | 50 |
| 鞋5 | 46005 | 88 / 0x58 | 50 | 50 | 50 | 50 |

Adapter明细：XML整数读取器返回本轮CRC核过的对应PFS行level；配置lookup返回对应行；UTF16构造/析构/复制使用运行库替身。实际执行原字段存储、完整复制、当前template读取及lookup参数传递、原getter。XML树构建/缓存初始化、真实网络物品入库与整个 `0x107fe20` 分配分支没有动态执行；初始化路径为原指令静态闭合，刷新路径动态执行。6组全是50级样例，不冒称全模板矩阵。

### 特殊kind边界的纠正

完整kind为 `0x1c8/0x2c8/0x3c8` 时，`0x1074d28..0x1074d39` 先取 `wrapper[0]+0xd0`，原代码为零值回退、与1000进行有符号比较，大于1000回退，其余返回。原代码没有正数判定。

本批20组原getter实测：普通 `0x508` 和三个特殊kind，各输入动态值 `0/1/1000/1001/-1`，wrapper基准level均50。普通始终50；三个特殊kind依次返回 `50/1/1000/50/-1`，全部符合原指令。因此既有NPC研究里“0<value<=1000”的proof_limits文字过强，应由所属窗口修正文案。本文未改它。

这不是允许服务器接受负等级的依据。特殊kind真实 `+0xd0` 的来源、意义、生命周期与鉴定资格仍unknown；本轮普通确定性子集应排除这些kind，或另闭合其详情字段与政策。普通报价应精确查 `cnpcidentifyneedmoneyconfig` 的原键，不插值，不把不存在的51降档到50。

## 2. 原PFS候选表与完整性

实际通过 `PfsArchive.read` 读取并BXML解码了全部160张 `knight.gsp.item.*.xml` 表。读取器逐条核中央/本地记录、长度、解压终止和CRC；本轮160张均成功。另枚举其他命名空间，相关候选仅发现effect侧 `cequipzhuzaoskillmapping` 与skill侧 `cequipskill`；名字所涉无双不等于普通随机鉴定，本轮未拿它们建配方。

下表CRC均直接来自原PFS且本轮读取通过。`client_verified`仅用于已验证的资源及原消费位置；“未闭合”表示未取得鉴定生成调用链，不等于表没有任何用途。

| 原item表 | 行数 / CRC32 | 关键字段或实例 | 原消费证据与可用边界 |
| --- | --- | --- | --- |
| citemattr | 12280 / a3add081 | id、itemtypeid、level；六样例见上 | 本批闭合level到普通报价getter；不证明物品实例的鉴定结果 |
| cequipeffect | 1521 / e354a76d | baseEffectType/baseEffect、scorecolor；40100原基础(81,20)/(811,20)/(1231,6)，阈值292/364/484/584/686 | 既有原完整详情parser将服务器给的基础map消费到EquipObject+80；原107dd14后的阈值比较算颜色，本批也复读原指令。将表中基础值作为新clean实例生成值是既有designed，不能当原服随机抽样范围 |
| cequipjichu | 48 / 3c3c1af8 | effecttype/effect；1060对应81/811/1231与380/380/146 | 本批只证表内容；未闭合普通鉴定调用，不猜id=部位×某数+等级，也不推为随机上下限 |
| cequipscoreconfig | 36 / 77c46054 | effectname、effectscore多行分号数组；id11“体质” | 只证评分候选数值；未闭合索引、单位、属性量→评分公式，不把数组当鉴定概率 |
| ceffecttype | 58 / 1cb8e9e5 | effectname/effectscore；id1“力量” | 只证另一评分/属性描述候选；未证明它与上一表的职责和鉴定结果生成关系 |
| cattributedesconfig | 195 / 56e2ca7e | numid/percentid、roleattribute、正负描述、numbasevalue | 属性显示/映射候选，不是概率/范围表；不能因有百分比描述就启用未恢复百分比修饰 |
| cequipprefixconfig | 6 / c8592725 | id1..5普通/强化/无瑕/卓越/完美，颜色帽3/4/5/6/6；第6行无普通名字 | 既有原parser/颜色oracle证明prefix颜色上限消费；没有证明鉴定产生各品质的概率。第6行不能纳入普通五档随机池 |
| cequipcolorconfig | 8 / c1a5b170 | colorname/baseattradd/intensitytime/luckynum等 | 颜色及强化相关候选；未得普通鉴定生成消费证据；阈值颜色来自前述cequipeffect+prefix帽，不据luckynum制造概率 |
| cnpcidentifyneedmoneyconfig | 16 / e80deb44 | id1、10…150与needmoney | 既有NPC原UI消费16行；本轮补普通等级真实字段来源。币种及原服务端结算仍unknown |
| cmakeidentifyitemconfig | 9 / a6720929 | needequip/needgem/outputproduct/outputcount，50行产37226×5 | 制作鉴定道具的候选，不是普通装备属性生成配方；没有作为鉴定随机结果使用 |
| cequipmakeinfo | 238 / becb8d5f | type/level/tuzhiid/hantieid及数量 | 打造输入/产物候选；不等于鉴定概率；不能把制造材料配方当结果生成模型 |
| cequipadvancedconfig | 5 / 9350fc25 | weight1、weight2、base、money、luckynum；第一行weight1=15、weight2=15/23/45/100 | 确有权重字样，未闭合普通鉴定消费，不能搬作附加条数/品质概率；需独立核对应高级玩法 |
| cequiprefineconfig | 1159 / 1a9af698 | chongzhucost、jingliancost | 重铸/精练成本候选，不是普通鉴定价格；本轮不混用 |
| cequipmakeupconfig | 1159 / fe0c5c9f | quencheffect、各种钻、gemrewards等 | 既有原详情parser在零强化分支也做lookup但不取这些进阶值；不证明鉴定抽样或强化完整公式 |

四个核心表原解包字节SHA256：

- citemattr：`974a3b38049c5f5f7cdae418718ffadd2741d373a5846a40fb71289af25e726f`
- cequipeffect：`8ef1aacae8d016f875a37a8cf907b16a077b89fa522a87e349dd54d320572fe8`
- cequipscoreconfig：`c370650594da413d8870204e0820dab958f34cd9b9386f6102a54f0ba43be683`
- cequipprefixconfig：`3b36fed5bf4e62e41ceec422d902f8479bdcc487e82351750168ba130805e7ae`

字段筛查覆盖rand/prob/poss/min/max/add/base/weight等，并人工查看装备相关候选。出现的probability是 `cequiprepairsuccposs` 的修理表，不得用于鉴定。未发现足以闭合“普通鉴定：抽条数→抽属性→抽数值→品质/评分”的原表组合或原消费算法。仅扫描客户端包无法证明服务端没有独立配置。

## 3. 两种恢复范围分别缺什么

### 已有干净基线的受限揭示

已有 `EquipmentDetail` 只持久化 identified、prefix_quality、score、base_properties，`DetailRules` 的当前显式clean生成策略为identified1/prefix1/score0，进阶容器空。既有六槽原完整parser实验证明，同一已供应干净payload仅改首个BE32的0/1，两种状态都被原parser接受且其余已供应基础map完全相同。此结论是 `client_verified` 的序列化可表达性，不能证明原服都是先有属性再揭示。

因此最小模型扩展（`inferred`的实现需求，非本轮政策）：

- 必须有明确的新来源/鉴定policy或单独资格记录，可信地证明该未鉴定实例的完整结果已经固定且属于确定性clean子集；现有identified1生成默认值不能悄悄改为0，不能靠template给未知旧实例补clean。
- 持久化一次鉴定结果/资产命令凭据与来源版本，受理时核同一角色、同一物品key、当前详情版本和identified0；付费重试不再次扣款或重新生成结果。
- 转为identified1时保持原基础、品质、评分、耐久、绑定及未涉及字段；事务中写详情/余额/凭据/库存版本，先完成原生刷新可编码检查。已穿装备是否受理及最终属性/HPMP过渡走既有角色Owner接口。
- 原报价金额复用精确表、普通level来源可用本轮结论；扣现金/绑银、NPC服务关联、资格与绑定处理仍由主策划designed。纯确定性子集也不能声称完整原版随机鉴定。

### 完整随机鉴定

[官方2013-08-30装备系统解析](https://sdxl.wanmei.com/news/gamenews/20130830/149369.shtml)支持鉴定时可能生成附加属性，属于 `guide_supported`，精确适配1.6.1及原生成时点仍unknown。本批未再次访问网络，沿用第一轮已直接读取及校日期的官方原页；完整来源/年代冲突见 `NPC_IDENTIFICATION_SOURCE_RESEARCH.md`。

完整恢复需额外模型/来源：附加属性容器及其原key/value语义、品质/基础范围、条数与类型/数值联合分布、重复属性规则、部位/等级/模板资格、是否出现无双及对应独立模型、品质和评分计算、绑定规则；随机结果与seed/配方版本或完整结果快照一次持久化以保证重试。客户端已有追加容器/扩展位置不等于这些业务语义与原服概率已知；现有clean codec将它们编码为空，不足以表达完整随机结果。

没有这些来源时，应由主策划给集中、版本化的designed配方，或明确先只支持上述确定性子集；本研究不填概率、不自动开启高级/神兵/重铸/精练能力，不对旧角色或旧装备做迁移。

## 本批验证与剩余卡点

- 实际验证：PFS全部160张item表读取/CRC/BXML成功；原level字段、行复制、包装刷新与普通getter组合6组成功；原getter普通/特殊边界20组成功；读取并区分既有详情codec与玩法模型。
- 具体进展：此前“普通模板等级是否真的进入NPC报价”已可关闭字段来源缺口；特殊kind需要修正文案并保留独立边界。没有因此关闭原服务端扣款、随机结果、服务权限或GUI验收缺口。
- 精确未知：特殊bean+d0的真实来源；普通鉴定追加属性分布与抽样算法；评分候选数组的原索引/单位/消费链；鉴定是否先生成隐藏值还是在确认时取样；普通绑定/币种规则。上述不是被零值替代的字段。
- 新产物：仅本文。未保存临时探针文件、未改旧研究输入；26个原生实验的入口、Adapters、fixture和实际结果均在本文逐项记录。完整商业事务/共享接线/部署/原生GUI不在本批验证范围。

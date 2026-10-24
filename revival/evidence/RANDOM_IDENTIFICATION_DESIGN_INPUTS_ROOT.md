# 完整随机普通六槽鉴定：主策划决策输入

2026-10-24；本地1.6.1端游 / 网络版本601。本文件仅是研究输入，不新增政策、生成器、迁移、收费接线或发布。结论中的“现有实现”指下列SHA固定的工作区源码；不把它冒称当前运行服选择。

## 方法与核心结论

已读取根AGENTS、ARCHITECTURE、DESIGN_AUTHORITY、GLOSSARY及research、codebase-design技能。research实际用于直接重读原config.pfs六个成员，逐个验证PFS头/目录、解压长度与CRC后BXML解码，并打开两篇同款端游官方原页；codebase-design实际用于将结果生成、人物属性投影和付费事务分成三个已有归属的Interface，避免把候选权重抄进NPC、Inventory和人物计算三处。本批作为root的后台研究执行，未再嵌套委派。

最重要的范围差异是：原包普通六槽非神兵的1038模板最高level为130；**不存在真实150级六槽样本**，citemattr中普通六槽非神兵level>=140数量为0，全部装备低四位8的level150条目也为0。鉴定费用表有150档不能证明装备模板覆盖150。973是平值基础修饰可映射的模板数，其中212含待恢复套装，761才是不受套装语义阻碍的平值模板；仍需当前实例、角色资格与资源状态检查，不能把761称为本批已上线。

原鉴定条数/类型/数值/品质权重、初始score公式及生成时点仍未知；本文件没有补造它们，供root依已有授权统一裁定designed。原有完整非空解析证据沿用[随机结果模型研究](D:/神雕侠侣/revival/evidence/EQUIPMENT_RANDOM_IDENTIFICATION_MODEL_RESEARCH.md:15)与其固定native JSON，本批未重复长模拟或改写旧证据。

## 1. 当前真正存在的政策与模型

| 文件 | 当前内容及限制 | 来源状态 |
| --- | --- | --- |
| [equipment-detail-v1.json](D:/神雕侠侣/revival/design/equipment-detail-v1.json:3) | 新建clean基础；identified1、prefix1、score0、原cequipeffect基础值；空附加/宝石/进阶容器 | 生成方式designed，原字段/表值client_verified |
| [role-equipment-v1.json](D:/神雕侠侣/revival/design/role-equipment-v1.json) | 旧师承武器投影，独立政策，不是普通全六槽随机模型 | designed |
| [role-equipment-v2.json](D:/神雕侠侣/revival/design/role-equipment-v2.json:4) | 973个非空平值模板，212套装延后；实例仍限精确原基础/prefix1/score0/color1 | 映射client_verified，组合/资格执行designed |
| [equipment-condition-v1.json](D:/神雕侠侣/revival/design/equipment-condition-v1.json) | 文件名v1、内部revision为condition.2；100/100、color1的新建基线；颜色并非品质 | baseline designed；色源有native证据 |
| [npc-equipment-identification-v1.json](D:/神雕侠侣/revival/design/npc-equipment-identification-v1.json:23) | 已有完整固定clean未鉴定结果，仅0→1揭示；费用/事务单独规定，不产生附加属性 | 固定子集designed，费用/level源client_verified |
| [role-attributes-v1.json](D:/神雕侠侣/revival/design/role-attributes-v1.json) | 五维成长增量按原系数的设计组合；物攻系数另有设计；装备修饰不在该政策内 | designed_composition_using_client_coefficients |

[equipment_detail.py:16](D:/神雕侠侣/revival/equipment_detail.py:16)的持久DTO仅有identified/prefix_quality/score/base_properties四项，[encode:164](D:/神雕侠侣/revival/equipment_detail.py:164)仍编码空附加容器。当前不能把非空三元组塞入base_properties或偷偷改DTO含义来冒充完整随机结果。

[role_equipment.py:161](D:/神雕侠侣/revival/role_equipment.py:161)显式装载普通v2；[投影:293](D:/神雕侠侣/revival/role_equipment.py:293)仍拒非零suiting及非clean实例。即使新随机详情能显示，人物最终属性仍须同步扩展这一严格契约，不能产生“看得见但无效”的属性。

## 2. 客户端模板覆盖与等级

client_verified资源口径：cequipeffect与citemattr按原id交集；itemtypeid低4位为8，slot=(itemtypeid>>4)&15在0..5，排除cgodweapon原85个ID。原kind必须保留完整值；不能只存slot后遗失武器子类/特殊分派。下节示例kind分别为1288/280/40/312/72/88，它们是具体行值，不是所有模板的唯一kind白名单。来源为本批原包重读，筛选与[既有全量研究](D:/神雕侠侣/revival/evidence/ORDINARY_EQUIPMENT_ATTRIBUTE_RESEARCH.md:16)及现DetailRules/普通v2一致。

| 原level | 全部六槽模板 | 非空且11类flat可映射 | 其中suiting=0 |
| ---: | ---: | ---: | ---: |
| 1 | 55 | 52 | 52 |
| 10 | 65 | 55 | 55 |
| 16 | 1 | 1 | 1 |
| 18 | 1 | 1 | 1 |
| 20 | 60 | 60 | 60 |
| 30 | 85 | 60 | 60 |
| 40 | 120 | 120 | 64 |
| 50 | 75 | 65 | 49 |
| 60 | 131 | 130 | 122 |
| 70 | 109 | 109 | 53 |
| 80 | 77 | 61 | 53 |
| 90 | 119 | 119 | 51 |
| 100 | 45 | 45 | 45 |
| 110 | 17 | 17 | 17 |
| 120 | 61 | 61 | 61 |
| 130 | 17 | 17 | 17 |
| 140 | 0 | 0 | 0 |
| 150 | 0 | 0 | 0 |
| 合计已有等级 | 1038 | 973 | 761 |

1038中另有64个缺基础列表，1个49192“残铁甲”原修饰102:72是百分比；不能当零效果或改为101。原level16、18各一件，现鉴定费用只支持精确1/10…150档，不能以十位下取整或角色等级替代。citemattr.level是报价来源，needLevel是另一字段；例如49192为level60、needLevel10，不应强制二者相等。client_verified字段差异见[EQUIPMENT_IDENTIFICATION_RESULT_SOURCE](D:/神雕侠侣/revival/evidence/EQUIPMENT_IDENTIFICATION_RESULT_SOURCE.md:15)。

973包含原givetype活动/奖励等条目，并不等于全部正常打造/掉落池。上表仅是资源与平值映射覆盖，完整可生产模板池及后续更高等级模板须root另定；本批不外推140/150数值。

## 3. 真实六槽样例与颜色阈值

以下全部直接取原citemattr/cequipeffect同id的记录，未由id规律猜算；50/100/130每槽选该等级有非空基础列表的最小id。原1级指定六件及下表所有样例needLevel均等于所列level，suiting均为0。基础列保留raw modifier:value，五个scorecolor顺序为原表序列；**基础表值不是原服随机上下限**。无150样例，额外给出真实最高130级用于裁定边界。

| 原level | slot | 原id/名称 | 完整itemtypeid | 基础raw:value | 原scorecolor五阈值 |
| ---: | --- | --- | ---: | --- | --- |
| 1 | 武器 | 40100 铁剑 | 1288 | 81:20 / 811:20 / 1231:6 | 292/364/484/584/686 |
| 1 | 护腕 | 42000 蓝布腕 | 280 | 1241:6 / 101:13 / 151:10 | 185/242/348/442/538 |
| 1 | 项链 | 43000 长命锁 | 40 | 111:20 / 821:5 | 128/178/276/367/459 |
| 1 | 衣服 | 44000 青布衣 | 312 | 101:33 / 141:4 | 182/239/344/438/534 |
| 1 | 腰带 | 45000 百草结 | 72 | 141:16 / 821:3 | 95/141/234/324/415 |
| 1 | 鞋 | 46000 灰布鞋 | 88 | 101:4 / 821:2 / 131:4 / 121:10 | 152/204/306/398/492 |
| 50 | 武器 | 40105 紫薇软剑 | 1288 | 81:320 / 811:320 / 1231:123 | 4125/4709/5364/5647/5986 |
| 50 | 护腕 | 42010 金蚕丝腕 | 280 | 1241:123 / 101:91 / 151:110 | 1864/2149/2493/2667/2870 |
| 50 | 项链 | 43005 琥珀丝链 | 40 | 111:370 / 821:72 | 1261/1466/1726/1871/2038 |
| 50 | 衣服 | 44010 青云战袍 | 312 | 101:231 / 141:44 | 974/1141/1362/1493/1643 |
| 50 | 腰带 | 45005 鸳鸯缎带 | 72 | 141:176 / 821:46 | 607/726/896/1009/1137 |
| 50 | 鞋 | 46005 勇武军靴 | 88 | 101:28 / 821:12 / 131:14 / 121:40 | 508/614/770/879/1001 |
| 100 | 武器 | 40117 湛卢 | 1288 | 81:620 / 811:620 / 1231:240 | 7967/9054/10245/13292/15779 |
| 100 | 护腕 | 42020 武神至尊腕 | 280 | 1241:240 / 101:169 / 151:210 | 3552/4057/4638/6030/7180 |
| 100 | 项链 | 43010 沧海月明珠 | 40 | 111:720 / 821:140 | 2409/2763/3186/4150/4954 |
| 100 | 衣服 | 44020 九天流炎甲 | 312 | 101:429 / 141:84 | 1774/2044/2380/3105/3718 |
| 100 | 腰带 | 45010 晶玉冰饰带 | 72 | 141:336 / 821:90 | 1134/1319/1566/2052/2470 |
| 100 | 鞋 | 46010 方天步云履 | 88 | 101:52 / 821:22 / 131:24 / 121:70 | 872/1023/1234/1621/1960 |
| 130 | 武器 | 40120 闇剑掩日 | 1288 | 81:800 / 811:800 / 1231:310 | 9494/10790/12198/15815/18769 |
| 130 | 护腕 | 42039 九龙纹护臂 | 280 | 1241:310 / 101:216 / 151:270 | 4209/4801/5472/7111/8460 |
| 130 | 项链 | 43023 北斗七星坠 | 40 | 111:930 / 821:180 | 2851/3262/3747/4875/5813 |
| 130 | 衣服 | 44041 不动金刚铠 | 312 | 101:548 / 141:108 | 2085/2395/2774/3616/4322 |
| 130 | 腰带 | 45021 战火龙血染 | 72 | 141:432 / 821:116 | 1331/1542/1817/2376/2853 |
| 130 | 鞋 | 46021 登极寻仙履 | 88 | 101:66 / 821:27 / 131:30 / 121:88 | 999/1166/1395/1830/2207 |

原表每行的定位是成员名+record id（BXML为结构记录，没有可声称的文本物理行号）。源字节/hash见末节；本批没有把样例复制到catalog、政策或生产。

### 品质、颜色和评分应分开

client_verified的cequipprefixconfig行如下，普通5档与官方原文一致；第6行无普通品质名，bestcolortype6、maxrefinetime0，不进入已证普通5档池：

| prefix行id | 原name | bestcolortype颜色帽 | maxrefinetime |
| ---: | --- | ---: | ---: |
| 1 | 普通 | 3 | 3 |
| 2 | 强化 | 4 | 4 |
| 3 | 无瑕 | 5 | 5 |
| 4 | 卓越 | 6 | 6 |
| 5 | 完美 | 6 | 8 |

颜色1..6依次白/绿/蓝/紫/橙/金；普通品质1的帽3是蓝色，不是“品质=颜色=1”。第三个附加整数与精练次数上限比较有原生证据，首次生成是否0仍须designed；特别是完美品质5的maxrefinetime为8，并非颜色帽6。

现[DetailRules.color:87](D:/神雕侠侣/revival/equipment_detail.py:87)按原scorecolor阈值和prefix帽组合，颜色须与EquipmentCondition一致。既有原parser执行支持接收score→颜色、prefix帽限制；不支持把原阈值反推成唯一初始评分公式。[随机模型研究:70](D:/神雕侠侣/revival/evidence/EQUIPMENT_RANDOM_IDENTIFICATION_MODEL_RESEARCH.md:70)明确非空附加并不自行让parser增加score。

本批1038行共5190个阈值，最小76（id49136），最大66062（id40109）。这只是**原颜色阈值数值范围**，不是装备score上限、属性生成上限或随机数范围。当前DTO允许非负signed32 score0..2147483647；原wire是signed32。可确定的单位是服务器供应的整数评分及原阈值比较，不能宣称“1点外攻等于某固定评分”已恢复。新计分公式必须单调、有界、给取整顺序，并用同模板阈值校准；品质帽只是上限，不能与属性强度脱节后独立抽一个颜色。

原cequipscoreconfig确有候选权重，例如行81的某序列400/408/420/432/440/448/460/440；但表还有多部位、多序列及特殊行。既有静态消费包含取部位、分号序列元素2、乘属性值、除100/加0.5等，也混有强化/宝石分支；未闭合到普通初始鉴定评分。本批不指定某列为原初始计分权重，不借ceffecttype同名字替换，不拿高级权重或修理概率当鉴定概率。

## 4. 原修饰ID到最终人物属性

下表client_verified来自cattributedesconfig **真实numid逆索引**及既有原人物getter/入场/刷新链，已与当前[普通v2 flat_mapping](D:/神雕侠侣/revival/design/role-equipment-v2.json:6)逐项一致；不是“raw减1”推断。[原全量研究:58](D:/神雕侠侣/revival/evidence/ORDINARY_EQUIPMENT_ATTRIBUTE_RESEARCH.md:58)给每项VA及原基础值分布。

| raw平值modifier | 人物key / 原类别id | 原name | 同行percentid（本批不启用） |
| ---: | ---: | --- | ---: |
| 81 | 80 | 外功伤害值 | 82 |
| 101 | 100 | 外功防御值 | 102 |
| 111 | 110 | 命中值 | 112 |
| 121 | 120 | 躲闪值 | 122 |
| 131 | 130 | 速度值 | 132 |
| 141 | 140 | 生命最大值 | 142 |
| 151 | 150 | 真气最大值 | 152 |
| 811 | 810 | 内功伤害 | 812 |
| 821 | 820 | 内功防御 | 822 |
| 1231 | 1230 | 加强封印 | 1232 |
| 1241 | 1240 | 封印抗性 | 1242 |

11种映射只说明类别/显示目标。它们可以出现在什么部位、概率、等级区间、正负取值及初始附加幅度仍unknown；不能因为基础表出现该id就把它无条件作为每个部位的附加池。1230和1240是两份独立裸身基线；旧角色缺值不是0，不能互借。最终整数还必须满足原普通刷新float32精确表示及入场signed32；新增五维入场还受signed16 0..32767限制。

五维资源行10/20/30/40/50分别给numid11/21/31/41/51（体质/内力/力量/耐力/敏捷），percentid12/22/32/42/52。本批再核表字段，既有原描述器实际执行了raw11等描述分支；**1038模板的基础项没有五维numid出现**，因此不能从基础表推原附加五维→最终人物派生的算法。当前RoleAttributes的five_stats顺序与这些五维一致；若生成五维附加，必须定义是否计入角色可分配五维、技能/穿戴门槛及派生重算的阶段，避免写回成长账本造成永久重复加点。应用现growth增量系数也是新装备政策的designed决定，不会自动变client_verified。

百分比同样需单独定义分母、作用基数、叠加/连乘、flat与五维先后、取整、负值和溢出。raw82/142/812是百分比身份，不能当81/141/811平值。若首版不支持某类，须在结果生成前排除且标明范围；不能生成后静默忽略属性。

## 5. 本批重新打开的端游官方原页

2026-10-24实际浏览以下两页；只用同款端游，未用手游、神雕2、坐骑装备或后期神兵规则。URL含历史日期，但当前页面未给精确客户端1.6.1版本证明，故适用性为guide_supported。

- [《打造最强装备 装备系统解析》](https://sdxl.wanmei.com/news/gamenews/20130830/149369.shtml)：URL历史日期2013-08-30。支持六个部位、评分影响颜色、基础与附加之分；鉴定可能产生附加，重铸与精练处理附加。没有普通鉴定条数、类型池、数值上下限、品质权重或初始评分公式。
- [《装备打造》](https://sdxl.wanmei.com/info/newplayer/50to69/20120705/132376.shtml)：URL历史日期2012-07-05。支持鉴定后揭示属性、五档品质/六颜色及品质帽、同等级属性有范围差异、品质与成长空间关联；评分受装备多类属性影响。没有具体范围、分布或精确生成时点，不能据“鉴定后看到”推定结果此前不存在。

品质名称/帽也由本地原表独立复核；网页的陈述不能证明本地五档生成概率。其无双提示意味着主策须明确新版本是否生成无双及评分，不能把空字段长期冒称完整原服。

## 6. root应一次裁定的最小未知集合

以下均为待裁定designed变量/Interface要求，**不是本文件已生效政策**：

1. 生成时点与结果身份：创建/打造时生成但未公开，还是本次鉴定事务生成；何时绑定稳定生成key、规则版本、可信随机源与完整结果。未鉴定客户端能否接收隐藏字段须单独验证；原parser可存全属性不意味着应提前泄露可预测极品。
2. 基础生成：按模板原base作为基准还是固定值；各level/部位的幅度、分布、取整、各属性相关性、上下限。对140/150缺模板、16/18缺费用档、64缺列表、49192百分比、212套装明确各自后续路径，不拷贝样例填空。
3. 附加序列：条数权重、各部位/等级池、重复规则、抽样是否放回、顺序、各属性值分布、负值/0/百分比/五维资格，第三个精练计数初值。原wire可4条且UI局部只示3条，业务上限需设计；不得dict吞重复。
4. 品质与耐久：五档权重及与基础/附加强度、成长空间的关系；品质生成时点；初始current/max及较好品质是否另有上限。品质、评分、颜色、condition版本在同一完整结果中一致，不能只抽颜色。
5. 初始评分：基准、每类贡献权重、是否包含基础/附加/无双、取整顺序、合法界与每模板scorecolor标定。若生成强属性还永久score0/color1，会形成评分失真，当前clean例外不能泛化。
6. 角色贡献：基础+附加对11类flat、五维/百分比/封印基线的组合顺序与版本；装备变化同事务更新资源投影，上限增加不回血、下降只裁剪、死亡保持0等必须明确；未知字段不得被clean投影覆盖掉。
7. 兼容与幂等：现explicit_known_clean_instance已承诺固定完整clean结果；既有identified0/1与旧paid receipt不能被新随机政策重新解释。若需要升级，必须单独版本化转换和完整原值审计，不能把已付款/已生成物品重抽或重收；失败回滚与同一admitted命令的draws稳定性也应明定。
8. 扩展字段与流程：无双/强化/宝石/套装是否纳入本版生成、保存和评分；已有未知修饰要拒绝/显式迁移，不能全写0。NPC实时身份/距离/ticket、库存全量CAS/唯一收款凭据、完整原生可编码检查仍须保持，各自不能由稳定binding代替。

采用codebase-design的结果是一个纯生成Module消费冻结完整输入、规则与可信draws，返回不可变完整计划；角色Owner在一个有界I/O事务中执行费用、Inventory公开全量CAS、详情/condition/资源版本与唯一凭据，连接Owner再做当前绑定下的编码与投递。该Interface需要性能预算、失败模式、幂等与结果完整性，不能仅把函数命名plan而在NPC里继续散落抽样。上述是inferred实施要求，实际政策由root最终裁定。

## 7. 原包成员与本批固定输入

本批直接读取 `D:/神雕侠侣/artres/config.pfs`；以下成员前缀均为 `autoconfig/knight.gsp.item.`、后缀 `.xml`。PfsArchive.read实际检查本地/中央记录、解压完整性、长度、CRC；BXML decode完整消费。原记录以id定位，样例取自原字段。表数量与既有native研究一致。

| 成员表名 | 记录数 | 展开字节 | CRC32 | 展开字节SHA256 |
| --- | ---: | ---: | --- | --- |
| citemattr | 12280 | 4096369 | a3add081 | `974a3b38049c5f5f7cdae418718ffadd2741d373a5846a40fb71289af25e726f` |
| cequipeffect | 1521 | 467441 | e354a76d | `8ef1aacae8d016f875a37a8cf907b16a077b89fa522a87e349dd54d320572fe8` |
| cgodweapon | 85 | 3704 | 65746fc2 | `295fbe76d7deaef3bb4c17733f329ce41384c5724b6aef713b93a7a6abfa86a2` |
| cattributedesconfig | 195 | 19508 | 56e2ca7e | `5c68180582cf6252696d0bd61cd9ea9c11119beab2b473e96aa27bf0da358a79` |
| cequipprefixconfig | 6 | 291 | c8592725 | `3b36fed5bf4e62e41ceec422d902f8479bdcc487e82351750168ba130805e7ae` |
| cequipscoreconfig | 36 | 10245 | 77c46054 | `c370650594da413d8870204e0820dab958f34cd9b9386f6102a54f0ba43be683` |

本批10项解析/模型/政策输入首次取hash后，结束前全部再次重算一致；另4项旧研究输入本批引用的hash如下。工作区后续可能继续演进，不能用新文件替换此处固定值冒称同一验收：

| 本地输入 | SHA256 |
| --- | --- |
| revival/pfs.py | `d4c9a5f6080276ab51886fdd4f1d7e7c1618715f870cbce84c916cf03b163352` |
| revival/bxml.py | `ba61810a10fede4305075efd7120429fb165af90fdbb4fb94697862a30c8b66d` |
| revival/equipment_detail.py | `05f974a8d201da47b11c332e00bc4c9eaa402366b3f6c14596929541e941118a` |
| revival/role_equipment.py | `7f3c539c3b0a0cdc001e63a829da835e781a04609dcfdad270ce03a25ee90352` |
| revival/design/equipment-detail-v1.json | `f628be27b3be8e0533e154014d3c0d09502cd25e7cb944bd3cb625cf98718358` |
| revival/design/role-equipment-v1.json | `a98b52c2bfe05464c8620a97eff09f33f280d7aa7728149691d600ebdd7bf0e9` |
| revival/design/role-equipment-v2.json | `d1907947b94a6e663a2f4ebc47a7b0fffa292567de2ff6e0a81c02fb5d35f0b9` |
| revival/design/equipment-condition-v1.json | `32b398d197fa64cb893fa91281a30919b962da03e0854029c68473f8d2c7b079` |
| revival/design/role-attributes-v1.json | `6502cf3ffaa256e0b260bf039584c96b31eff5ef5b2775c3092f618e222a8456` |
| revival/design/npc-equipment-identification-v1.json | `2a486c524ff3e043359cc57a5fce6305d16f680f555e3072aab14374bcf7f138` |
| revival/evidence/EQUIPMENT_RANDOM_IDENTIFICATION_MODEL_RESEARCH.md | `ce30d279cf0f904d9057b796d33bfa8f2e1bd9ec7c9b6f5ea2c50ad8678d57a6` |
| revival/evidence/equipment-random-identification-native.json | `16e5e29b90f3e1c70d35ae18c08fa8a42fdd20e40a6e81326a10cfe947d3039c` |
| revival/evidence/ORDINARY_EQUIPMENT_ATTRIBUTE_RESEARCH.md | `390d0b1d4d243c6f6bdc39b3d3764037810842aaaf042fb429786630af5966c4` |
| revival/evidence/EQUIPMENT_IDENTIFICATION_RESULT_SOURCE.md | `9032fe7aa0625172d1a36322b9f003830c28a31cc7c6ff3c0f91bc30006dd637` |

实际验证：原PFS六成员解码/计数、1038筛选与等级覆盖、973/761与原政策口径一致、24条真实模板与5档品质逐字段提取；两篇官方原页实际打开。150六槽不存在是扫描结果，不是省略样本；130样例是明示的补充。未运行原程序长模拟、游戏进程、GUI、服务、正式或临时DB、游戏socket；未测试完整随机模型、余额、穿戴/战斗、容量或共享接线，未修改任何生产/政策/旧报告/frozen目录。

产物仅本Markdown。后续若原包或政策发生变化，应重新绑定对应来源并重验，不能把本批未知数以字段默认0补齐。


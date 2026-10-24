# 玩家100008太祖长拳：原施放上行、目标与消耗/表现来源

2026-10-24。本批只查100008，供未来第二战配方使用，不增加当前首战+教学发布门。重读research技能，作为根任务后台代理沿原PFS/原指令追溯；ARCHITECTURE/DESIGN_AUTHORITY完整约束沿用。仅新增本文和独立staging研究脚本，不改RoleSkills/TaskPve/battle/shared/政策，不运行GUI、真人DB、线上战斗或已暂停Battle goal。

## 可以采用的事实

`client_verified`：原技能列表选择尾写入100008后，目标mask480使其进入选目标模式；原目标点击分支与校验通过后，实际发送 **CSendAction0xc1b5c，operation2、主目标21、operation_id100008、is_role1、is_auto0**。原marshal/decoder实得14字节 `0000000200000015000186a80100`。本批比“向sender参数注入2/100008”多执行了原选择写入、原配置target-mask读取、原目标校验和真实sender；仍不是GUI点击或服务器技能授权。

原玩家配置文字明确“攻击2个敌人”、真气消耗随人物等级提升；没有闭合精确MP、伤害倍率/类型/防御关系或第二目标算法。四个param原值0不能当成免费或伤害0，NPC同名条目的15/1不能移植。**已学ledger的100008/value1不是战斗能力、伤害配方或一次施放授权。**

## 原来源与复现

原映像 `evidence/native-image.bin` SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`，下列VA绑定此映像。PFS各成员均直接经长度/CRC校验后BXML解码，不以缓存JSON为最终依据。

| 原成员 autoconfig/knight.gsp.… | rows / bytes / CRC32 | SHA256 |
|---|---|---|
| skill.cskillitem.xml | 652 / 107547 / b5d9fdd8 | `2a8645ae11267eb3cbbeeab0f56f4be8f8fe9b4fa95f6c4026448f59afc07194` |
| skill.cskillshowlistclient.xml | 239 / 11110 / 112a2193 | `eda1374328a6a2574cc53b6eee53f1e81b144f5d9da44965c89a647940d8d6eb` |
| skill.cskillshowlist.xml | 6 / 4644 / 118178bc | `67632b0dc85a979637846c3d1717bac6f75b48d93a9661a381ea92f95931c5ac` |
| skill.cskilltypeconfig.xml | 1308 / 42614 / 388ccdb8 | `ea99ab5cf95d1d9e571bb2841cbd7c99457e46a26891cc5cf2dafc63fed3699e` |
| skill.cskillbase.xml | 70 / 12938 / 26013e23 | `06b7342f3becec4e8c4227168536aecf9a83caa3c3cd82b17fbd07b2b6017b2a` |
| skill.cskillconsume.xml | 15 / 2229 / 1ac3874e | `ece2760d4f01b4b100f4f8105c382a41641bcb1296b06de902171d30ca65fa3a` |
| skill.cskillcost.xml | 160 / 8857 / c56c975e | `a7a8321616a3f0cc0e8349e7d311e6a7bf89d771d757136cbbe29ea3bd65ee8f` |
| skill.cskilleffectextra.xml | 60 / 1607 / d989ce1c | `03abef3e8d50b898f8be736848d290262ad5ebc742c6d60b94d60a0da856513e` |
| battle.cbattlemagicconfig.xml | 805 / 140194 / 44d2f6d0 | `08077ffead7f19f8e18b4a779c01f9f18c03d90699d823a23e8696534f018476` |

独立工具：[research_taizu_first_skill_combat_native.py](../staging/research_taizu_first_skill_combat_native.py)，SHA256 `90d08ab95ef3948637f520b1886783b0ad35d9a03326ffdb32be56e7ef5636be`。可导入 `source_audit()`、`native_taizu_action()`、`native_numeric_classes()`；仅stdout/返回值，无DB或写文件。沿用 [research_battle_commands.py](../research_battle_commands.py) 的原sender/codec地址，未运行其会写旧报告的main。

## 四套“类型”与相似ID必须区分

| 来源 | 100008原值 | 限制 |
|---|---|---|
| cskillshowlist | 展示class6“其他技能”包含100008 | 不是统一已学容器；只读完整namespace沿既有研究 |
| cskillshowlistclient | skillname太祖长拳、skilltype1 | 显示字段，不等于下表4 |
| cskilltypeconfig | skilltype4 | 原字段存在，未闭合其完整枚举语义，不能直接命名某种伤害公式 |
| 原分类1070ea0 | native class1 | 与显示class6/config4分开；已学身份走manager+40 |
| 原战斗CSendAction | operation_type2 | 技能施放操作号；4是已证防御操作，不是本招式 |

本批实际执行原1070ea0：100008→1、600005→6、500001/500067→2。原600005在showlistclient名“宝石合成”、skilltype0；cskillitem没有600005。它不是本玩家战斗技能，也不能因某处称“class4”就与100008混用；若class4指cskilltypeconfig原4，应保留该来源名称。

cskillitem500001同名太祖长拳、paramB15、sType“多体法术攻击”；500067名“赵老爵爷-太祖长拳”、paramB1，属于另一ID/原class2。这些项共享effect10011/targettype480，但不是玩家100008。相同名称/特效/目标mask不证明MP或倍率相同。

## N1：原玩家100008完整配置字段

该记录没有子列表。

| 字段 | 原值 |
|---|---|
| id / skillname | 100008 / 太祖长拳 |
| sType | 多体伤害招式 |
| paramA / paramB / paramC / paramD | 0.0 / 0.0 / 0.0 / 0.0 |
| costA | 消耗：消耗真气随人物等级提升 |
| costTypeA / costTypeB | 70 / -1 |
| normalIcon | 327 |
| skilldescribe | 虽然初入江湖，却也有着不俗的精气神。使用自身力量，攻击2个敌人。 |
| targettype / bCanUseInBattle / effectid | 480 / 1 / 10011 |

“2个敌人”是原文字事实，目标mask480不是计数480，也不是已证明自动补选算法。cskillbase、cskillconsume、cskillcost、cskilleffectextra均无ID100008行。cskillconsume的15行numberrand来自其他技能，不能套入；cskillcost各行是ExpCost/MoneyCost，id70行184061/21688不因costTypeA70就变成此技能战斗消耗。缺行只表示本批未取得相应配方，不表示原服无公式。

## N2：原选择→目标校验→真实14byte施放

1. `11b1ca0` 是技能列表事件消费者；此前 `4d3aa0` 从UI项目取ID。本probe从明确UI已选100008的边界 `11b1cd6` 开始，保留原 `11b1cdb` 把ESI写BattleMgr+e0。UI项目getter/渲染未执行。
2. 原 `11b1ce8→12cc180` 调1070ea0分类；class1在 `12cc1c2..1e2` 查原cskillitem、用原拷贝ctor `c68920`，从复制对象+c4读targettype480。table getter仅适配为合成结构，参与的id/+c4目标/+c8可战斗/+cc特效字段匹配原PFS；其他文字用空字符串夹具。本probe没有把整个原配置解析器或完整UI渲染冒充已运行。
3. `11b1ced` 比较该值1；480不等1，进入 `11b1d4c` 的选目标模式，而不是立即按自己施放。该返回是target mask，不能误叫cskilltypeconfig.skilltype。
4. 以合成目标object+140=21、+17c=3进入原点击分支 `1196b2a`：原 `119acd0` 再读同一targettype，原 `119ab00` 分发目标类别；本夹具走 `119ac09..119ac24`，对位置15..28取mask bit8，480通过。目标类别3仅为该原对象discriminator夹具，不据此外推全部服务器阵营/死亡/宠物规则。
5. `1196b3a..41` 实际push手动0、技能操作2、主目标21并调用原 `1196060`。原 `1196153..61` 从Mgr+e0取技能100008；人物phase3走原 `11962bf..e0` 字段写入，`1196334` 抵达连接send虚槽。没有替代target predicate、sender、字段构造或编码。
6. 原marshal `e41550` 及原CSendAction ctor/unmarshal `d598c0/d59ab0` 执行并一致读回：

```text
type0xc1b5c
00000002 00000015 000186a8 01 00
operation2 / primary_target21 / operation_id100008 / is_role1 / is_auto0
body length14 = BEi32 + BEi32 + BEi32 + u8 + u8
```

反事实反馈：保持选中100008与目标相同，仅把配置fixture target mask480改0，原 `119acd0` 早退；在 `1196b46` 停止，无发送、未进入sender。因此目标mask确被原消费者使用。该负例是敏感性夹具，不是修改原资源或批准mask0。

此包只有一个主目标，无第二目标列表、技能值/level、MP或伤害数值。它是请求，不证明已学、资源充足、技能可执行、当前配方允许或胜利。

## N3：表现资源与伤害/消耗结果

原cbattlemagicconfig闭合effect10011的演示配置：10011“太祖长拳起手”，effectname `geffect/sprite/skillbanner/taizuchangquan_`，basetype1、postype0、genemagictype2、genemagicid10012、genemagictime600、genemagicdirection0、geneeffect=false、geneeffecttime0；starteffect列三条1/2/3版技能横幅。10012“太祖长拳结果”，effectname `geffect/skill/taizuchangquan/taizuchangquan_`，basetype3、postype0、genemagictype/id/time/direction全0、geneeffect=true、geneeffecttime700。

这些是原表现字段，600/700不当耗蓝或伤害，时间外部单位/演示完整调度/GPU本批未执行。施放operation_id必须100008，不换成表现effect10011/10012。

已有通用DemoExecute原字段为attackerid、hpconsume、mpconsume、spconsume、operatetype、operationid、msgid、childskill、passiveskill；目标结果可逐目标给独立map。伤害表现的原key1消费者在 `119115d` 从结果map取signed HP变化，见 [BATTLE_DAMAGE_PRESENTATION_FIX.md](./BATTLE_DAMAGE_PRESENTATION_FIX.md)；它不是DemoAttr列表。本文沿用该已证通用结果布局，未重新执行整段RoundScript，也未宣称100008的某个实际伤害已由原公式算出。

既有 `verify_battle_loadout.py` 的100008/MP10/伤害6是训练显式fixture，能说明原codec承载技能ID/一次耗蓝/多目标结果，不是原版MP或伤害配方。单发已学包或显示横幅不证明服务器正确扣MP、命中两目标或执行真实受击。

## 尚需root设计的精确缺项与验证边界

- MP：按人物等级还是技能value取值、精确函数/下限/取整、何时扣、MP不足处理。原cost文字只支持随人物等级提升，param全0不补公式。
- 伤害：物理/法术/固定的正式语义、基数/倍率、防御与防御动作影响、上下界/取整/异常值；cskilltypeconfig4及sType文字不代替公式。
- 目标：可将原文字“2”作为数量设计依据，但主目标合法性、另一个目标选择、去重/死目标/宠物/阵营/自动目标0策略未由14byte包给出。
- 能力：本场只读完整已学快照与100008当前value/revision，经已批准recipe显式允许，再由BattleOwner结算一次消耗和分目标结果；学习receipt不直接开启技能执行，不能每次开战重授value1。

最终统一执行通过九原表长度/CRC/SHA、选择/原mask读取/原目标校验/实际sender/原marshal/decoder、mask单变量拒绝及四ID原分类。本批仅原指令离线夹具，未验证真实菜单、全部目标状态、完整自动战斗、MP前置校验、全套Demo/GPU、真人资产与终态结算、发布或GUI；未加任何当前发布开关或验收门。

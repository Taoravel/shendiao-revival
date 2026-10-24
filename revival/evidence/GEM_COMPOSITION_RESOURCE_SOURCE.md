# 宝石合成：体力450/630与杂学600005的来源及账本边界

2026-10-24，本地1.6.1端游/网络版本601。按Matt Pocock research，本批重新读取research SKILL和根AGENTS，沿用完整上下文中的ARCHITECTURE/DESIGN_AUTHORITY；作为根已委派的后台研究代理直接查原PFS、原消费者和顶层当前源码。唯一落盘产物为本文，没有修改生产、现有研究报告/脚本、政策、其他文件或线上状态，没有操作真实客户端或向其他聊天发送消息。

## 首先纠正旧报告的技能ID

**原宝石合成窗口读取的是600005，不是602053。** 原0x1361d51的立即数为`0x927c5`，十进制600005；旧EQUIPMENT_GEMS_SOURCE_RESEARCH把它误写成602053，是研究记录中的十六进制换算错误。本批重新读取原指令、原表并执行原技能map保存/查询确认。按要求不改旧报告，以本文明确纠正该字段；不能据旧报告创建602053账本。

原npc.czaxueskillconfig的600005名为“宝石合成”、zaxueid=2、inbattle=0；skill.cskillshowlistclient的600005同名。clifeskill中的300403也是“宝石合成”，但属于生产入口、bCanStudy=0；不是这里查杂学等级的键。顶层原native映像可执行区内600005立即数xref为0x12d66db、0x1361d52、0x13626c6；602053没有相同用途的xref。

## 体力与活力确实是两份资源

`client_verified`，直接原`item.cattributedesconfig`：

| 当前ID | 原名/用途 | 上限ID/原名 |
|---:|---|---|
| 440 | 活力；炼药、烹饪等消耗；养生术提高上限 | 620，活力上限 |
| **450** | **体力；装备打造、宝石合成等消耗；强体术提高上限** | **630，体力上限** |

450行numid=451、percentid=452属于该属性的其他分量字段，不是体力上限；630才是命名明确的上限属性。620与630两行都有numid601/percentid602，不能因这两个分量相同而合并资源身份。

独立原消费者也成对读取：

- **0x10dcec0..10dcedb完整getter**：从当前角色manager+0x164的属性map读取`0x1c2=450`并返回，未读440。
- **0x13618ac..13618c8**：宝石原料完整等级getter0x1074d10→`5×(level+6)`→完整0x10dcec0取450→有符号余额比较。
- **0x1361e33..1361e62**：合成UI直接取450，按同一费用比较，决定体力数值显示颜色。
- **0x115a219..115a232**：角色显示同时取`0x276=630`和`0x1c2=450`，格式化当前/上限。
- **0x10ad478..10ad498**：分别取630/450并比较是否满；紧接0x10ad4a0..10ad4b7另取620/440，证明并列资源而非一个字段的别名。

原book115/116分别是体力/活力。两者都写初始值30、每在线5分钟恢复一次，但分别由强体术/养生术提升上限。**“初始值30”不能自行外推成每个现存角色当前余额或最大值都30**。原clifeskill320103强体术与320104养生术分别写每级增加对应上限4；当前角色已学等级、基础上限和其他修正未获授权时，不可用`30+4×等级`反建未知旧存档。

## 本批原生实际执行

均先import native_inspect/native_gameplay_probe再导入Unicorn，使用原只读native-image.bin，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`；没有启动客户端/服务、没有生产数据库写入。

### 42例合成体力门槛：实际读取450

原x86-32映像完整映射，manager=0x5300000，原属性map位于manager+0x164；构造真实map sentinel/node，节点key450/value余额。原物品引用level在+0x28，type5。实际执行0x13618ac至原分支0x13618ca（不足）或0x13618f9（够用），保留完整0x1074d10、完整0x10dcec0和原属性map查找0x4e8e00，**没有拦截这些函数返回值**。

原料等级1..14，每级测试所需−1/恰好/所需+1，共42例，全部符合：

| 原料等级 | 原费用 | 余额不足 | 恰好余额 |
|---:|---:|---|---|
| 1 | 35 | 34→拒绝 | 35→放行 |
| 2 | 40 | 39→拒绝 | 40→放行 |
| 5 | 55 | 54→拒绝 | 55→放行 |
| 10 | 80 | 79→拒绝 | 80→放行 |
| 14 | 100 | 99→拒绝 | 100→放行 |

这是原客户端门禁/费用计算。原服务端在成功和随机失败时是否都扣同样体力、取消/掉线的时机，是结算策略，不能由门禁单独证明。本批不代替该策略作决定。

### c32c8资源刷新：四个键并存而不混淆

原 **attr::SRefreshRoleData type0xc32c8**，constructor0xec3590、marshal0xec36b0、unmarshal0xec3730，体是`compact(count)+若干BE32 attrid/BE float32 value`。

本批同时放四个原键，完整原marshal/unmarshal一例通过：

```
440=85, 450=35, 620=100, 630=150
04000001b842aa0000000001c2420c00000000026c42c800000000027643160000
```

随后借用verify_role_resource_protocol.native_assignment但不运行其写报告的main，实际执行原 **0x113f5f0..113f630** 的普通attr赋值切片6例：450=0/35/16777216，630=150，440=85，620=100。原float→整数转换和最后overwrite执行，唯当前角色的属性单元查找由host接缝提供；每例准确写回对应键，没有450到440的映射。停止在GUI观察者之前，不声称完整UI生命周期已执行。

协议无专门“体力增减包”的必要：可以用同一c32c8只发450当前绝对值，或同时发450/630；必须从当前体力权威读取，不能从VigorState复制余额。float32原字段在2^24以上不保证每个整数可精确表达，服务端应沿现有资源编码标准验证精度，不能先扣资产后发现编码值不合法。

### 杂学等级600005：原map与更新协议

原技能manager全局0x29448a4；杂学等级map在manager+0x4c。完整 **0x12d1db0** 用传入skill ID查map，命中返回node+0x10的等级，缺失返回0。原 **0x12d66bc..12d66ce** 将收到的int/int pair写入同一map；紧接0x12d66d9比较600005，有打开合成窗时调用0x1362690刷新该窗。0x13626c5也再次明确push600005。

本批构造真实单节点int→int map，依次以600005等级0..6执行原保存切片，再完整执行0x12d1db0查询，每次都读到原保存值；同一map改查602053均返回0。共7组保存/正确查询/错误键缺失对照，原map查找及iterator检查均执行，没有注入预期等级返回值。

**客户端缺键返回0是本地显示约定，不授权服务器把缺失持久来源当“已知未学”。** 服务器若不能确认角色600005状态，须保留unknown；已知未学等级0可作为有明确来源的有效基线。

原 **skill::SSendZaxueSkills type0xc36cb**，constructor0xf31100、marshal0xf31250、unmarshal0xf311b0，原vtable0x228530c；体是`compact(count)+若干BE32 skillid/BE32 level + byte flag`。它与c32c8的float属性map类型不同。

本批14例完整原constructor/marshal/unmarshal：600005等级0..6，每级flag0/1，两字段精确保留。例如：

```
600005=0, flag0  01000927c50000000000
600005=6, flag1  01000927c50000000601
```

原process0x12d6850将末byte是否等于1转换成布尔，复制map并调用0x12d63c0；本批未完整执行带配置/UI/提示的整条process，也未确定flag的所有业务含义，**不能自行把flag0/1命名成“全量重置/增量”**。已执行的是codec、实际最终map保存切片和完整getter。

### 体力恢复显示量不等于现有活力设计常数

原角色tooltip在 **0x11526c4** 区分450，**0x11526d6**取630，**0x11526e6..11526fc**按当前上限整数计算`floor(maximum/100)+2`作为该提示中的恢复量。原算术切片8例通过：30→2、99→2、100→3、194→3、399→5、400→6、1000→12、16777216→167774。

原属性说明明确每在线5分钟恢复；这使“每期显示增量按上限变化”有客户端依据。**本批没有执行服务器定时恢复、离线恢复、跨登录余数或溢出规则**，也没有把现有role_vigor的固定gain5改成该公式。新的体力实现如果只先提供已知基线的读/扣/刷新，可保留自动恢复未开放；若以后实现，需由资源所有者集中定义时间来源、租约、满值余数及离线边界。

## 当前顶层服务器源码审计

仅扫描`revival/*.py`顶层源码；不查runtime副本、部署目录、历史快照，不读取真实数据库。第一次搜索时role_stamina尚未出现相关命中；研究期间父窗口正在实现，最终快照已有634个顶层py、role_stamina.py及equipment_gem_composition.py，role_skills.py仍不存在。以下是读取时的代码事实，不是运行服部署/验收结论。

| 当前文件/模块 | 查到的权威范围 | 与本任务关系 |
|---|---|---|
| role_vigor.py | role_vigor_profiles；VigorState；440/620；显式初值100/上限100、5分钟加5为已有designed policy | 只负责活力，不能扣作体力 |
| game_runtime.py | 登录/检查点/登出调用role_vigor；`initialize_vigor`入口 | 证明已有活力运行时接线，不能证明体力已有相同接线 |
| npc_recovery.py | 客栈休息消耗role_vigor | 不能借客栈接口消费宝石体力 |
| role_practice.py | role_practice_skills只允许360001..360007七个战斗修炼技能 | 不是通用生活/杂学ledger；不能向其中塞600005 |
| item_effect_protocol.py | c32c8一般资源编码，但当前函数只发HP/MP60/70 | 可参考原协议结构，不提供体力账本 |
| 本轮新出现role_stamina.py | role_stamina_profiles；450/630；explicit_known_stamina来源；当前租约/事务、version CAS consume、refresh | 已有独立体力候选Module；本批只读，不修改或宣称其测试完成 |
| 本轮新出现equipment_gem_composition.py | policy校验skill_id600005；CompositionStudy携role_id/login_epoch/policy/version/level | 这是调用方传入的可信技能快照合同，并非已经存在的通用技能持久ledger |

读取时源码SHA256，帮助区分并行变化：

```
role_vigor.py             5d5794460962f498c34d727a17c2841efec3d74114d180a745da20dd4de86a9d
role_practice.py          c6bff759fdd62f6c813b1a871f0652bad19328c29daa3acb57c22799c6429710
item_effect_protocol.py   64e000f7fb468dd6fcd64af1c8910e91fb0ec39ae1c0107f8b820d59c772f883
game_runtime.py           4ff8b224d5ea4d18e1daddeb2211752f9c1fceeb34b7eb20ddaf4027cd44fe61
role_stamina.py           3b731535bad94fafc397756f6371ec68f51a5a87b22195d222cbef238511f7e1
equipment_gem_composition.py dc0519b755395577d9ebc5ba81d77237d4cdaef3ebdb625f66a4c1dca789f138
```

在该审计范围内**没有发现通用600005杂学等级权威持久ledger**。这不证明其它聊天不会随后创建role_skills，也不授权宝石系统自行争抢技能所有权。对接尚未出现的任务窗口role_skills时，应输出不可变的当前role/epoch/skill600005/level/version/policy来源快照，并在同一角色事务复核版本；只凭客户端显示或请求不能初始化技能。

## 原配置直接重读与版本

原`artres/config.pfs/autoconfig/knight.gsp.*.xml`本批重新PFS读、CRC检查、BXML解码，完整attributes/lists逐行与catalog一致：

| 表 | 行数/字节 | CRC32 | SHA256 |
|---|---:|---|---|
| item.cattributedesconfig | 195/19508 | 56e2ca7e | 5c68180582cf6252696d0bd61cd9ea9c11119beab2b473e96aa27bf0da358a79 |
| npc.czaxueskillconfig | 18/59516 | e0e23e6a | 8bdca3c38b48984f51c80a8df57af8e1fbff87ed8e7dfc2c683ad33edaa51f96 |
| skill.clifeskill | 49/16147 | 63c49bf7 | 0b55580becb96531fa99287c977d8257fca305c02b973a1aa5e5252b9cbc1a4d |
| skill.cskillshowlistclient | 239/11110 | 112a2193 | eda1374328a6a2574cc53b6eee53f1e81b144f5d9da44965c89a647940d8d6eb |
| item.cgemcomposesuccessrate | 7/219 | 6adf7e9e | cf2e9af3eea695785552de97cb1fcd413b6d6b468ebe9a257ad197dabceb8565 |
| servant.bookanswerconfig | 2123/1391956 | db4543ec | 5676da882382a3c4e23221a35e0911a3bed1c6ab4e1c6364d9826a912267bf4c |

misc600005的leveldescribe原文列1..6档5/10/18/24/35/50%，与cgemcomposesuccessrate id0..6的0/5/10/18/24/35/50完全对应；原0x1361d4b..1361d9a明确“读取600005当前等级→按等级查加成表→加宝石基础成功率→截顶100”。本批没有把clifeskill300403等级或强体术等级当成功率加成。

## 官方同款PC旁证

本批重新从官方资料导航获取并直接HTTPS读取，而不是复述旧报告。以下都是2012端游历史资料，不能替代本包新增字段或真实服务器账本；不使用手游或神雕2。

- [2012-07-29生活技能](https://sdxl.wanmei.com/info/qita/skill/20120729/133533.shtml)：分别说明强体术每级加体力上限4、养生术每级加活力上限4。直接响应10668字节，SHA256 `633c246fcdcdb651f8ba08763b75b0d86129f7e8936b666a591f92968381a762`。
- [2012-07-28杂学技能](https://sdxl.wanmei.com/info/system/olio/20120728/133510.shtml)：宝石合成属于杂学，用途是提高合成成功率、从原著人物学习。直接响应11373字节，SHA256 `01a54152318bd76e2c6a71061ed3040ea39be2d919dd01e72b824449b3672d96`。网页没有600005数字ID，数字由本包/原指令确认。
- [2012-07-29宝石合成](https://sdxl.wanmei.com/info/qita/skill/20120729/133540.shtml)：明确合成消耗体力、宝石级别越高体力越多。直接响应13031字节，SHA256 `c7f1a0090a30b35ccd5048cd581df24dcbdb701ffb5ee7f9546f577708cbd052`。网页没给`5×(level+6)`公式，该公式取自本批原生执行。

web直接open前两页未能访问，本批通过常规HTTPS读取成功；不是把不可读页面推定为已证。以上旁证标guide_supported，原字段/原函数标client_verified。

## 能实施的合同与仍需决定的边界

可直接实施的来源事实：资源键450/630、原合成门禁费用35..100（原料1..14）、c32c8绝对float map、misc键600005、有效成功率表索引0..6、c36cb int map尾byte结构。现有role_stamina独立于role_vigor方向正确；仍需具体测试/接线/部署证据才能宣布完成。

建议由角色所有者在同事务内读取并校验当前体力profile和600005技能快照，保存计划中的版本及来源；物品、体力、随机结果和命令凭据一起提交；重试返回当前绝对450值。未知profile或未知技能来源拒绝/保留待迁移，不能借“原客户端缺键=0”补建服务器未学档，也不能调用role_vigor.consume。

仍未知或未验：当前角色真实体力基线/完整上限构成；原服务器恢复节奏/离线与余数；成功/失败实际扣体力时点；技能学习费用与全部来源、持久化/重登接线；c36cb末flag的完整业务语义；任务窗口未来role_skills接口；生产服是否采用本轮新模块。若主策划补全这些，需集中标designed，不能将本报告的只读源码发现当部署事实。

## 方法、产物、验证与未验证范围

research实际影响：以原属性名和成对消费者区分两资源；重新读取原立即数发现并纠正600005换算错误；用真实原map lookup和对照错误ID排除伪映射；扫描顶层源码发现并行新增体力模块，避免声称“仍没有体力账本”，并保持技能快照合同与持久ledger区别。

正式验证：6张原表全行比对；42原合成余额边界；1个原四资源map codec往返+6原赋值切片；7组原misc保存/完整正确键查询/错误键缺失；14原misc codecs；8原体力恢复显示算例；顶层源码只读审计与3页PC官方读取。所有harness只在内存运行，唯一新文件本文。

没有验证完整UI或服务器运行、真实资产、技能学习/体力自动恢复、真实数据库迁移、任务窗口新代码或部署，不修改旧报告、不擅自创建任何角色资源/技能基线。

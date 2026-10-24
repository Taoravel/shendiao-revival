# 帮派成员生活技能：原生请求、费用、等级与容器调查

2026-10-24，第26批后台research。对象为本地1.6.1端游、network601。本文是本研究子任务唯一Markdown产物；调查阶段未改实现/政策/共享文件，未启动游戏或服务，未访问真人数据库。临时验证均经stdin运行，使用原映射镜像与受控虚拟内存。

## 会影响实现的结论

- `client_verified`：`CUpdaetAssistSkillLevel`（原名拼写如此）为`0xc36b6`，body是BE64 NPC上下文、BE32技能ID、1字节mode。帮内生活技能按钮`0x13503c0`使用mode0；mode0也出现在其他学习窗口，不能单凭mode0认定NPC属于本帮派。其余mode0..4仅完成原marshal形状核验，未赋予本研究未绑定的业务意义。
- `client_verified`：生活技能与七项修炼共用原技能manager（全局`0x29448a4`）的`+0x74`树，值为两个i32：等级及该技能的熟练/经验值。它们与`OtherSkills`的`+0x40`树不同。原`SUpdateAssistSkill` `0xc36b7`三i32增量会更新这份`+0x74`树；工坊对打造技能把第二值读作熟练度，不能把它当角色升级XP或帮派研究XP。
- `client_verified`：`SSendAssistSkillMaxLevels` `0xc36b8`是NPC Q + compact数量 + map<i32,i32>，原完整14节点marshal/unmarshal已执行。Process把Q存入帮内窗口`+0x68/+0x6c`、注册NPC关闭追踪type13，将返回的技能最大等级放入窗口`+0x88`。学习按钮以当前等级+1查表，目标级不得超过该最大等级。原消息140421把拒绝说明为达到/超过帮派研究上限。该协议是服务端给出的个人可学上限；服务器是否还取其他限制的min，本批未证。
- `client_verified`：帮内面板以目标等级行的`inMoneyCost`显示所需银两、`inExpCost`显示所需角色经验、`inBG`显示所需声望。**显示所需声望不等于已执行声望扣款。** `inBangGongNeed`、`inBR`未找到对应的实际扣除/门槛消费者，不按名字认定其为声望门槛或资源费用。
- `client_verified`：原按钮的预算顺序是先查经验、总银两预算，再查**银两+绑银至少10000**，最后决定是否提示使用存款。这10000并非只在使用存款时检查，也不是`min(费用,10000)`：费用仅3时，身上仅3且无存款仍被142514拒绝。这个事实应进入学习业务门槛，不能用通用资金分摊器覆盖它。
- `client_verified`：`outMoneyRP`在帮内按钮仍用于个人“人气”检查，比较角色属性`0x262`；失败消息140418明确说“人气太低”。它不是帮派人气，也不是声望。`inSkillLevel`已绑定工坊熟练度进度条分母；实际服务器学习时是否检查、扣除或清零熟练度仍未知。

以上是客户端证据与离线执行；均不等于原服务器结算、真实NPC准入或GUI验收。未知生产默认由唯一设计来源裁定，本报告没有采用任何新默认。

## 十四种可研究/可列出的生活技能

`catalogs/knight.gsp.skill.clifeskill.json`有49行，恰好以下14行`bCanStudy=1`：

| ID | 原名称 | ID | 原名称 |
| --- | --- | --- | --- |
| 300101 | 武器锻造 | 300201 | 饰品制造 |
| 300301 | 防具打造 | 310101 | 炼药 |
| 310103 | 家具生产 | 310201 | 烹饪 |
| 320101 | 健身术 | 320102 | 吐纳术 |
| 320103 | 强体术 | 320104 | 养生术 |
| 330101 | 暗器术 | 330102 | 追捕术 |
| 330103 | 逃离术 | 370001 | 易容术 |

不是仅凭表名采用：原配置解析器`0xa76b49–0xa76b75`以`bCanStudy`名字读值并写记录`+0xb8`；帮内窗口构造`0x13514d0`遍历原CLifeSkill表，经`0xcfb020`复制记录到局部`ESP+0x2c`，在`0x1351659`检验相应`ESP+0xe4`，零跳过、非零加入窗口catalog。实际执行该原分支输入0/1/9，分别走`0x135168a/0x135166a/0x135166a`。本包实际值是0/1；不将49行全部放入帮内学习列表。七项360001..360007是另一类辅助技能，不能列为这14种生活技能。

## 协议、原类与客户端状态

| 原类/用途 | 协议 | 原地址和布局 |
| --- | --- | --- |
| `CUpdaetAssistSkillLevel@skill@gsp@knight` | `0xc36b6` | vtable`0x227cd10`；ctor`0xdcf280`，marshal`0xe56880`；对象`+8/+c`为Q、`+10`技能、`+14`mode字节。原marshal对NPC=`2**48+1395`、技能300101、mode0..4分别匹配`struct.pack('>QiB',npc,skill,mode)`。 |
| `SUpdateAssistSkill@skill@gsp@knight`，单项更新 | `0xc36b7` | vtable`0x227cfc0`；marshal`0xdd0a80`（内嵌AssistSkill bean marshal`0xe56a90`）；Process`0x12d7270`→`0x12d5ca0`；body为`>iii`技能、等级、熟练/经验。 |
| `SSendLearnedAssistSkill@skill@gsp@knight`，完整列表 | `0xc36b5` | vtable`0x2282b34`；ctor`0xea3bd0`，marshal`0xea4150`，unmarshal`0xea41d0`，Process`0x12d5b80`→替换消费者`0x12d4ac0`；body为compact数量及逐条`>iii`。对象`+8`原list，head在`+c`、count在`+10`；节点next/prev在0/4，AssistSkill vptr在+8，三个数在+c/+10/+14。 |
| `SSendAssistSkillMaxLevels@skill@gsp@knight`，帮内学习面板上限 | `0xc36b8` | vtable`0x22852c4`；ctor`0xf30940`，marshal`0xf30a70`，unmarshal`0xf309f0`，Process`0x1353240`。对象`+8/+c`为Q，`+10`为map容器，head在`+14`、count在`+18`。树节点key/value在+c/+10，nil flag在+15。 |

`0xc36b8`原map按有符号i32键序处理（查找`0x5f1e00`使用有符号比较）；原marshal输出原树中序。实际以原14种ID、各不相同的cap20..33、NPC=`2**48+1394`构造平衡树，原marshal结果恰121字节；独立构造`Q+compact(14)+14×(i32,i32)`逐字节一致。随后实际执行原ctor与unmarshal，消费完整121字节并重建14节点、Q高半保留。这里只把20..33作为数值可区分的夹具，不作为cap政策。

原辅助技能manager全局`0x29448a4`：`+0x74`为树容器，head指针`+0x78`、count`+0x7c`，节点key在+c、等级在+10、熟练/经验在+14，nil flag在+19。`0x134bad0`复制这份树供窗口使用；`0x12d4cd0`查询等级，`0x12d4d40`查询第二值，`0x12d2900`执行原树定位/插入。

本批执行`0x12d7270`完整Process，对300101和360001分别把既有节点改为`(11,123)`；原`0x12d5ca0`在`0x12d6069–0x12d607a`写入真实节点。两次均保留manager`+0x40/+44/+48`的独立哨兵。窗口全局`0x294f32c/330/338/340/33c`设为无窗口，以免启动UI；原Process对这些窗口的刷新调用仍可由静态地址检查。

**完整列表会替换，不是合并子集。** 实际先用原c36b7 Process建立360001=(3,27)，再经原c36b5 ctor/unmarshal/完整Process输入只含300101=(11,123)的列表，最终`+0x74`只剩300101，原360001被移除。适配仅为分配/CRT及空UI回调。故不能将“生活14项子集”冒充完整c36b5快照投递，清掉另一个Owner维护的七项修炼或其他辅助技能；已知14项可分别用c36b7增量表达。若未来投完整c36b5，须先有整个辅助技能命名空间的完整权威快照。

任务窗口的`role_skills.py`当前仅授权OtherSkills manager`+0x40`的5个ID：100007/100008/100009/310202/700004。它的`0xc36c3`完整map协议及新手基线不能复用为生活300xxx档案；反之，本报告也没有授权改写该账本。现有`research_other_skill_snapshot.native_other_skills`可继续独立验证其命名空间，不用生活技能扩充其ID白名单。

## NPC、面板与按钮的原链路

原`cnpcserverconfig`121文字为“学习生活技能”。`cnpcconfig`10076是帮派师爷、模板图1394、坐标39/42；模板及坐标不是实际组织副本准入证明。

1. 原菜单低段switch`0x1636d1c`以服务ID121定位`0x1637b0f`。实际执行原`0x1135590`从角色属性map`+0x164`查属性`0x1ea`等级；29拒绝、30继续。随后原`0x148dac0`使用当前地图模板和64位场景身份，与帮派manager`+0x228`及三份场景ID比较。本批30级+错误scene拒绝，30级+正确本帮64位scene进入`0x1627be0`通用NPC服务调用，实参仍121。**验证停止在通用NPC请求helper入口，没有将其受保护代码后续或完整请求帧称为已执行。**
2. 原c36b8 Process`0x1353240`取得工厂`0x13531c0`的窗口（全局`0x294f330`）。若响应Q不同，写窗口`+0x68/+0x6c`，调用`0x8015e0`，实参是`Qlo,Qhi,1,dialog+4,13`，返回对象再交`0x8013b0`。本批用工厂/登记Adapter返回虚拟对象，实际执行Q比较和写入。
3. 接着原`0x1351ea0`遍历本窗口CLifeSkill catalog`+0x7c`，按技能查响应map，写窗口`+0x88`的最大等级；未返回的catalog技能写0。实际执行已有300101上限7、响应40，得到40，停止在`0x1351f99`后续GUI刷新之前。catalog节点nil flag是+f9，响应上限map节点是+15，不能套同一种虚拟节点。
4. 原控件名`AssistskillstudyInFaction/studybutton`在构造`0x1352398`查找，保存窗口`+0x4c`；`0x13523c5`将回调设为`0x13503c0`。选中技能回调`0x1351b10`从按钮`+0x26c`读ID，写窗口`+0x60`。
5. 学习按钮用`0x134bad0`取个人当前树，计算目标=current+1。`0x13504f0/0x1350501`查窗口最大等级；最大值0或目标高于最大值，走140421。随后按目标等级查成本。成功段`0x1350853`调用原ctor，复制技能`dialog+60`及NPC Q`+68/+6c`，保持ctor的mode0，然后走网络发送。实际从完整按钮入口运行，验证NPC两半1394/256、skill300101、mode0进入发送边缘；没有借此声称服务器同意学习。

个人上限可以与帮派研究程度有关，但c36b8本身是已计算结果，不证明它恒等于某一原研究字段；服务器再加人物等级/特殊阶段等上限仍需原证或明确设计。

## 成本表字段到用途

原`CLifeSkillCost`表的getter是`0x89e8f0`，返回配置总对象`+0xed4`；其虚函数+8按等级查行。原记录解析`0xa76ce0`用实际属性名字取值；本批使用字符串构造/析构与XML属性查询Adapter，将catalog第1/40/155行交给原解析器，执行到`0xa770a6`（vector解析前），所有15个标量均落到以下实际偏移。原记录复制`0xcfbbe0`也实际执行，没有以自写重排函数替换。

| 字段 | 原记录偏移 | 已确认用途/限制 |
| --- | --- | --- |
| `id` | +0 | 目标等级行索引；按钮实际current+1，未以当前级直接查费用。 |
| `outExpCost/outMoneyCost` | +4/+8 | 帮外学习费用存在；本批不据其扩大帮内支付，未绑定全部帮外模式。 |
| `outMoneyRP` | +c | 帮内按钮仍将此数与个人属性0x262比较，失败140418为个人“人气太低”；非帮派人气、非声望。 |
| `outMoneyCostJQDS/outExpCostJQDS/outMoneyJNYS` | +10/+14/+18 | 字段解析已证，对应其他支付模式本批未授权。 |
| `inExpCost` | +1c | 帮内“所需经验”；原按钮与角色`0x2944550`对象+178/+17c的64位当前经验比较。 |
| `inMoneyCost` | +20 | 帮内“所需银两”；预算比较见下一节。 |
| `inBG` | +24 | 帮内“所需声望”数字显示，窗口+3c（名称虽为bindmoney/have1，旁标签是所需声望）；未执行服务器扣款。 |
| `inBangGongNeed` | +28 | 解析有值，未绑定门槛/扣除消费者。不能凭Need命名直接采用为原声望门槛。 |
| `inBR` | +2c | 解析有值，未绑定资源扣除或其他用途。不能凭简称直接采用为资源费用。 |
| `inSkillLevel` | +30 | 工坊打造熟练度进度条分母，取当前等级+1行；不证明学习时消耗/清零。 |
| `mingwenExpCost/mingwenMoneyCost` | +44/+48 | 解析有值，铭文业务另核；不套生活学习或七项修炼。 |

帮内选中详情`0x1350ee0`：原`0x1350fcc`将复制行`inMoneyCost`地址交给格式化`0x1016030`，最终设置窗口+28；`0x1351075`将`inExpCost`交给同一格式化并设置+24；`0x1351116`将`inBG`交给格式化并设置+3c。独立layout中的标签分别是“所需银两/所需经验/所需声望”。原显示“当前声望”的窗口+40另从帮派manager`0x2945570`的`+0x3c0`对象再读+34；未把它与个人0x262人气混为一个值。

| 实际执行目标行 | 银两格式化输入 | 角色经验格式化输入 | 声望显示输入 | inBangGongNeed | inBR | 熟练分母 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3 | 16 | 1 | 5 | 2 | 0 |
| 40 | 2104 | 24535 | 40 | 200 | 18 | 0 |
| 155 | 695472 | 22060446 | 155 | 775 | 64 | 2250 |

这里只前三数实际通过原帮内数字读取切片到格式化实参；后三数的表/解析偏移已证，其中熟练分母另由工坊验证，另外两个业务用途仍未知。

## 总预算、10000门槛与存款提示的精确顺序

原钱包对象全局`0x2944628`：+b0/+b4为银两，+b8/+bc为存款，+c8/+cc为绑银。原显示函数`0x134f530/0x134f630/0x134f730`分别读这三份64位量，设置窗口+30/+34/+38；layout标签明确“当前银两/当前存款/当前绑银”。没有看到可据此另命名为储备金的独立字段。

原帮内按钮中的可观察顺序如下：

1. `0x135054f`先检查个人人气；`0x13505de–0x13505eb`以`inExpCost`比较当前角色经验，不足消息140424。
2. `0x135062d`调用原`0x134f1f0`，按64位加法求银两+绑银+存款总额，`0x1350632–0x135063a`与`inMoneyCost`比较；不足消息140419。
3. `0x1350669–0x135069d`重新取银两+绑银，要求至少10000；不足走`0x135069f`的142514提示。此检查无条件位于总预算足额之后，费用低于10000也不能豁免。
4. `0x13506d6–0x13506e6`检查银两+绑银是否覆盖整笔费用；覆盖即可发送。不覆盖但总预算足额，`0x13506f0`查窗口+74标志；为0则提示141620“需要使用存款”，为1直接进入发送。

实际从完整按钮`0x13503c0`运行的关键矩阵（经验、个人人气及研究上限均足额）：

| 目标/费用 | 银两 | 绑银 | 存款 | 原结果 |
| --- | ---: | ---: | ---: | --- |
| 1/3 | 0、1、2（逐例） | 0 | 10000 | 全142514，不能靠存款绕10000 |
| 1/3 | 3 | 0 | 0 | 142514，费用恰好足也不能绕10000 |
| 1/3 | 0 | 3 | 0 | 142514 |
| 1/3 | 9999 | 0 | 0 | 142514 |
| 1/3 | 10000 | 0 | 0 | 发送mode0 |
| 1/3 | 0 | 10000 | 0 | 发送mode0 |
| 1/3 | 0 | 0 | 2 | 先140419，总预算不足 |
| 155/695472 | 9999 | 0 | 10000000 | 142514 |
| 155/695472 | 10000 | 0 | 10000000 | +74=0提示141620；+74=1发送mode0 |
| 155/695472 | 695471 | 0 | 0 | 140419 |
| 155/695472 | 695472 | 0 | 0 | 发送mode0 |

另执行目标155、上限154拒140421，上限155通过；经验22060445拒140424、22060446足额；第1行outMoneyRP12，个人属性0x262=11拒140418、12通过。上述测试使用真实配置行与原树查询、原预算/分支指令，但钱包/角色属性/配置对象是受控虚拟内存。

窗口+74准确含义是本地“已提示存款”，不是可传给服务器的确认凭据：原`0x135083f`在创建确认框后就置1。确认框登记callback`0x134f0e0`（在`0x13507ad`传入）；该callback检查银两+绑银的10000条件，再从全局窗口的+60/+68/+6c直接构造原c36b6，mode仍0，wire没有额外确认位。因此服务器应重新验证预算/门槛，不伪造第二个确认协议。银两、绑银、存款实际扣除优先级、是否扣后仍留10000，本批没有原服务器证据；客户端前置检查证明的是扣前条件。

## 熟练度的确切绑定及限制

原工坊函数`0x1307850`依据页面类型分别查300101/300301/300201：用`0x12d4cd0`取当前等级、`0x12d4d40`取熟练值，再以当前等级+1查CLifeSkillCost；`0x130791f`读`inSkillLevel`，原浮点指令计算熟练/分母，调用`0x4ba4b0`设置进度。

本批原查询实际返回等级59、熟练125；原表查询收到60，行60的inSkillLevel=250；原进度实参0.5，随后数字格式化分母250。控件由`0x13309ca`以`WorkShop/Euipproduct/back/Materialback/ProgressBar`查找，在`0x1330a13`存窗口+17c；`workshop.layout:646–647`明确“当前熟练度/升至下级所需熟练度”。所以inSkillLevel的分母用途已证；**服务器是否把熟练值作为升级门槛、达到后是否消耗或保留，没有由这个进度条证明。** 初始熟练、成长生产者和购买升级规则仍需独立来源/设计，不把个人熟练奖励交给帮派研究Owner。

## 可复用的离线Interface和最小重放示例

可以直接复用`verify_social_native.native_payload`、`verify_family_donation_native.Native`和`research_battle.NativeBattleDecoder`，不需要改生产模块。下例可在revival用指定Python stdin运行；不会写文件或修改这些helpers的全局CLASSES：

```python
import struct
from verify_social_native import native_payload
from research_battle import NativeBattleDecoder

npc=2**48+1394
for mode in range(5):
    actual=native_payload(0xe56880,scalars=[(8,npc&0xffffffff),
        (12,npc>>32),(16,300101),(20,mode)])
    assert actual==struct.pack('>QiB',npc,300101,mode)
assert native_payload(0xdd0a80,scalars=[(8,0x227cfac),
    (12,300101),(16,11),(20,123)])==struct.pack('>iii',300101,11,123)

# Small explicit map fixture. Complete14 business projection needs known14 caps.
payload=struct.pack('>Q',npc)+b'\x01'+struct.pack('>ii',300101,40)
p=NativeBattleDecoder()
p.call(0xf30940)
p.write(p.stream,0x224c100,p.buf,0)
p.write(p.buf-12,len(payload),len(payload),1)
p.u.mem_write(p.buf,payload)
p.call(0xf309f0,p.stream)
assert p.read(p.stream+8)==len(payload)
assert p.read(p.obj+8)|(p.read(p.obj+12)<<32)==npc
assert p.read(p.obj+24)==1
head=p.read(p.obj+20)
node=p.read(head+4)
assert struct.unpack('<ii',bytes(p.u.mem_read(node+12,8)))==(300101,40)
```

## 方法、Adapter与未验证范围

按Matt `research`追到本包表、原配置解析器、marshal/unmarshal、原Process、原消费数值指令与独立布局，逐条区分存在/显示/预算/结算。按`codebase-design`将角色学习、帮派研究/资源、OtherSkills三个状态权威分开：个人等级/熟练/钱包/角色XP应在角色Owner事务内；帮派只提供当前成员/研究上限与可能的资源预留Interface；不能让Caller提供可信费用或把帮派经验当角色经验。已读取AGENTS、ARCHITECTURE、DESIGN_AUTHORITY和适用Skills；未采用全服锁或改变任何生产Interface。

实际执行范围：两原marshal类型、c36b8原ctor/14节点marshal/unmarshal、单项更新完整Process、完整辅助列表替换Process、c36b8 Process至UI前、帮内按钮至发送/拒绝边缘、服务121 switch与原等级/scene函数、成本原标量解析/复制/格式化输入、工坊熟练度数值切片。没有再次抓取外部网页，本批数值结论不借手游/其他游戏/跨年代攻略补齐。

明确Adapter：分配/释放/CRT memcpy/cookie沿现有helpers；成本解析的wstring构造/析构与XML属性取值返回实际catalog属性；完整按钮配置getter/虚表查行由受控记录提供、原复制/索引/比较不替换；角色属性map、钱包三份余额、研究cap均为虚拟夹具；消息表取到原消息ID即停止，网络发送在完整原请求构造后截获，未发送；c36b8窗口工厂与NPC登记返回虚拟对象，停止后续GUI；c36b5空通知回调适配，原树重建/替换执行。一次max-panel探测因误把catalog节点的+f9 nil flag按普通map+15构造而达到步数限制，修正后明确断言停在0x1351f99，未把前次未完成算作通过。

未验证：真实NPC registry/成员代次/组织MapAddress证明，正式raw路由、原服务器扣费与取整/退款/并发、声望与资源真实消费、熟练成长/升级消耗、人物上限完整公式、生产钱包储备业务、完整GUI或客户端现场购买。个人生活学习缺档不能自动补0；新建角色或显式迁移基线仍须授权。`inBG`作扣费、`inBangGongNeed`作累计声望门槛、`inBR`作资源费、熟练达标但保留等若被采用，必须另标`designed`，本报告没有将这些规则升格为client_verified。

## 实际读取/执行来源SHA256

路径相对`D:/神雕侠侣/revival`。原包CRC本批未重审；下列为实际提取物与helper指纹，后续代码改动不由本文同步覆盖。

| 文件 | SHA256 |
| --- | --- |
| `evidence/native-image.bin` | `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791` |
| `catalogs/knight.gsp.skill.clifeskill.json` | `f7bddc6e74ae9ee7f91b16854cdfa378ced3f01288b8adf390492a1377b54bac` |
| `catalogs/knight.gsp.skill.clifeskillcost.json` | `517f76b0a3f4af5c1028b97f5cecf0ee886707e3f32b890f920772414d92a07a` |
| `catalogs/knight.gsp.message.cmessagetip.json` | `22e8a58ab45a8bb354fa4f1be1250eb61a7ca6e47c5cb0c21890250397ba1400` |
| `catalogs/knight.gsp.npc.cnpcserverconfig.json` | `6ab88d06635ea2905f0994ed12b0bdab503a689cc0d30b247f2587268841d9b3` |
| `catalogs/knight.gsp.npc.cnpcconfig.json` | `cf070e700e37a6d8d350ccb1e4d86610408e5ffcecad4710641cf2d06aca847d` |
| `decoded/ui/layouts/assistskillstudyinfaction.layout` | `ccfd84fdd57a47be0f18e6104329c15e8036c2b5d5e9957b2f52ca5f9da16e05` |
| `decoded/ui/layouts/assistskillstudy.layout` | `3c9e4c15a45bd0def9e5ecd89d1c0506d1215d5c4e21cacdb33290b27796e854` |
| `decoded/ui/layouts/workshop.layout` | `eb541ba7791ab2e2e05b534a24d42cd29f7a99df5e412d72cd17dcc1172176fb` |
| `verify_family_donation_native.py` | `c9a16c862f5f56f16b15a4e78672c787578995c35326b7d20469e9687109c1cb` |
| `verify_social_native.py` | `a5e85ff5ec786c461a55af075b5ecd5c6d40b57da41c6f84bf9116596cae1a80` |
| `research_battle.py` | `4aa276ece9ea4a9f13d9c4f9a0de2900f97cf77ff3783aeecc92e7d5f3a47b45` |
| `research_other_skill_snapshot.py` | `6687f49953f34f387fafdc26d4965aec8aa6511bd0f25b92c279d7dae1a3ff49` |
| `role_skills.py` | `bf36f8dc1968976c0a0e1cf4988624b749fc02cab1246c43484a56c49b219b6d` |

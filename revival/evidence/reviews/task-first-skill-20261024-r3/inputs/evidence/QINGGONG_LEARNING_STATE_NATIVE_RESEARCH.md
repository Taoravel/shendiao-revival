# 教学轻功学习状态：原生分类、同步及消费者

2026-10-24。本批只研究原客户端，未编辑玩法实现、role_skills、共享入口、裁定或原资源；未启动客户端、连接在线服、操作数据库或战斗。

## 结论与实际方法

`client_verified`：原客户端把 **350001「轻功」** 的当前值存入技能管理器 `+0x74` 的 `(level, experience)` 树，使用 `SSendLearnedAssistSkill` 全量同步及 `SUpdateAssistSkill` 单条更新。UI 的「其他技能」展示类 6 混合四种实际容器，不能据其 26 个 ID 全部进入 `SSendOtherSkills` / 管理器 `+0x40`。100007 是九阴白骨爪，100009 是凝神静气，均不能代替轻功。

research 方法用于沿原表→原分类函数→原 Process→实际字段写入→原 getter/原消费者逐级核验；本代理承担后台研究，根代理并行处理任务端点。codebase-design 方法用于区分 UI 展示 Interface 与学习状态同步 Interface：恢复方应在独立学习状态 Seam 管理技能 350001，不能让展示分类成为普通技能账本的准入规则。本文提供资料与原生反馈，不授权学习、扣书、任务完成或世界移动。

## 原始来源与可复现工具

- 原映像：[native-image.bin](./native-image.bin)，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`；以下地址均为该映像原 VA。
- 直接经 `PfsArchive.read`（包含长度/CRC 检查）读取 `artres/config.pfs` 中 `autoconfig/knight.gsp.skill.cskillshowlist.xml`，解压后原 BXML SHA256 `67632b0dc85a979637846c3d1717bac6f75b48d93a9661a381ea92f95931c5ac`。
- 同包 `autoconfig/knight.gsp.skill.cskillshowlistclient.xml`，原 BXML SHA256 `eda1374328a6a2574cc53b6eee53f1e81b144f5d9da44965c89a647940d8d6eb`；350001 行 `skillname=轻功, skilltype=1`。`skilltype` 不等于下述原数值分类函数结果。
- 新独立工具：[research_qinggong_learning_state_native.py](../staging/research_qinggong_learning_state_native.py)，SHA256 `8d77b5f662df281e72f9ed2d47e1f04fbe64f8bc67512d6d3ccc474b30c28015`。执行入口为该脚本；可导入 `native_namespace_rows()`、`native_learning_updates()`、`native_packed_presentation()`。
- 教学三书来源、端游官方资料及历史版本冲突沿用 [QINGGONG_BOOK_SOURCE_AND_GUIDE.md](./QINGGONG_BOOK_SOURCE_AND_GUIDE.md)，本批未重复网络检索。

## N1：展示类 6 的全部 26 个 ID 实际分流

直接原表第 6 行 `classify=其他技能`。下表各 ID 均实际执行原分类函数 `0x1070ea0`，再实际进入存在性查询 `0x12d55f0`，停止于容器查询入口，未伪造查询结果。`+offset` 相对技能管理器，不是服务器数据库字段。

| 原展示顺序 ID | 原数值 class | 实际存在性查询容器 | 运行到的原入口 |
|---|---:|---|---|
| 100008 太祖长拳 | 1 | +0x40 | 0x1090770 |
| 100007 九阴白骨爪 | 1 | +0x40 | 0x1090770 |
| 100009 凝神静气 | 1 | +0x40 | 0x1090770 |
| 310202 做馒头 | 4 | +0x40，先行特判 | 0x108e030 |
| 350001 轻功 | 4 | +0x74 | 0x12d4cd0 |
| 700001 含情脉脉 | 7 | +0x80 列表分支 | 0x12d5677 |
| 700002 深情似海 | 7 | +0x80 列表分支 | 0x12d5677 |
| 700003 感同身受 | 7 | +0x80 列表分支 | 0x12d5677 |
| 360001 | 4 | +0x74 | 0x12d4cd0 |
| 360002 | 4 | +0x74 | 0x12d4cd0 |
| 360003 | 4 | +0x74 | 0x12d4cd0 |
| 360004 | 4 | +0x74 | 0x12d4cd0 |
| 360005 | 4 | +0x74 | 0x12d4cd0 |
| 360006 | 4 | +0x74 | 0x12d4cd0 |
| 360007 | 4 | +0x74 | 0x12d4cd0 |
| 600018 随身商店 | 6 | +0x4c | 0x1090770 |
| 700004 齐心协力 | 8 | +0x40 | 0x1090770 |
| 380001 | 4 | +0x74 | 0x12d4cd0 |
| 380002 | 4 | +0x74 | 0x12d4cd0 |
| 380003 | 4 | +0x74 | 0x12d4cd0 |
| 380004 | 4 | +0x74 | 0x12d4cd0 |
| 380005 | 4 | +0x74 | 0x12d4cd0 |
| 380006 | 4 | +0x74 | 0x12d4cd0 |
| 380007 | 4 | +0x74 | 0x12d4cd0 |
| 380008 | 4 | +0x74 | 0x12d4cd0 |
| 380009 | 4 | +0x74 | 0x12d4cd0 |

合计 `+40=5, +74=17, +80=3, +4c=1`。未在本批所读 `cskillshowlistclient` 找到名字的行保留 ID，不猜补名称。

原静态证据：`12d55ff` 对 `310202/0x4bbba` 特判，`12d5612` 使用 `+40`；其他在 `12d565c` 调用 `1070ea0`，经跳表 `12d5864` 分流。class1/class8 到 `12d56e6` 使用 `+40`；class4 到 `12d574f`，本表除 310202 外均到 `12d578d→12d4cd0`；class6 到 `12d57a5` 使用 `+4c`；class7 到 `12d5677` 遍历 `+80`。class4 另有本表以外的 300401..403 常真及 310102 别名分支，本批不将上述集合外推成所有技能的通用规则。

静态同步对应：`SSendOtherSkills.Process 12d6810→12d60f0` 写 `+40`；`SSendZaxueSkills.Process 12d6850→12d63c0` 写 `+4c`。因此“UI class6 = 原生 Zaxue/class6”及“UI class6 全部 = SSendOtherSkills”均不成立。本表只证明容器选择，不授权将这五个 `+40` ID 全部发放；当前已批准 100008 的范围由原裁定控制。

## N2：350001 当前学习值与原消费者

`12d4cd0` 的 `12d4cd4` 选择管理器 `+74`；键存在时 `12d4d24→12d2900` 查值并返回 `[value]`，缺键返回 0。相邻 `12d4d40` 用同一容器和键返回 `[value+4]`，缺键也为 0。

`13e7f2f..13e7f48` 在轻功 DIY 界面读取全局管理器 `29448a4`，以固定 `350001/0x55731` 调 `12d4cd0`，比较返回值 2。另 `1211a84..1211a97` 用同一 getter 比较 1；`12168c5..1216904` 及 `1217b51..1217b98` 对返回 1、2、3 分别分支。这些是当前学习等级由真实消费者使用的证据。未继续还原各分支的跳跃公式、气力或世界权限；出现 1/2/3 分支不等于证明协议拒绝 4 或客户端对等级强制封顶 3。

## N3：已学辅助技能全量与增量，实际原生反馈

| 类型 | wire type | ctor / vtable | marshal / unmarshal | Process / 状态消费者 |
|---|---|---|---|---|
| SSendLearnedAssistSkill | 0xc36b5 | ea3bd0 / 2282b34 | ea4150 / ea41d0 | 12d5b80 / 12d4ac0 |
| SUpdateAssistSkill | 0xc36b7 | dd0a30 / 227cfc0 | dd0a80 / dd0c30 | 12d7270 / 12d5ca0 |
| AssistSkill bean | 无外层 type | dd0a10 / 227cfac | e56a90 / dd0b40 | bean 值由上述 Process 消费 |

RTTI 均取原 `.?AV...@skill@gsp@knight@@`。**AssistSkill 是实际 bean 名，不能与另一个 SkillInfo bean 混同。** bean 内存 `+4,+8,+c` 是三个 i32；线为 `BE32 skill_id | BE32 level | BE32 experience`，无 vtable 字节。增量包 `+8` 嵌入 bean，字段实际位于包 `+c,+10,+14`，body 共 12 字节。全量 body 是 `compact_count | AssistSkill[count]`，不是 wire map；原包 `+8` 是列表，Process `12d5c11..12d5c31` 按技能键转成临时 native tree，再由 `12d4ac0` 替换管理器 `+74`。

原增量正常分支 `12d6056..12d607a` 以技能 ID 在 `+74` 下标查找/插入，写 level、experience。`310201` 有其他分支，350001 走这里。随后 `12d609d..12d60ce` 另对 350001 且 level1 触发 `12d1420`；本批未执行此快捷表现调用，不凭它推导服务端授予规则。

离线 probe 实际调用原 marshal、原 ctor/unmarshal、原 Process 与原 tree 操作，并在写入后调用原 getter；更新止于 `12d607d`，全量止于 `12d4b27`，均在后续 UI/cache 操作之前。

| 反馈 | 输入 body hex / 内容 | 实际原 getter 结果 |
|---|---|---|
| 敏感性：错误通道 | SSendOtherSkills 把 350001 写成 91 到 +40 | +40 查询 91，+74 轻功等级查询仍 0 |
| 增量 | `000557310000000100000000` | level1 / exp0 |
| 增量 | `00055731000000020000007b` | level2 / exp123 |
| 增量 | `0005573100000003000001c8` | level3 / exp456 |
| 增量 | `000557310000000000000000` | level0 / exp0 |
| 全量 | `0200055731000000020000031500057e410000000500000141` | 350001=(2,789)，360001=(5,321) |
| 空全量 | `00` | 两个键的 level/exp getter 均 0 |

全过程 `+40` 的 350001=91 保持不变。上述 level、exp 和错误通道 91 都是敏感性 fixture，不是恢复服设计数值。全量原消费者会替换整份辅助技能状态，恢复方不能只发一条轻功全量而遗漏角色既有辅助技能。增量与全量 body 均已用独立的原 serializer fixture 比对，不仅由本地编码器自证。

## N4：名字含 QingGong 的其他候选实际是什么

| 候选及原地址 | 已证实字段/消费者 | 对学习状态的含义 |
|---|---|---|
| SRoleChangeQingGong@move，type c0fd9；vtable22791bc，ctor dac290，marshal e50a30，decoder dac330，Process11d78b0 | role u64 + packed u16；解析实体后调用1203de0。该函数将 `(packed>>10)&63`、`(packed>>4)&63`、`packed&15` 写实体字节+21a/+21b/+21c | 三个表现选择字段，不是本批已证的350001等级同步 |
| SRoleQingGongActionList，type c36ce；vtable2282ae8，ctor ea2e10，marshal ea35b0，decoder ea3680，Process1138b60 | 三列表+8/+14/+20交1134d20，分别写自身角色+1c8/+1d4/+1e0的条目；各条目的QingGongInfo有byte键与wstring内容 | 动作/字符串集合，不写管理器+74学习值 |
| QingGongInfo，vtable2282b0c，marshal ea3440，decoder f7b2e0 | bean+4为byte，+8为wstring（内联字符+ c、长度+1c、容量+20） | 与AssistSkill三个i32布局不同 |
| CSetRoleQingGongData，type c36cf；vtable227cc60，ctor dcee10，marshal e567f0 | body三个byte；13e4cc0从三处UI选项取+c0选择值，13e4d53/57/5b写包三字节，13e4d70发送 | DIY选择请求，不是教学书实例或任务结算 |
| SRequestQingGongDIYInfo，type c36d2；vtable227ce90，ctor dcfdb0，marshal e56a50，decoder dcfe40，Process13e90d0 | 单byte，经13e9030选UI，再调用13e7f00；后者自行读350001当前等级 | 请求打开/选择DIY界面的流程，包自身不传当前学习等级 |

原 setter `1203de0` 实际离线反馈：1059→实体三字节 `(1,2,3)`，10392→`(10,9,8)`。原 `cqinggong` 的一段/二段/拖尾配置与 DIY 三选择共同支持表现用途（该语义关联为 `inferred`）；位拆分、字段宽度及消费者为 `client_verified`。本批没有把低4位解释成教学轻功级数，也未声称所有这些协议的全部 UI 行为已经闭合。

## 验证结果、决定与未验证范围

最终 probe SHA 如上。最终统一执行通过：26 条原分类与原查询分流、4 条增量原 marshal/decode/写入/getter、两条全量原 marshal/decode/替换/getter（含清空）、错误通道敏感性、两条 packed setter。仅 heap/CRT 操作复用离线 Adapter；未替换分类、协议 codec 或状态写入指令。空辅助树由原 Process 的 `12d5bbd..12d5bea` 初始化块构造；不把 wire 列表的 sentinel 当树。native Process 分段的外层 UI、cache、定时器及真实进程整链未测。

根代理可据本证据更正只读 catalog/namespace，或将350001同步设计为独立辅助学习状态 Interface；实际写入需角色所有者与持久化事务满足 ARCHITECTURE。**仍 unknown**：三教学书原服务器学习顺序判定、重复学习处理、读条中断/重登规则、经验字段在教学时的授权值、扣物/任务完成原子性、真正服端可跳段数与气力/寻路权限。原客户端能接收level1..3，不能代替这些服端授权。既有 `class6` UI集合不能充当通用普通技能发放白名单，本批不扩大当前仅批准100008的发放范围。

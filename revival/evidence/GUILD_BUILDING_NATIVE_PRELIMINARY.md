# 帮派建筑：下一批原生核验线索

第24批已闭合这些线索：完整原消息、receiver、三算术函数、三控件读取片段和建筑名称均执行通过；正式证据与当前源码见GUILD_BUILDING_NATIVE_BINDING.md、GUILD_BUILDINGS_RUNTIME.md及guild-buildings-current-review.json。本文保留第23批初查时的范围，后文“待”不是最新状态。

读取条件：继续建筑编解码、成本计算与建设事务前。本文是第23批等待审查期间的只读调查；已离线执行三个计算原函数，完整消息/缓存/控件链和正式 codec仍待完成，不属于第23批已审实现。机制与官网来源另见 GUILD_BUILDING_MAINTENANCE_SOURCES.md；下一批绑定完整消费者，再采用数值。

## 发现的原路径

- CChooseBuildConstruct：vtable0x22725c8；构造0xd6b630写type0xc5631；marshal0xe44d10发送bean+8的Q、+10的i32。建筑选择按钮0x14ac980/0x14ac8f0仍须完整执行，Q不能仅凭形状认作组织ID或当前NPC。
- CRequestFactionBuildData：vtable0x224de9c，marshal0x8373a0为空；构造/type及其真实发送点仍须追证。
- SRequestFactionBuildData：vtable0x2282564，marshal0xe92d80。先发+8的i32，再发+0xc的原list；元素FactionBuildInfo vtable0x2282588，marshal0xe92c70发+4/+8/+c三个i32。不要把它当完整c5624帮派详情。
- 原Process0x1495020将消息+8的0..2选择存manager+334，范围外存-1；遍历行中+0xc作为0..2索引，把+0x14存manager+33c+8×index，后半段仍需补取并执行，避免将level/construction次序猜反。
- GangConstruct.layout在原映像0x22b3264；列表名0x22b3230被0x14acc1b引用，构造把列表放dialog+2c。实际列表刷新0x14acee0。0x14ad3ac、0x14ad4d1、0x14ad588分别调用下列三个计算函数，后续列插入代码用于核对需求、资金、人气语义。

## 原计算执行，完整语义仍待闭合

三个函数都读manager+338+8×index，并在该值>=20时返回0。以下已做隔离原指令执行，尚未确认所有业务前置、合法等级及服务端采用范围：

| 函数 | 原指令推导 |
| --- | --- |
| 0x1486d70 | 值<20时返回(值+2)×50，供原列表第四列候选 |
| 0x1486d00 | 值<20，索引0/1/2分别返回(值+5)×100000/300000/400000，EAX/EDX符号扩展 |
| 0x1486d50 | 值<20时返回200，否则0 |

若完整原响应→缓存→列表列与离线原函数执行一致，这些函数可收窄“未发现客户端成本表”的缺口；不能继续仅查catalog后声称所有成本都无原证据，也不能把20分支直接当原服所有建筑绝对上限。12小时资金储备、帮派等级约束、扣款时点和任务代次仍另验/设计。

原Native Adapter执行索引0/1/2、缓存值0/1/4/19/20/21，共18行、每行三个原函数。原值1时结果分别为需求150、资金600000/1800000/2400000、人气200，另独立检查20/21返回全0。结果和原映像hash保存在guild-building-cost-native-preliminary.json，原函数文本另见guild-building-cost-native-disasm.txt；只是计算执行，不是原服费用或全建筑已实现。

静态反汇编：guild-building-protocol-preliminary-disasm.txt。附属guild-details-consumer-fields-disasm.txt记录完整详情raw组向manager的复制；guild-detail-popup-fields-disasm.txt实际为奖励设置/公告弹窗刷新，不是建筑控件，不能据其+2f0读取绑定建筑费用。

## 验证边界

实际方法：research先读包内/官方机制报告，按codebase-design区分建筑Module、角色任务奖励及组织资金所有权；原生静态跟踪和三个计算执行为下一条公开codec/x86 Seam的测试准备。仅产生原指令、计算观察及此线索，未改实现、政策、共享入口、正式库或游戏。完整原marshal/receiver、真实Store/Owner建设状态和GUI均待后续完成。

# 原客户端任务协议证据

本批日期：2026-10-23。研究对象为本项目 `native-image.bin` 映射镜像，基址 `0x400000`。没有使用其他游戏的协议表或推定奖励公式。

采用 research 的一手来源追溯方法：从原 RTTI 定位虚表，以构造函数写入的 type 常量确认协议号，再沿原 marshal、unmarshal 和 Process 确认布局与用途。采用 codebase-design 的小 interface 方法：`../task_protocol.py` 仅承载 wire 编解码，任务条件、存档、奖励与传送决策留在任务模块。本子任务本身就是主任务委派的独立研究，不再递归委派。

产物：`../research_task_protocol.py`、`../task_protocol.py`、`task-protocol-evidence.json`（151 个 task 包协议的静态索引及三项原生解码探针）、`task-native-disassembly.txt`（关键地址反汇编）。JSON 记录镜像 SHA256，运行研究脚本可复现。索引中的其他协议只确认身份和方法地址，未逐一确认布局或可执行语义。

## 可立即接入的最小范围

原客户端使用 `ScenarioQuest` 命名，没有发现名为 SRefreshMission / SAcceptMission / SRefreshMissionList 的主线消息。当前最小只读往返为：

1. 收到 `CRequestQuestCanAccept`，type `0xc4a50`，body 必须为空。
2. 回复 `SRequestQuestCanAccept`，type `0xc4a51`：`compact_uint(count)` 后跟 `count` 个 **BE i32 任务 ID**。空列表正是单字节 `00`。
3. 列表项是原任务 ID，与原配置索引对接；不是 ScenarioQuestInfo，也不携带状态/奖励。由服务端规则决定可接清单，不能把全部配置 ID 当成可接任务广播。

证据：请求构造 `0xdd6ee0` 写入 `0xc4a50`，原 marshal / unmarshal `0xdd6f00 / 0xdd6f10` 直接返回 stream，没有读写字段。回复构造 `0xe72770`（type 写入 `0xe727bb`），虚表 `0x2281b04`。回复 marshal / unmarshal `0xe72810 / 0xe72870` 均把对象 `+8` 交给容器 factory `0x82d360`，后者使用虚表 `0x224dc08`。实际列表 marshal `0x82db40` 写 compact count，再逐项 bswap i32；unmarshal `0x82e0e0` 先读 compact count，循环每次读取 4 字节、bswap 并插入 list。Process `0x125cae0` → `0x125b720` 将该 ID list 写入客户端可接任务列表并刷新显示。

## 主线消息布局

下面列的是 body，外层仍使用项目既有 GNET framing。i32 / u64 均大端；C++ padding 不进入 wire。

| 协议 | type | body 顺序与长度 | 原始证据 |
|---|---|---|---|
| CCommitScenarioQuest | `0xc4a44` | i32 questID, u64 npcKey, i32 opaqueOption；16 字节 | 构造 `0xdd4780`；marshal `0xe57530`；decode `0xdd4840` |
| SAcceptScenarioQuest | `0xc4a45` | ScenarioQuestInfo，24 字节 | 构造 `0xdd8570`；虚表 `0x227df7c`；decode `0xdd8820` |
| SRefreshScenarioQuestState | `0xc4a47` | i32 questID, i32 state；8 字节 | 构造 `0xddbae0`；marshal `0xe58280`；decode `0xddbb80` |
| SRefreshScenarioQuestValue | `0xc4a49` | i32 questID, i32 value1, i32 value2；12 字节 | 构造 `0xddbca0`；marshal `0xe582d0`；decode `0xddbd40` |
| CTrackQuest | `0xc4a4a` | i32 questID, i32 flag；8 字节，flag 限 0/1 | 构造 `0xdd8140`；decode `0xdd81f0` |
| STrackQuest | `0xc4a4b` | i32 questID, i32 flag；8 字节，flag 限 0/1 | 构造 `0xddd2b0`；marshal `0xe586d0` |
| CRequestQuestCanAccept | `0xc4a50` | 空 | 构造 `0xdd6ee0` |
| SRequestQuestCanAccept | `0xc4a51` | compact count + count×i32 ID | 见上节 |
| CQuestDialogEnd | `0xc4a52` | i32 字段；4 字节，任务 ID 用途待后续调用链确认 | 构造 `0xdd6430`；decode `0xdd64d0` |
| CQuestReachScene | `0xc4a54` | 空 | 构造 `0xdd6580`；marshal / decode `0xdd65a0 / 0xdd65b0` |
| STrackedQuests | `0xc4a55` | compact count + 每项 i32 questID, u64 opaque；不是 ID list | 构造 `0xfa87d0`；marshal `0xfa8d00`；map marshal `0xfa8ec0` |
| CRequestReward | `0xc4a87` | i32 opaque；4 字节，不据名字推定可发奖规则 | 构造 `0xdd6fd0`；decode `0xdd7070` |

状态/进度刷新协议对 questID 有原生约束：1001..499999；提交协议为 1001..999999，npcKey 的有符号解释须非负，末 i32 须非负。`SAcceptScenarioQuest` 的原生标量检查仅要求 ID、state、npcKey 非负，未在该 decode 内强制上述任务号范围。

### ScenarioQuestInfo

RTTI `.?AVScenarioQuestInfo@task@gsp@knight@@`，虚表 `0x227df68`；marshal `0xe57b10`、unmarshal `0xdd86e0`：

| wire 偏移 | 类型 | bean 内偏移 | 含义证据 |
|---|---|---|---|
| 0 | i32 | +4 | questID；Process 以该值搜索原任务配置和已接集合 |
| 4 | i32 | +8 | state；状态刷新处理直接写入此字段 |
| 8 | i32 | +0xc | value1；精确业务名称未确认 |
| 12 | i32 | +0x10 | value2；精确业务名称未确认 |
| 16 | u64 | +0x18 | npcKey；用途从场景实体查找调用链推断 |

`SAcceptScenarioQuest` 对象 `+8` 嵌套这个 bean，因此其成员地址相应再加 8。`0xdd8820` 直接虚调用 bean decoder，不额外写入长度或任务号。

接受消息 Process `0x125d5c0` 从消息 `+0xc`（bean+4）取得 questID，经 `0x1257ac0` 检查已接任务。若不存在，将 bean 交 `0x125d070` 放入客户端已接集合。它不是简单的提示弹窗。

进度 Process `0x1258c90` 以 questID 查 bean，直接覆盖 bean `+0xc/+0x10`。因此该消息后两字段是 **两个完整原值**，不能将它们当作 index/value 或增量。

末 u64 在 `0x125d124` 连同原配置 `+0x168` 传入 `0x125a950`。该函数在 u64>0 时调用 `0x11d5260` 按 u64 查场景实体；否则用配置 ID 调 `0x11d1870`，随后 `0x11fe390` 更新标记。故 `npc_key` 是有调用链支持的工作名，非线上的原始字段名，不能把它叫奖励/时间戳。精确 NPC ID 与场景 key 转换仍由世界模块提供。

### 状态值不能由 UI 分类反推

客户端查询 `0x1257b20` 返回 UI 分类：已接任务的 bean.state==3 或特定任务类型 `0x28` 返回3，其余已接返回2，未接返回1。这里的 **返回1/2/3不等于 wire state 的完整枚举**。

`SRefreshScenarioQuestState::Process` `0x125ea00` → `0x125e660`，会根据任务所在集合分派。ScenarioQuest 分支 `0x125c020` 在 state==1 时有完成对话、电影和移除跟踪等副作用（调用 `0x125bb30` 等），state==-2 也有独立分支。不能把 state=1 当成“新接任务”的通用状态。state=3 与可提交阶段相关是合理推断；本批未恢复 TaskStatus 枚举全部含义和各任务类型的合法流转，不自动播状态或串联任务。

### 追踪同步

RTTI 直接包含 `map<int,TrackedQuest>`。`0xfa8b40` 构造虚表 `0x2286380` 的容器 adapter；`0xfa8ec0` 写 compact count，在 `0xfa8f6f` 取 map key、bswap 输出 i32，然后在 `0xfa9000` 虚调用 map value 的 marshal。`TrackedQuest` 虚表 `0x228636c`，marshal `0xfa8c70`、decode `0xfa8a60` 仅处理一个 u64；该 u64 的业务含义未确认。

空 map 是 `00`。非空 map 不能只写任务 ID，也不能把未知 u64 随意当成时间戳。`CTrackQuest` 原 UI 发送入口 `0x15faa40` 在发送前已经修改本地追踪集合；`STrackQuest` 的 Process `0xddd310` 为空函数，所以回复该消息不等于证明已恢复追踪显示。

未发现主线已接任务完整 list 的独立协议。对已经保存的已接任务，可以研究逐条 SAcceptScenarioQuest 的同步方式；本批只证明布局与插入效果，未证明登录阶段的正确发送时序，也未检查 SEnterWorld 是否在其他位置嵌入任务数据。

## NPC 请求补充

| 协议 | type | 已确认布局 | 地址 |
|---|---|---|---|
| CVisitNpc | `0xc2329` | BE u64 npcKey | 构造 `0xdb3450`，marshal `0xe52020`，decode `0xdb3500` |
| CNpcService | `0xc232b` | BE u64 npcKey + BE i32 serviceID | 构造 `0x837400`，marshal `0x83b5a0`，decode `0x8392d0` |

SVisitNpc 身份确认为 `0xc232a`，marshal `0xe701b0` 包含 npcKey 和两个容器；容器元素及任务服务 ID 映射本批未完成，不提供猜测实现。SCantAcceptTask `0xc2337` 为单个 i32，不能据名字擅自广播。

## 验证结果与范围

研究脚本仅执行三个原生标量 decode，无大型场景模拟：

- `0xdd8820` 解析 questID=100184、state=2、value1=11、value2=22、npcKey=`0x1122334455667788`，消费24字节且原样写回相应成员。
- `0xddbb80` 解析 100184、3，消费8字节。
- `0xddbd40` 解析 100184、11、22，消费12字节。

三个 decoder 均执行原镜像代码直接返回，不替换 codec、不调用真实客户端、不发送任务或奖励。Python 编码模块还做了空/非空可接列表、非空追踪 map、接受 bean、提交请求的简短 round-trip 检查。

未验证：原服任务状态机、NPC serviceID、合法提交时机、奖励金额/物品/经验/前置与后继规则、剧情/传送/战斗执行、完整登录任务同步、真实 UI 的网络往返。此处的成功只表示原布局已取得直接证据，不能称为全部任务玩法已经恢复。

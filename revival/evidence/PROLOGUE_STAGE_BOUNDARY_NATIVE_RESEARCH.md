# 序章缺失 Post 终点的原客户端语义

2026-10-24；独立 research 子任务。结论：原客户端确实对 **首个 PostMissionList 元素 `%100 == 99`** 有专门判断，也按任务 ID `/100` 查询当前任务组；本轮未找到足以证明“服务器应将缺失 ID 写入完成历史，并据此自动开启下一段”的证据。不能把这两个客户端行为扩大为原服阶段政策。

## 方法、来源与范围

按 `research` 追溯原始配置、RTTI、原机码调用点，并把实际执行与推定分开；按 `codebase-design` 在独立 staging Module 内放置合成内存 Adapter，Interface 只返回条件分支、查找结果，不接入生产任务状态。已读 ARCHITECTURE/DESIGN_AUTHORITY，遵守角色任务状态的唯一写入者及来源优先级。未委派其他聊天，未运行游戏进程、线上数据库或战斗，未修改 Task/World/Inventory/shared/中央政策。

原始来源（本轮实际读取）：

| 来源 | 精确身份 |
|---|---|
| `D:/神雕侠侣/artres/config.pfs` | SHA256 `eee475d5ffe7eecbde99abc119c2b9b8faa899489e2f7e13533a8de81f40d915` |
| PFS 内 `autoconfig/knight.gsp.task.cmainmissioninfo.xml` 原 BXML 字节 | 2,026,233 bytes；SHA256 `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706`；解码 2,460 行 |
| `D:/神雕侠侣/revival/evidence/native-image.bin` | 基址 `0x400000`；SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`；下文地址均为该映像 VA |
| 独立执行产物 | `revival/staging/research_prologue_stage_boundary_native.py`；复用 `native_inspect.py` 和 `research_battle.NativeBattleDecoder` 的映像/分配 Adapter |

主任务另负责完整原 Post/Request 两层图重盘及 43 门派/角色续段，本报告不把派生图当原生执行证据。仅复核指定 20 个 ID：`100199,100299,100399,100499,100599,100699,100799,100899,100999,103299,101199,101299,101399,101499,101599,101699,101799,101899,101999,103399`，它们均没有原 CMainMissionInfo 行。缺行是 `client_verified`，缺行的服务端用途仍未知。

## client_verified：Post 字段与尾号 99 的真实 consumer

原 CMainMissionInfo 解析器识别 UTF16 `RequestMissionList`（文字地址 `0x226bd88`），在 `0xbb68b7..0xbb68cd` 将其写入记录 `+0x4c` 的整数 vector；识别 `PostMissionList`（`0x226bd44`），在 `0xbb6906..0xbb691c` 写入 `+0x6c` vector。Post begin/end 分别位于记录 `+0x70/+0x74`。这些解析器仅证明字段、顺序和存储，不证明 Request 列表的 OR/AND/自动开启规则。

普通任务刷新路径为 `SRefreshScenarioQuestState`（vtable `0x227e4e0`，Process `0x125ea00`）→ TaskManager `0x125e660` → 普通 Scenario 处理 `0x125c020`。该处理先取定义（`0x125c024..0x125c037`），再调用精确 active getter `0x1257ac0`。**已有 active bean** 时，`0x125c0ec..0x125c105` 写入收到的 state；state=1 进入移除及展示分支。它不能证明服务器何时有资格发送 state=1。

真实条件段 `0x125c1cd..0x125c238`：

1. 定义的 ExpReward signed64 大于 0，进入 `0x125c21f`；否则继续。
2. SMoney signed64 大于 0，同样进入 `0x125c21f`；否则继续。
3. Post vector 非空，原 accessor `0x643e50` 取 **index 0**，`0x125c213..0x125c21d` 执行 `idiv 100`，余数等于 99 才进入 `0x125c21f`。
4. `0x125c233` 调用 `0x174d320`；不满足则跳 `0x125c238`。

字段归属有直接解析器依据：ExpReward 文字 `0x226c54c`，`0xbb5ac2..0xbb5af6` →记录 `+0xa0/+0xa4`；SMoney 文字 `0x226c4f4`，`0xbb5bd6..0xbb5c0a` → `+0xc0/+0xc4`。ExpReward 不是 MoneyReward。

`0x174d320` 的实际实现移除旧 UI 对象，`0x174d3b5` 以资源 ID `0x27e7`（10215）取资源，随后 engine vfunc `+0x120` 创建 UI，存入 manager `+0x54`，分配回调并按视口居中（`0x174d3c3..0x174d444`）。**本轮仅证实这是界面对象创建路径，资源文字/具体视觉含义没有确定**；不能以“章节完成特效”名称代替证据。也没有在这个条件段观察到写完成历史、添加后继任务或发送完成请求。

特别限制：判断对象是 **当前真实任务定义的第一个 Post 值**，不是“收到任意尾号 99 的任务 ID 就完成”。`Post=[100198,100199]` 不满足该分支，不能改为 any/suffix 扫描。

## client_verified：当前任务组查询与精确任务查询不同

`0x1257a40` 遍历 TaskManager `+0x24` 的普通 active 列表，取 node `+0xc` 任务 ID，使用乘数 `0x51eb851f`、有符号移位修正实现正任务 ID `/100`，与查询 ID `/100` 比较；匹配返回 AL=1，否则 AL=0（`0x1257a6c..0x1257ab3`）。此函数没有单独把尾号 99 作为完成标记。

`0x1257ac0` 遍历同一 active 列表，按任务 ID 完全相等返回 node `+8` bean，否则返回 null（`0x1257ae6..0x1257b0b`）。因此有 active `100121` 时，“组查询 `100199` 为真”只证明当前组相同；精确 active `100199` 仍不存在。不能将组查询结果当作 `100199` 的完成历史。

## client_verified：缺失定义 getter 返回默认 bean

`0x89ebd0` 返回配置管理对象 `+0x1050` 的 CMainMissionInfo 表；任务消费者经其 vfunc `+8` 查 ID。原 RTTI `CBeanCacheMemory<CMainMissionInfo>` vtable `0x226e67c` 的 `+8` 为 `0xd390d0`。该缓存构造 `0xd38cf0` 在 `0xd38d58..0xd38d62` 构造内嵌默认 bean，然后将默认 bean 的 id 设为 `-1`。

getter 在查询参数 `-1` 时（`0xd390d3..0xd390e4`），或树查找结果为 end 时（`0xd39117..0xd39125`），都返回 **this+0x10 的同一个默认 bean**。命中才返回树节点 `+0x18` 的记录（`0xd3913d`）。查找函数链 `0xd39020`→`0xd38fc0` 按 key 遍历树。

这解释了为什么“getter 有非空返回值”不能作为“原任务定义存在”的检查；它不代表自动创建任务，也不赋予默认 bean 奖励/后继/状态权限。本轮合成空树执行 getter 仅验证其真实缺键路径，不声称已把完整原表装载进原客户端进程。

## client_verified：可接任务列表由入站协议更新

`SRequestQuestCanAccept` vtable `0x2281b04` 的 Process `0x125cae0` 将 packet `+8` 列表交给 `0x125b720`；后者比较已有列表，调用 `0x730810` 清空 TaskManager `+0x3c` 的旧列表，`0x825860` 复制收到的列表，然后刷新相应 UI/NPC（`0x125b77b..0x125b811`）。这一可见路径是接受服务器下发结果，不是客户端从 RequestMissionList 自行计算可接集。

`SAcceptScenarioQuest`（vtable `0x227df7c`，Process `0x125d5c0`）先用 `0x1257ac0` 拒绝已有 active bean，再经 `0x125d070` 添加；该添加流程先插 bean，再读定义。由此仍不能推导：缺失配置 ID 是否应该被发送、记录在服务器历史，或应该如何激活后续。

本轮只追踪上述普通任务链和任务相关 RTTI 协议名称，未定位到可证明这些缺失 ID 持久化规则的任务历史消费者。**这不是“客户端不存在任何历史消息/Request consumer”的全局否定。**

## 实际隔离执行结果

执行命令：Python `-B -X utf8 revival/staging/research_prologue_stage_boundary_native.py`；正常 exit=0。探针入口固定映像 SHA；真实执行原 vector accessor、idiv 分支、active 遍历及缺键 getter，不以 Python 复写业务条件。只在 UI 函数入口停机，不执行完整 UI/定时器。

| 原机码条件输入（ExpReward=SMoney=0，除标明外） | 实际结果 |
|---|---|
| Post `[100199]` / `[101199]` / `[103399]` | 三者均到 `0x174d320` |
| Post `[100198]` | 到 `0x125c238`，无 UI 调用 |
| Post `[100198,100199]` | 到 `0x125c238`，无 UI 调用 |
| Post `[]` | 到 `0x125c238`，无 UI 调用 |
| Post `[]`，ExpReward=1 | 到 `0x174d320` |
| Post `[]`，SMoney=1 | 到 `0x174d320` |
| active `[]`，query `100199` | 组查询 false；精确查询 false |
| active `[100121]`，query `100199` / `100198` | 两者组查询 true；精确查询 false |
| active `[100121]`，query `101199` | 组查询 false；精确查询 false |
| active `[101121]`，query `101199` | 组查询 true；精确查询 false |
| active `[100121]`，query `100121` | 组查询 true；精确查询 true |
| 合成空配置树，query `-1/100199/101199/103399` | 四者均返回 this+0x10，默认 id=-1 |

合计 8 组 Post、6 组 active（每组运行两个原 getter）、4 组空表 getter；这是原生局部执行，**不是完整 GUI、真实协议往返、真实阶段完成或数据库持久化验收**。本轮未对项目全部测试作完成声明。

## inferred 与 unknown：供主任务设计使用

- `inferred`：首 Post 尾号 99 的专门展示条件、百位 active 分组、以及原表缺行，共同支持“这些终点 ID 可能是组/阶段终止用符号”的解释。它比纯编号规律更强，但尚不足以证明服务器完成标志的存储或规则。
- `unknown`：这些精确 ID 是否原服持久化 marker、由哪一个真实任务完成产生、是否参与任务历史协议、是否作为普通任务实例存在。
- `unknown`：RequestMissionList 多元素的 OR/AND、门派/角色过滤、何时自动开启后续及对应原服数据事务。解析出 vector 不证明列表逻辑。
- `unknown`：UI 资源10215的具体文字/视觉名；全部任务引擎或所有客户端消费者，本批没有穷举。

交接决定：原服上述服务端规则仍 unknown，交主任务按 DESIGN_AUTHORITY 制定 **精确、可替换、来源标为 designed 的阶段衔接政策**，并与其原 Post/Request 续段核对。不能批量完成所有 `%100==99`，不能把任意缺行 ID 发成普通 active 任务，不能仅凭 Request 里出现一个已完成前提就假定全列表 OR/自动激活，更不能将本研究当作服务器已实现或实服已修复。

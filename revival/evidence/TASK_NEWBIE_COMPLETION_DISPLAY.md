# 新手 type50 root 完成状态是否重播电影

2026-10-23，只读原客户端研究。遵循 `AGENTS.md`，已读 `ARCHITECTURE.md`、`DESIGN_AUTHORITY.md`、`design/newbie-opening-v1.json`、`evidence/NEWBIE_OPENING_DECISION.md`。采用 `research`：追溯原资源、原 handler 和必要小段原代码探针，集中写此报告；当前工作本身是委派背景研究，没有再派研究代理。沿用 `codebase-design`：线协议显示效果与章节完成授权/事务 Interface 分开。

## 结论

**在已收到匹配 `CEndPlayCG`、服务端章节已合法提交完成之后，保留 generic TaskWorkflow 的 root `SRefreshScenarioQuestState(state=1)` 下发，不会在所查原完成路径重播相同新手 root 电影。没有必要为了避免该重播而过滤掉 root state1。**

这不是“type50 自动过滤动画”或“客户端记住已播过”的机制：原 handler 不按 MissionType50 判断，而是经共用后续函数按 **AnimationID 数值区间和 RewardMapJumpType** 分流。新手 root 的 11001–11009、11032 均小于 20000，所查播放 dispatcher 会拒绝该区间。完成状态仍会移除客户端 active 任务记录并通知观察者。

对照：古墓后继 type10 的电影 20025、20037、20006、20001 大于 20000，且 RewardMapJumpType=0。在其完成显示 fallback 中会立即调另一电影路径。因此不能把 root 的结论扩展成“所有任务 state1 都不会播动画”。

结论强度：`client_verified` 的静态分支和局部原代码执行；没有真实 GUI、线上包、完整章节运行实测。是否应接受某次 CEnd、匹配 nonce/epoch/任务与幂等事务，仍由已裁定章节 Module 负责；这段客户端显示逻辑不提供授权或去重。

## 一手资源

- 原资源：`D:/神雕侠侣/artres/config.pfs` → `autoconfig/knight.gsp.task.cmainmissioninfo.xml`，本批直接经 PFS 长度/CRC 校验、BXML 解码重读。解压后原字节 SHA-256：`ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706`。
- 原映像：`D:/神雕侠侣/revival/evidence/native-image.bin`，基址 `0x400000`，以下全部为原 VA，使用 `native_inspect.py` 定向反汇编。
- `catalogs/newbie-routes.json` 用于确定本批43条路线涉及的 root ID，再与原配置重新联查，并不单独作为原生控制流证明。

43条路线涉及10种原 root；所有行均 MissionType=50、RewardMapJumpType=0、NoteInfo 空、ScenarioInfoFinishConversationList 空：

| root任务 | ScenarioInfoAnimationID |
|---:|---:|
| 100101 | 11001 |
| 100201 | 11002 |
| 100301 | 11003 |
| 100401 | 11004 |
| 100501 | 11005 |
| 100601 | 11006 |
| 100701 | 11007 |
| 100801 | 11008 |
| 100901 | 11009 |
| 103201 | 11032 |

古墓对照原后继：100184/type10/movie20025、100185/type10/movie20037、100186/type10/movie20006、100187/type10/movie20001；四条的 RewardMapJumpType 均为0。

## 原字段位置核对

| 原字段 | 字段名 UTF-16 VA | parser证据 | config位置 |
|---|---:|---|---:|
| MissionType | 0x226c408 | 0xbb5dec 推字段名；0xbb5e0f 解析；0xbb5e18 存值 | +0x164 |
| RewardMapJumpType | 0x226c4d0 | 0xbb5c1d 推字段名；0xbb5c40 解析；0xbb5c49 存值 | +0xc8 |
| ScenarioInfoAnimationID | 0x226be10 | 0xbb6751 推字段名；0xbb6774 解析；0xbb677d 存值 | +0x2ac |

因此完成 fallback 中的 `[config+0xc8]` 是 RewardMapJumpType，不能误称 MissionType。本文只描述它如何参与原分流，不以这个字段推导服务端传送或地图归属。

## state1 原路径与 active 记录移除

下行 `SRefreshScenarioQuestState`（既有 codec 名也写作 `SRefreshState`）type `0xc4a47`，body 为网络序 `i32 task_id, i32 state`。已知 Process `0x125ea00 → 0x125e660`；ScenarioQuest 分支在 `0x125e6c6` 调 `0x125c020`，随后 `0x125e6cf` 调 `0x10907c0` 通知该任务的观察者。

`0x125c020`：

1. 原表 getter `0x89ebd0` 读取任务 config，`0x1257ac0` 查 active bean。
2. active bean 存在时，`0x125c0f2` 比较 state1，`0x125c0f5` 写 bean.state；`0x125c105` 调 `0x125bb30(task_id)`。该函数在 manager+0x24 的活动列表中按 ID 查找，`0x125bb77–0x125bb8a` 清理索引并调用列表 erase，删除活动记录。该操作没有 MissionType50 特判。
3. 随后刷新 NPC 标记和显示相关集合。
4. `0x125c168` 起检查本地完成对白 vector；非空则 `0x125c19b → 0x164beb0`。否则 `0x125c1a2` 检查 NoteInfo；非空则 `0x125c1be → 0x156d130`。两者皆空时 `0x125c1c8 → 0x1255e70(config)`。
5. 本批10种 root 两种文字都空，确定到达此 fallback。其后的奖励显示、任务观察者刷新等仍保留；本文不建议跳过整个 state1。

如果 active bean 已不存在，而仍收到 state1，`0x125c04d` 起也会按同样的完成对白 → NoteInfo → fallback 次序处理，并在 `0x125c0d6` 调该 fallback；不是“任务不存在就自动忽略完成消息”。所以服务端仍应避免无意义重复投递，客户端不是事务幂等的依据。

## fallback 与电影分流

原 `0x1255e70(config)` 关键分支：

```text
0x1255e75  eax = config.ScenarioInfoAnimationID  // +0x2ac
0x1255e7b  compare eax, 20000
0x1255e82  compare config.RewardMapJumpType, 0  // +0xc8
0x1255e8c  call 0x12550c0(eax)                 // movie > 20000 且 jump=0
0x1255ea3  manager.pending_movie(+0x70) = eax  // movie < 20000 或相应 jump>0 路径
```

新手 root 11001 (<20000) **只把该值写入 manager+0x70，不直接调用播放函数**。原代码仍会读取 config.ActiveInfoNpcID (+0x168) 查场景 NPC 并做显示更新；root 的该字段为0。此报告没有把 pending 槽写入说成清空或消失。

原 dispatcher `0x12550c0(movie_id)`：

```text
movie_id == 0 时，从 manager+0x70 读取 pending
0x12550d2  compare movie, 20000
0x12550d7  movie < 20000 -> 0x125511c 返回
30000 <= movie <= 59999 -> 0x1749260(movie)，随后 pending=0
其他已通过 >=20000 的电影 -> 0x11ca790(&movie)，随后 pending=0
```

所以即使后续以0调用此 dispatcher 来消费刚暂存的11001，仍会因 `<20000` 返回。**11001 此时没有被清槽，而是没有被该 dispatcher 播放。** 原映像直接相对 call 引用发现完成 fallback 的 `0x1255e8c` 和另一路 `0x11e2b46`；后者调用前 `push ebx`，本批未继续还原整个调用方的寄存器来源。本文不宣称已穷举所有间接访问 manager+0x70 的代码。

这个控制流不检查“此前收到过 CEndPlayCG”或“同一 movie 已播完”的标志，因而本次结论基于新手电影 ID 区间，不基于事件历史。已知 `SStartPlayCG` 专门启动 root 的链与本处 dispatcher 不同；章节完成后不得又主动发送一条相同 `SStartPlayCG`，该重复启动不在本报告的“state1不会重播”结论内。

## 必要小段原代码探针

仅以 Unicorn 执行原 `0x1255e70` / `0x12550c0`，使用 synthetic config/manager/stack，拦截 NPC 查找返回空、拦截两个播放调用入口记录参数后返回，不执行真实 UI、地图或电影。每例300条指令以内返回局部终点：

| 入口 | 输入movie | JumpType | 观察到的播放调用 | 返回后 pending |
|---|---:|---:|---|---:|
| fallback 0x1255e70 | 11001 | 0 | 无 | 11001 |
| fallback 0x1255e70 | 20025 | 0 | 0x11ca790，movie=20025 | 0 |
| fallback 0x1255e70 | 20025 | 1 | 无（暂存） | 20025 |
| dispatcher 0x12550c0 | 0，初始pending11001 | 0 | 无 | 11001 |

这四例仅核实已定位数值分支与参数；没有伪造完整客户端运行环境，没有跑战斗或接入当前客户端。没有为本次研究修改生产、共享入口、任务配置或既有协议文件。

## 对集成方的具体影响与未验证范围

- root 完成可继续使用既有 state1 下行以清 active 任务、刷新显示，再同步已在同事务选定的唯一后继；无需新增 type50 的 state1 过滤规则。
- 不能把“CEnd匹配”交给此 handler 推断；它不理解服务端章节票据/epoch，且 wire没有这些字段。
- type10 后继的 state1 可能启动其本地配置电影，不能为了让它立即成为已完成任务而在刚激活时直接发 state1。后继的开始/提交/动画完成授权不在本次小核对范围。
- 新手 root 的已播放身份和章节幂等仍由服务器持久状态控制；pending未清槽是观察事实，本文没有声称内存里删除了所有 root 电影信息。
- 实际 GUI 所见、连接初始化排序、电影自然结束/跳过、真实任务列表刷新、完整新手章节跑通均未验证。这里交付的是原资源联查、静态协议显示路径和局部原代码基本验证。

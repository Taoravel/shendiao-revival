# ESC 开场结束后的“任务已失败”：原生追踪器判据

2026-10-23。本批使用 Matt Pocock `research`：由根任务委派后台研究，沿原资源、原 x86 handler 和必要离线执行建立判据，没有递归委派。已读项目 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY。本文未改任务模块或共享入口，未启动客户端、读取进程、访问现场数据库、部署或执行战斗。

## 结论与最小修复

**当前把 active 任务投影为 `ScenarioQuestInfo.state=2` 会进入原追踪器“任务已失败”分支。** 不是由 ESC 自身、value1/value2 为 0 或 npcKey 为 0 推导出来：原代码只比较 bean `+8` 的 state，等于 2 就把 null data 传入失败显示 helper。该 helper 取原 `CSpecialQuestConfig` 的 1000 行 `tracdiscribe`，其值正是截图文字。

建议统一任务 wire 投影：普通进行中用 **0**，完成清理仍用已核验的 **1**，失败为 **2**，可提交保留已见专门分类的 **3**；其中本批直接执行核验的是 0/2/3 的追踪分流，1 的完成移除见既有报告。不要据此猜测所有任务类型完整枚举或改变持久领域状态的名称。

修复位置应是领域 `active` → wire bean 的转换，同时覆盖初次激活和重连同步。无需修改原客户端、禁用 ESC、重发奖励或重置章节。根任务已独立确认现场 root100101 completed、后继100186 active、chapter completed；本文没有重复读现场或证明图中是哪一个同名任务。

## 一手来源

- 原映像：[native-image.bin](native-image.bin)，基址 `0x400000`；以下地址均为原 VA。使用项目 `native_inspect.py` 定向反汇编。
- 原资源：`D:/神雕侠侣/artres/config.pfs` → `autoconfig/knight.gsp.specialquest.cspecialquestconfig.xml`，本批通过 `PfsArchive.read` 检查目录/长度/CRC，并用 BXML 解码直接读取。id1000 的 `tracdiscribe` = `<T t="任务已失败"></T>`，`aim` 同值，`discribe` 还要求在任务栏放弃再重新领取。这一配置内容不能反过来授权服务器真实放弃任务。
- 原资源同包 `autoconfig/knight.gsp.task.cmainmissioninfo.xml`，本批同样直接读取。100186 为 MissionType10、NPC10014、map1100，`TaskInfoTraceListA` 为“去拜见你的师父”及链接“陆无双”，不是失败文字；root100101 与后继都名为 `[主线]序章缘起`，仅凭截图标题无法区分。
- 原 bean 布局复核依据：[TASK_PROTOCOL.md](TASK_PROTOCOL.md)：SAccept 的 bean state 在 `+8`，wire 偏移4；原 decode `0xdd86e0`，SAccept decode `0xdd8820`。NPC 分类函数与追踪器不是同一判据。

## 精确控制流

### Scenario 已有追踪项更新

`0x160e2c0` 更新入口依次查各类任务；Scenario 分支 `0x160e31d → 0x1257ac0` 查 active bean，非空调用 `0x160daa0`（`0x160e333`）。

`0x160daa0` 先查现有 UI item（`0x160dab0 → 0x51c3b0`）；存在时：

```text
0x160daf5 mov ecx,[esp+14]       ; ScenarioQuestInfo*
0x160daf9 cmp dword ptr [ecx+8],2
0x160dafe jne 0x160db18
0x160db00 push 0               ; null data, deliberately select failure
0x160db02 push ebx             ; existing UI item
0x160db05 call 0x160d560
```

state!=2 则 `0x160db18` 获取本任务 CMainMissionInfo，以该 config 与现有 item 调 `0x160c770`（`0x160db2e`）。`0x160c7af` 使用 config+0x238，即 TaskInfoTraceListA；查 bean 后从 `+0xc` 做 Number 替换（`0x160c80b`），最后 `0x160c8a7 → 0x5200a0` 更新文字。这个正常分支不将 0 值进度解释为失败。

失败 helper `0x160d560`：参数 data 为 null 时，`0x160d5ac` 直接跳 `0x160d765`；后者：

```text
0x160d765 call 0x89ea90        ; CSpecialQuestConfig table getter
0x160d771 push 1000
0x160d776 call eax            ; table lookup virtual +8
0x160d785 add eax,90h         ; tracdiscribe field
0x160d78f call 0x74b0f0       ; construct display string
0x160d7a6 call 0x5200a0       ; set item text
```

字段身份还可由原 parser `0x8927f8` 推 UTF16 `tracdiscribe` 地址 `0x225fbe4`，`0x892807` 目标为 config+0x90 交叉核对。

### 初次构造与后续更新的区别

现有 UI item 不存在时，`0x160dacb → 0x160d2f0` 构造 Scenario 项；构造通过 `0x160d4dd → 0x160c770` 先读取正常 TraceListA。本批没有证明一次完整 SAccept 具体经历多少次观察者回调，但**已有项更新分支的 state2 失败判据已经直接证明**。因此不能仅观察首次构造普通文字就把 state2 视作正确。

`0x1257b20` 是 NPC/UI 分类：只要 bean 存在且 state!=3（并排除原 MissionType40 特例），它就返回分类2。它没有排除失败 state2；所以“NPC 分类返回2”不能证明 wire state2 是进行中。这正是先前混淆的边界。

完成 state1 的处理 `0x125c0f2` 比较1并写 bean，`0x125c105 → 0x125bb30` 移除 active，详见 [TASK_NEWBIE_COMPLETION_DISPLAY.md](TASK_NEWBIE_COMPLETION_DISPLAY.md)。本批不建议改 root 的完成消息，也不建议用 state1 冒充新接任务。

## 可执行红绿判据

独立脚本：[verify_task_tracker_native.py](../verify_task_tracker_native.py)。只在 Unicorn 执行原映像少量指令，synthetic bean/UI/stack；没有运行真实客户端。公开函数 `trace_path(state)` 可接收实际 Owner 返回的 SAccept 解码 state，让集成检查直接复用原判据。

| 原 bean state | 原执行入口 | 观察结果 |
|---:|---|---|
| 0 | 0x160daf5 | 到0x160db18，normal_config_trace |
| 2 | 0x160daf5 | 到0x160d560，existing item原样、data=0，failure |
| 3 | 0x160daf5 | 到0x160db18，normal_config_trace |

另一个 `failure_text()` 从 `0x160d765` 执行原查表/字段选择指令，拦截表 getter 和表查找的宿主适配，只记录所请求行号及最终字符串地址；实际得到 `config_id=1000`、`field_offset=0x90`。随后直接原包读取断言其文字包含“任务已失败”。全部断言已通过。对集成方最小红绿：实际 CEnd 后下发 successor SAccept，原有 state2 → failure；修正投影0后 → normal_config_trace。这个 probe 不自行决定是否应完成章节或授予奖励。

## 未验证范围

没有真实 GUI 复验 ESC、任务列表刷新或 NPC 点击；没有完整模拟 STL/UI/观察者事件循环，也没有证明所有任务状态枚举、所有任务类型或重连投递顺序。持久状态正确不等于显示正确，正常追踪文字也不等于后继任务玩法已完成。上线与现场验收由根任务统一进行。

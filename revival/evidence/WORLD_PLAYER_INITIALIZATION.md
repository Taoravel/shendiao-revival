# 原生主角初始化与入世界字段

日期：2026-10-23（Asia/Shanghai）。本批采用 `research/SKILL.md` 的原始材料交叉核验方法，读取 `native-image.bin` 的 SEnterWorld handler `0x8337c0`，结合已恢复原配置表确认实际查表入口及可用 key。未修改生产服务、客户端或运行态。产物为 `../research_world_player.py`、`world-player-disassembly.txt`、`world-player-candidate.json` 和本报告。

## 最早应避免的零值

`SEnterWorld` 外层对象的 RoleDetail 位于 `+8`。下文将内层 RoleDetail 偏移与 handler 中 ESI 所指的外层偏移分列，防止误写错 8 字节。

| 字段 | RoleDetail 内层偏移 | handler 外层偏移 | 本批证据 |
| --- | --- | --- | --- |
| 等级 | +0x2c | +0x34 | 0x833f0d 使用它查 CResMoneyConfig，返回后直接读 +0x10 / +0x14 |
| 门派 | +0x30 | +0x38 | 0x833967 / 0x833988 分别以它查 SchoolInfo / SchoolMasterSkillInfo |
| 形象/颜色模型 ID | +0x34 | +0x3c | 0x8338d2 开始处理模型及性别 |
| 经验 u64 | +0x40 | +0x48 | 0x83380a–0x83382b 用经验是否大于零设置 global 0x2945438 |

门派两个查表结果分别在 `0x83397a` 加 4 后直接作为 string 使用、`0x83399b` 加 0x60 后直接作为 string 使用；等级查表在 `0x833f1f` 直接解引用结果。前面没有对应的查表失败分支，因此门派和等级不能随意默认 0。

配置类型的原生身份链已确认：

- `0x89e790` 返回全局配置注册表 `[0x2945aec]+0xe18`；注册 `0xd43dc0` 写虚表 `0x225e83c`，创建入口 `0xd0a940` 引用 UTF-16 名称 `0x225e848`：`knight.gsp.role.SchoolInfo`。
- `0x89e7a0` 返回注册表 +0xe20；注册 `0xd43ddc` 写虚表 `0x225e884`，创建入口 `0xd40020` 引用 `0x225e890`：`knight.gsp.role.SchoolMasterSkillInfo`。
- `0x89e660` 返回注册表 +0xd74；注册 `0xd43bb0` 写虚表 `0x225e144`，相邻 UTF-16 名称 `0x225e150`：`knight.gsp.role.CResMoneyConfig`。

这些不是根据函数名或游戏经验猜测，而是同版本注册指令、字符串和 handler 调用交叉匹配。完整范围与映像 SHA256 保存在 `world-player-disassembly.txt`。

## 候选组合的配置验证

`research_world_player.py --verify-candidate` 已对以下组合执行 5 项断言，全部通过：level=1，school=11，shape=1010109。

1. 原 `SchoolInfo` 有唯一 id=11，名称古墓派。
2. 原 `SchoolMasterSkillInfo` 有唯一 id=11，名称古墓派，心法玉女心经。
3. 原 `CResMoneyConfig` 有唯一 id=1，包含 nextexp=89、vimlimit=110 等配置。这里没有把它的字段当作角色初始 HP/MP 公式。
4. 原 `CreateRoleConfig` 的云夕 id=9，color1=1010109。
5. 云夕的原门派列表含 11（另含 15、18、111）。

handler 对形象 ID 有兼容映射：≤10 的旧 ID 加 0xf69b4；11–299 的值使用另一余数映射；≥300 的值直接保留。1010109 走直接保留分支；末位 9 落入性别值 2 的分支（`0x833908–0x83393c`）。因此不能把“建角选项 id=9”直接代替 RoleDetail 中的 color1 模型 ID。

验证结果保存 `world-player-candidate.json`，包括实际配置条目。这证明上述早期必需的 key 存在以及组合在原建角配置中兼容，**不证明整个 renderer 或全部后续场景逻辑已经执行成功**。

## HP / MP 与上限映射

以下映射由 handler 将字段写入属性 map 的实际 key，结合原 `knight.gsp.item.cattributedesconfig.json` 的属性名称核对；同时与主任务另一个角色协议研究子任务的结果一致。

| 字段 | RoleDetail 内层偏移 | handler 外层偏移 | 属性 key |
| --- | --- | --- | --- |
| 当前生命 HP | +0x48 | +0x50 | 60 |
| 生命上限（伤势上限） | +0x4c | +0x54 | 640 |
| 生命最大值 maxHP | +0x50 | +0x58 | 140 |
| 当前真气 MP | +0x54 | +0x5c | 70 |
| 真气最大值 maxMP | +0x58 | +0x60 | 150 |

对应 handler 映射语句分别位于 `0x833a6e`、`0x833c7e`、`0x833c06`、`0x833a8c`、`0x833c24`。不可根据数值相邻关系错误交换 MP 和 maxHP。

本批未取得等级 1 的原版 HP、MP、五维属性及成长计算公式。主任务拟用于本地进图实验的 HP/MP=100 属于明确的实验初值，不能标称原服原始规则。角色等级、形象、门派使用已存在配置；其他未知标量维持已有原生构造/序列化探针的默认值，待行为证据支持后逐项补齐。

经验 0 在原 handler 中触发经验非正的分支并影响新手标志。没有证据支持为了躲过该分支擅自赋经验 1。

## 主角与容器初始化边界

handler 首先检查全局已入世界/处理中标志 `0x2945080`，随后要求 `0x2944550`、`0x2944628`、`0x2944564` 三个管理器存在，否则提前返回。完成角色临时信息与属性 map 组装后，`0x833f99` 调用 `0x113b3e0` 写入角色信息，`0x833fa9` 调用 `0x11da380` 开始主角相关初始化。

`0x11da380` 会注册管理器回调；之后在某全局对象的虚调用状态检查成功时，再将角色信息交给既有角色/场景对象。说明 SEnterWorld 并非一个只靠静态属性就能单独加载地图的消息，后续场景时序仍由主任务另一研究子任务跟进。

本批没有完整仿真 `0x8337c0`，其依赖运行时 UI、管理器、角色、事件和渲染对象；离线把它们清零或替换成假对象将无法证明真实安全性。因此没有声称“未知容器全空必定安全”。已有 `world-layout-probe.bin/json` 的 266 字节探针，只证明原 serializer / constraint 接受其布局和空容器，不代表原入世界 handler 的所有前置条件满足。

保留协议中的空 map / list 表达时，应让正常原生 unmarshal 建立容器头；不要将线上 C++ 容器对象地址或内存零值直接作为 wire 数据。此子任务未更改这些生产实现。

## 本批验证与未验证范围

完成：3 个早期配置注册身份链、等级/门派直接解引用风险、云夕/古墓组合和 3 个查表 key 的 5 项断言、HP/MP 偏移交叉核对；原生反汇编和候选配置输出已落盘。

未完成：完整 renderer 调用验证、原版属性成长公式、所有未知字段含义、场景消息时序、实际入地图或移动。后两项由主任务收集真实运行证据；本报告没有将静态解析成功写作已进图。

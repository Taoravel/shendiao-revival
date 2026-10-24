# Standards 独立审查：可见拒绝提示 P0

固定候选 `2f25815c0badaeb6dd8f5440f4f3e42512a4f6a9ff7955bf9d2796c87c8154a1`。两份新增文件，无 Git；以冻结快照审查，commit 列表不适用。

**P0/P1/P2/P3：0/0/0/0。** 文档硬标准违规：无。完整 Fowler baseline 的可行动判断性 smell：无。

`visible_notice.py` 把可信文案的校验、固定来源/频道和编码集中在单一 Interface，返回 frozen DTO 与 bytes；调用者只传递逻辑消息，未触碰其他 Owner 的可变状态、发送器或数据库，符合 ARCHITECTURE.md 的所有权及逻辑消息投递规则。该 Module 隐藏已验证协议细节，未增加假设性 Adapter。`verify_visible_notice_native.py` 使用实际编码体，经原构造、unmarshal 和同一对象完整 Process 到 ChatManager 入口；只适配文档声明的 CRT/渲染出口，证据与声明一致。

独立核验：2 候选、736 冻结源、4 规格、原生映像和 13 条实际 import 的路径/SHA 全部一致；独立执行原生 4 组通过。另验 1 字符、256 ASCII、256 补充平面字符和混合 Unicode，均与原 marshal 逐字节一致并经原 unmarshal/Process；13 种额外无效输入拒绝，DTO 两字段禁止赋值，执行前后源/规格/映像哈希一致。

方法：code-review Standards 与完整 Fowler 逐项判断；codebase-design 核实纯编码 Interface/Owner seam；writing-for-agents 将接线前提和证据限制共置。独立结果见 `standards-independent/checks.json`。

未验证：真实聊天渲染/筛选/GUI、当前连接及角色代次接线、实际拒绝提示可见性、系统弹窗协议。只证明当前频道 2、sender 0 的 designed 聊天通知编码与消费入口；未接 shared、未发布、未改固定源码。

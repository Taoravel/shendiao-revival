# Standards

2026-10-24。使用 `code-review` 的 Standards 轴；新增文件相对空文件审查，本目录没有 Git 比较或提交历史。冻结 `verify_world_portal_runtime.py` SHA256 为 `c902399b21ddf36ce36987d41e56b097850b54e1d226b55f5136679755eac399`，已实际核对。

结论：**0 项发现**，未发现需要修改的文档标准违背或实质性 Fowler 基线气味。

实际检查：读取根 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY、GLOSSARY；搜索当前非发布/非证据目录，未发现额外 CODING_STANDARDS 或 CONTRIBUTING。逐段检查新增脚本 1–297 行，复核准确候选的 approach/nearby、Peer.take、原 NPC decoder 接缝。每组使用独立临时数据库；真实成员 Location 只用于显式离线采用；共享模块、生产源码和正式服均无写操作。没有增加全服锁/串行执行器；事务由调用方显式开启，未把测试中的直接存储调用当作生产热路径。来源、完整地址和 legacy 未采用状态分开记录；GUI、客户端加载 ACK 与完整寻路均显式未证明，符合 DESIGN_AUTHORITY 的证据分层要求。

只读核对冻结 pilot-adopted.json：验证器哈希与冻结源码相同，两个案例均完成同/冷 runtime 重连，生产 1442 文件及输入稳定。此项是现有报告核对，未宣称独立重跑。末尾 all_passed 仍须与 inputs_stable/production_stable 以及真实进程退出状态共同判断，不能单独当发布凭据。

未验范围：本审查未执行 212 全量、真实客户端、正式服务、正式存档或并发容量；其结果由父任务实际运行证据另证。仅新增本审查文档，未改生产或冻结脚本。

# Standards 复审

硬标准违背：0项。Fowler 判断性问题：0项。

范围仅为本目录固定捕获的 npc_services.py、verify_npc_services.py 相对 base-* 的 changes.diff；不重复此前四文件评审。沿用已读取的 code-review、codebase-design，按 AGENTS.md、ARCHITECTURE.md、DESIGN_AUTHORITY.md 逐 hunk 检查，并检查全部12项 Fowler baseline；没有将启发式当作硬规则。

本次允许纯说明树及10001..10004本地导航，仍在启动阶段校验，仍拒绝本地节点被同NPC绑定为行动。未新增生产绑定、资产写入、热路径读取或共享入口修改。没有足够依据报告新的重复分发、无实际用途抽象或其它味道问题。

验证：从本目录捕获文件优先导入，8项公开检查全部通过；changes.diff与捕获内容重新计算结果一致。未运行客户端、真实库或部署。

证据口径：manifest.json 的哈希是UTF-8文本经LF归一化后的SHA256，与捕获文件CRLF字节哈希不同。base-* 与上一固定目录 current 对应文件经同样文本归一化完全相同。审查基线内容成立，但这些manifest字段不能称为文件原始字节哈希；已向主任务说明，未改动其证据文件。

未验证：真实GUI导航表现、未涉及服务的完整业务、部署状态。上述静态与公开Interface测试不代替现场验收。

# Standards 复审

硬标准违背：0项。Fowler 判断性问题：0项。

范围仅为本目录固定捕获的 npc_services.py、verify_npc_services.py 相对 base-* 的 changes.diff；不重复此前四文件评审。沿用已读取的 code-review、codebase-design，按 AGENTS.md、ARCHITECTURE.md、DESIGN_AUTHORITY.md 逐 hunk 检查，并检查全部12项 Fowler baseline；没有将启发式当作硬规则。

本次允许纯说明树及10001..10004本地导航，仍在启动阶段校验。最终修复还在统一绑定入口拒绝四个导航ID，覆盖没有展示树时的独立行动注册；树内父项继续独立拒绝。未新增生产绑定、资产写入、热路径读取或共享入口修改。没有足够依据报告新的重复分发、无实际用途抽象或其它味道问题。

最终验证：从本目录更新捕获文件优先导入，9项公开检查全部通过，包括四个导航ID的独立绑定拒绝。重新生成LF归一化语义差异，复核新增构造器条件与测试。未运行客户端、真实库或部署。

最终证据口径：已逐一重算两文件base/current四个原始字节SHA256，全部匹配更新manifest.json明确命名的base_bytes_sha256/current_bytes_sha256。原先LF文本哈希与CRLF字节哈希的口径问题已经修正；初轮材料保留于initial目录，不再作为最终哈希结论。base-* 与上一固定目录 current 对应文件的文本内容一致；本轮changes.diff包含换行格式变化，故审查时另行归一化以隔离实际代码增量。未改动源码或快照/manifest。

未验证：真实GUI导航表现、未涉及服务的完整业务、部署状态。上述静态与公开Interface测试不代替现场验收。

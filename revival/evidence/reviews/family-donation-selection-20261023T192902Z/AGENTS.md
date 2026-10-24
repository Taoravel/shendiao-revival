# 神雕侠侣恢复协作

遵循用户长期偏好：每批从 `D:/User/Documents/Codex/.codex/skills/` 读取适用的 Matt Pocock Skills，完整内容仍在上下文时沿用；记录实际方法、决定、产物、验证与未验证范围。全局 Codex 主目录统一为 `D:/User/Documents/Codex/.codex`。

实现或修改服务器功能、状态、并发、数据库、网络投递前，必读 `revival/ARCHITECTURE.md`，按其中状态所有权和接入标准执行。禁止用一把全局世界锁、全服命令队列或全服单线程阻塞执行器保护所有玩法。现有同步恢复代码属于迁移对象。

补全玩法或数值前，读 `revival/DESIGN_AUTHORITY.md`：客户端验证优先，端游攻略其次，仍未知由主策划设计并标明来源。

共享入口的架构迁移由原始复原聊天统一集成；各系统窗口维护所属模块，向集成方提供接口与所需接线，避免同时重写 `serve.py`、`gateway.py`、`accounts.py`。用户当前指令优先。

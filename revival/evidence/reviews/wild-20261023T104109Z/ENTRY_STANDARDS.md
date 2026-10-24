# Entry Standards

补审实际入口，与原7文件纠正审查分开。固定候选wild-20261023T104109Z；基准按entry-scope.json：game_runtime/runtime_storage用shared-resource current，其余用旧release，wild_runtime_storage按新增。5个候选及4个基准哈希匹配。

硬规范缺陷1项：[P2] game_runtime.py:844–853，非终局checkpoint失败保留pending后，断线close只重试旧pending，忽略close操作；成功重试仍finished=None，不移除rt.battles或关闭战斗邮箱。disconnect:1173–1180只关闭角色邮箱，遗留旧战斗。应先完成pending持久化，再处理close，明确释放旧BattleOwner。依据ARCHITECTURE“数据库故障触发局部超时、背压和恢复”。

判断性smell 0项。沿用code-review十二项baseline与codebase-design所有权/Seam；读取上述5文件完整接线及关闭上下文。SQL/配置走工作线程/启动，终局先checkpoint再同事务结算后返回消息。仅静态读取/哈希；未运行DB、战斗、服务或GUI，未验部署和容量。

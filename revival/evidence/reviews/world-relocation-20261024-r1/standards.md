# Standards

2026-10-24。重读 `code-review` 与根 AGENTS，沿用 ARCHITECTURE、DESIGN_AUTHORITY、GLOSSARY，并重读 ADR0001。按真实 `git diff --no-index before/world_owner.py after/world_owner.py` 及新增文件空基线审查；无提交历史。搜索未发现额外 CODING_STANDARDS/CONTRIBUTING。完整 Fowler 基线均作为判断启发式，项目约束优先。

结论：**0 项发现**。

已实际核对 before Owner SHA `9a701d8e8eb4de138f66e553eedbbf37dcb2d80a89453c948bdbe518ca906e4f`、after Owner `b38aacb55911568c724e0288c288a438acacc41ad2d4c34d7224342a7c471339`、新增 verifier `a8c40653110f580e90512a00b0ecda641c5158cc56fe29b4dcddfaada5756c82`。检查状态转换、成员投影与 ready/leave/move 接缝：当前位置仍仅由本 MapOwner 的角色记录持有，不创建假实例或第二成员槽；决定记录按本地图 transfer_capacity 有界并计入空闲门槛。metadata 撤销许可代次、Owner冷建证明、精确回执重试与旧位置拒绝均在本Owner同步命令完成，没有全服锁、跨Owner等待、文件/DB/网络热路径。

全 AOI 变更仍通过其公开预检/编码 Interface，在可能失败的投影更新成功后才发布地图位置；ready 容量失败保留loading。新增交接文档明确SQL、恢复、实际发送屏障、shared接线和入口政策未实现，未将Domain能力写成运行服/玩家入口已修复，符合证据分层要求。

独立执行同SHA工作区 `python -B revival/verify_world_relocation.py`，8组全部通过，运行前后Owner与verifier SHA不变；重生成报告与冻结报告字节一致。范围覆盖冻结/提交/取消、许可与冷建围栏、回执预算及空闲回收、另一实例独立、全AOI失败原子性和热文件I/O封锁。

未验：SQL原子提交、崩溃/新租约恢复、真实连接generation和发送屏障、shared运行时、1627玩法政策、住宅语义、原生现场与容量。未修改生产/shared/冻结源或服务；仅新增本文及执行已授权隔离验证。

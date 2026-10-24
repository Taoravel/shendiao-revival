# Standards

2026-10-24。沿用已读 `code-review` Standards 轴、根 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY、GLOSSARY、ADR0001及完整 Fowler 判断基线。依据真实冻结 r2 before→after 的 `git diff --no-index`；初版冻结与报告保留，不假称提交历史。

结论：**0 项发现**。

实际核对 after Owner SHA `a454134ec3d274e5c6203b66adea9364f10a42563bf7fbdc2c83ed1865a693ac`、verifier SHA `eedf6c8c1c4ba600104bf425c9992b4786d856991ba2ce2bf349410919536f3e`。逐段审查新增 Detached 标记、退出/清源/提交接缝与 preparation_id：标记仍封装在本地图单写者内，保留原不可变终态回执及容量占用，退休只认精确原回执；不保留另一份位置权威，也不以位置version代替新成员身份。每次新准备生成独立操作身份，pending精确重试沿用原身份，避免原回执释放后同请求重建复活旧回调。

退出扫描受既有本地图 transfer_capacity 上界约束，原地替换字典值不改变枚举规模；无新全局索引、锁、队列或跨Owner等待。新增接线在投影校验/更新后执行，未引入文件、数据库、网络或SQL热路径。文档明确只完成Domain，未把围栏修正表述为shared运行时、入口政策、现场或持久恢复已完成。

独立在同SHA工作区执行 `python -B revival/verify_world_relocation.py`，10组全部通过；执行前后Owner/verifier哈希一致，重生成报告与r2冻结报告字节一致。原8组及bare/paired commit/cancel同值重入、回执退休后同请求ABA检查均绿。未改生产/shared/冻结源或运行服，验证仅再生成相同内容的隔离报告。

未验：真实SQL与重放持久化、崩溃/重登恢复、连接代次发送屏障、共享集成、1627/住宅入口政策、真实客户端及容量。Spec轴的修复结论由独立Spec报告提供；此处仅报告Standards轴及实际复跑证据。

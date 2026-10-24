# Spec review

结论：0 个可行动发现（P0/P1/P2/P3 均 0），无阻塞。

基准为家族维护批14及已核验的旧 guild_runtime；按 candidate.json、since-family-maintenance.diff、spec.md 审查9个 changed_files，采用固定文件快照代替本仓库不存在的 Git 历史。这是独立组织增量，不是36632发布激活单。

按 code-review 的 Spec 轴检查缺失/部分要求、范围夹带与实现错误；按 codebase-design 检查冻结事件、小 Interface、同帮派顺序与跨所有者等待；按 writing-for-agents 核对完成条件与限制。已读 ARCHITECTURE.md、DESIGN_AUTHORITY.md、FAMILY_DEVELOPMENT_RESEARCH.md。未发现当前增量违反具体规格：

- “晚到事件不得删除新代次关系”“不会凭缺失记录填零”：guild_dissolution.py:102–168核对源outbox、完整家族代次与成员token，同事务清帮派声望/权限、断关系、继任和凭据；guild_projection.py:130–159在推进cursor前兑现pending新加入者的明确基线，已消费缺档仍拒绝。
- “保留历史组织ID、原帮主外键、资金和账本”：终局仅保存生命周期、返回有效帮主0；新日常操作/聊天/投影被拒绝，旧resolve_practice可恢复。继任次序和资金处置集中标为designed。
- “等待帮派期间不占用家族所有者”“仅完成帮派阶段”：目录有16分区、索引/限量/游标、合并与总容量；帮派先提交，家族独立核凭据ack，outbox仍pending。重试重建原成员退出通知，收件人重查当前组织。Delivery背压会断开慢连接，符合架构允许策略；不将入邮箱等同GUI已见。

验证：独立复核9个候选、574个依赖及142个实际导入Module哈希未变，未导入未固定工作区代码；核阅固定源14项脚本全部exit0的报告（新解散14组及13项回归），未重复大回归。另独立运行两项临时库检查：迟到旧退出不覆盖后续有效组织scope；无帮派ack只完成guild_done、仍保留整体pending，均通过。

限制：未验在线服/真实GUI、商业容量或跨库事务；角色任务、物品、地图清退及建设/Boss/帮战明确不在本批，不能以本报告声称全量恢复。未改生产源码、候选、共享入口或启动游戏。
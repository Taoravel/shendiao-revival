# Standards

结论：**Standards 0**。未发现可行动的硬性规范违规或 Fowler heuristic 问题；P0/P1/P2/P3 均为 0。

范围：`candidate.json.changed_files` 的7个增量文件，对照 batch17r2 的固定 baseline 与 `since-family-donation-r2.diff`；无Git，以冻结前后文件、差异和哈希清单代替提交范围。独立核验7个候选、614个依赖源码、11份规格/约束、636项只读资源及资源清单/差异哈希，全部一致。

依据：本目录冻结的 `AGENTS.md`、`ARCHITECTURE.md`、`DESIGN_AUTHORITY.md`、`FAMILY_DONATION_ROOT_DECISION.md`、`FAMILY_DONATION_NATIVE_HANDOFF.md`。沿用完整 code-review、codebase-design、writing-for-agents；Fowler baseline仅作判断，仓库规则优先，工具强制格式项不重复报告。

实现核对：选中项通过既有公开codec进入冻结窗口校验，限定数量/唯一正key/总量；预留将选择纳入持久body及fingerprint，付款只消耗该角色当前真实携带的指定银箱，短缺或异物不会替换其他箱子。旧count-only预留仍保持旧body和fingerprint。新增纯Adapter无数据库连接、发送或所有权，原角色/家族事务职责未改变。FamilyView保持旧构造名称兼容，64位标识仅由可信调用方投影，不从模板、家族ID或入包推导准入。原指令验证明确隔离CRT、网络和对话框Adapter，未等同真实GUI。

唯一数值配置与上批相比仅 `numeric_review` 元数据改变；还独立重算批准前政策投影SHA，匹配根裁定的 `9d04099d…e2246`，未改奖励、阈值、选择默认规则或声望投影公式。新Module集中窗口/选择的共同校验，未发现有证据的重复抽象、职责分散或额外写者。

独立验证：从固定source运行 `check_scene_identity`、`check_window`，以及临时库中的 `check_selected`、`check_no_substitution`、`check_persisted_selection`，全部通过；覆盖公开Interface的选择、拒绝、持久重试和结算。未启动游戏、真人数据库、服务端口或部署。

限制：主任务18脚本完整回归仍由其记录，不冒称本轴全量重跑。原296历史窗口值、实际驻地准入、共享激活闭包、正式资源precommit、真实GUI及生产容量仍未验收。本次仅写本报告，不修改候选或历史快照。

Standards 总计：0；最高严重级别：无。

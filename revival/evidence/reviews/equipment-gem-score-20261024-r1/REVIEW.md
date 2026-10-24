# 宝石评分候选与显式基准固定审查

非Git固定清单，6个新增owned、1,329依赖；diff SHA `7262f905d9e0508bf2d182a789b1d3e946372d2f6c8942cb159819cdb426258b`。此片是明确designed候选及基准来源，不代表原普通宝石评分公式或收费玩法已还原。

## Standards

[独立报告](standards.md)：硬规则0、启发式0。配置启动冻结、角色当前租约、调用方事务、不可变且不隐式补档的pre-gem基准符合规范；no-change纯投影只验证当前来源，不保存虚构下一宝石状态。

## Spec

[独立报告](spec.md)：缺失/部分0、越界0、错误实现0。原分基准+当前设计贡献重算、颜色使用原阈值、保留耐久/其他字段、错来源和溢出拒绝符合候选合同。未将400/420原强化系数冒称宝石原式。

两轴各独立运行两个verify，全部PASS；均先核固定1,329依赖/diff及6scope SHA。父复跑两个verify、四Python编译，前十个既有生产SHA保持。

未验：公开score/color writer、收费/工具/资产结算控制器、root完整宝石属性/资源、共享入口/发布/真实GUI。原公式仍unknown。全量目标active。

计数：Standards hard0/smell0；Spec0。仅本片通过。

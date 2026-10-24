# 等级等待任务与角色条件奖励

2026-10-23。本批方法：research按原包/原显示分支核实；codebase-design将可信等级、任务计划和分渠道奖励保持在原Seam；diagnosing-bugs先用最小失败检查复现全11项误发；writing-for-agents记录以下实际调用与迁移分支。没有改共享入口、在线库或当前客户端。

## 等级等待接口

原证据TASK_LEVEL_GATE_RESEARCH：30条type58中28条明确等级目标，209302是手机绑定、224302目标未明。当前supports_level_gate支持其中19条无额外动画的原任务；9条含600xx效果，需要后续效果授权流程，不把等级达标当全部演出/选择已完成。原门槛、零奖励、非零奖励、后继、角色列表和字段均保留。

`TaskDomain.plan(...,'wait_level',task_id)`是服务器专用章节激活，允许未达MinLevel先等候，仅适用上述能力查询；普通offer/accept的等级约束没有放松。唯一支持后继的既有chain政策已能激活等级等待；多分支、未确认前置和其它类型仍保留pending。不能由客户端ID开任意等待任务，也不播种全表。

角色所有者在真实成长、章节激活或重连的同一租约事务调用`advance_level_gates(db,account_id,role_id,epoch,resources,inventory,...已准备reward rules,budget=32)`。它从事务内当前role读取等级，只完成已激活且达标的目标，复用任务/人物/资产/宠物/钱币共同结算；不接受客户端声称等级，也不将CRequestReward活动包接成任务领取。budget最大32，ready_remaining非空时由该角色有界邮箱继续，未另设全服队列。

重登bean及progress消息将value1写当前权威等级，value2为本恢复流程未使用的0。原跟踪Number读value1，并不会自动读角色等级；没有伪造需求数或给其它类型套该解释。commit后才发level_gate_messages；state1已有原NoteInfo/完成对白显示，不另造提示包。自动检查时点和>=比较是inferred/designed，非原服程序已恢复。

verify_task_level_gates通过：原102061在17级等待与显示17，伪称18不能越过当前actor；权威18后原0奖励完成一次；原102094的10000XP与任务/凭据随外层失败回滚。结果task-level-gates-check.json。共享成长/登录触发点、9条效果任务与真实追踪UI未接/未实测。

## 角色条件道具修复

原最小失败：verify_task_reward_variants在220902、未给角色选择时报告“all11 configured rows granted without a role selector”。三个候选解释是漏接selector、仅展示列表、尾部共用；TASK_REWARD_VARIANTS_RESEARCH的原过滤循环/getter及185原生用例证明：1..10按建角角色行过滤，同下标取数量/绑定；缺项/<=0/>10条件保留，尾部为共用。221002是乱序映射，不能简单按第N项选。

TaskDomain在首次完成计划冻结reward_item_selectors与reward_role_config_id，TaskPersistence与原效果/请求凭据一起保存。TaskRewardPlan保留全部display_items原值，只有实际获选下标进入Inventory；220902形象1获36671+32029，形象10获36670+32029；221002形象1获36735+31253，形象10获36739+31253。原绑定仍按原获选下标，未因此更改实例绑定。

人物/钱币/宠物渠道沿原source fingerprint，条件物品另有包含selector、冻结角色及选中下标的item_fingerprint；不会因修复选择器而重付旧人物经验。旧completed缺冻结选择的条目保留explicit_role_reward_reconciliation，未解析角色身份保持pending。旧版已经全发的物品凭据不能自动重发或冲销，须显式审计迁移；没有从当前形象推断旧领取者。

verify_task_reward_variants通过四个原角色端点和共用尾部，真实临时背包绑定入账一次；固定形象1后即使当前角色形象9仍只得原1的结果，重试不重复。结果task-reward-variants-check.json。角色选择时点为design，原过滤/身份对应为client_verified；真实UI与历史误发修账工具未验收。

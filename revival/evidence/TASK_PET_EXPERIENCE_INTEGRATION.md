# 任务宠物经验与人物成长刷新接线

2026-10-23。此文是本窗口的实现交接；不代表当前运行进程已加载，也未做原客户端实测。原奖励量/消息布局与补全规则分别见TASK_PET_EXPERIENCE_RESEARCH.md、TASK_PET_EXPERIENCE_DECISION.md、design/task-pet-experience-v1.json。先前“宠物经验全待定”记录保留为历史，现仅旧账和明确未决分支继续pending。

## 集成顺序与完成条件

1. 启动时加载`task_pet_experience.load_task_pet_experience_rules()`为只读依赖；现有`prepare_reward_storage(db)`已一并准备新表`task_pet_reward_decisions`。准备发生在启动阶段，不在网络收包或单次奖励热路径执行。Inventory由所属窗口启动prepare并注入。
2. 角色所有者在原事务调用`complete_task_transaction(...,pet_experience_rules=rules)`。仅库内active的新完成创建选宠记录；位置、NPC或胜利等可信证据仍由原有TaskDomain/TaskConversation验证。内部在人物经验变化前读取当前人物等级和`Inventory.selected_fighting_pet(db)`，资格、原amount、pet id/template/profile/state/version、uselevel、cap和policy均冻结落盘。
3. 任务、选宠记录、人物成长/属性/伤势、道具、钱币、宠物成长及各渠道凭据同事务提交。异常由调用方整笔回滚。宠物调用`Inventory.change_pet_growth(...,'experience_capped',(amount,cap))`，稳定键`task:role:task:PetExpReward:pet`，cap进入宠物模块指纹；本模块不实现另一套成长曲线。
4. 提交成功后，角色邮箱保持顺序，在新的租约校验事务调用`refresh_completion_pet(db,actor,completion,inventory)`，用返回的新completion生成`completion_messages`。该步骤通过公开`Inventory.read_pet_state(db,固定pet_id)`读取当前冻结PetState，不选当前参战宠、不使用历史经验回执。事务内的首次结算结果刻意不携带可直接发送的宠物快照；省略此步骤就不发宠物刷新。
5. 当前连接/epoch仍有效后，把逻辑消息交连接所有者顺序发送。宠物完整刷新0xc07d5后接0xc07d6：BE32固定key+BE64当前剩余XP。人物经验、钱币依旧发送结算末尾的当前绝对余额。角色Mailbox需覆盖结算、后置读取和投递决策，旧回调不得覆盖新epoch。

本批未修改serve.py、gateway.py、accounts.py、game_runtime.py、runtime_storage.py；上述规则注入和提交后读取由原集成窗口完成。任务模块不再读取inventory_pets或调用Inventory私有方法。

## 重试、终态与核对分支

- 原0：zero终态，不选宠、不改成长版本。原549条非零字段可走此渠道，但只有可信完成才执行，不表示549条玩法已恢复。
- 无参战宠、死亡、人物低于原uselevel、宠物超过完成前人物+5：not_awarded终态，保留原amount及原因。后来买宠/切宠/升级不重领。忠诚寿命不加为此经验渠道的资格条件。
- 合格：cap=min(150,完成前人物等级+5)，到cap存剩余XP。金额不均分、不倍率、不转人物XP；超过2147483647拒绝整个事务。
- 原成长未知：保留固定pet id，pending explicit_pet_baseline_reconciliation；后来初始化成长也不自动认定当时资格。首次完成未注入规则同样冻结信息，待显式迁移，不按后来状态补资格。
- 已completed但缺接收者决策：pending explicit_recipient_reconciliation，结算不会调用selected_fighting_pet。历史已付人物/道具/货币凭据继续防重。
- 固定宠后来缺失/放生：pending original_recipient_unavailable_audit，原pet id和已付凭据保留。未支付宠的成长/profile/version在捕获后变化也保留audit，不重选。政策、原amount或选宠记录指纹变化拒绝，需显式迁移。
- 一次性角色+任务ID是当前实例键；周期任务先实现周期实例，再开放重复领奖。核对分支尚无自动修账工具。

`TaskRewardReceipt.pet_experience`为冻结结果(status/reason/amount/recipient_id/current_pet)。pending进入effect.reward_pending；zero/not_awarded/awarded解决该渠道，但不清除钱币、声望、动画、传送、复杂后继等其他待办。后置刷新发现宠物已缺失时只返回显示侧audit；持久化渠道的历史支付事实不撤销，下次settle会记录当前pending审计。

## 人物成长普通刷新

主策划维护的role_attribute_protocol.growth_refresh已核验普通0xc32c8字段路由。complete_task_transaction仅对已有显式属性基线读取当前GrowthState与RoleAttributeSnapshot，在事务内预编码19项：等级490、潜能500、五维、攻防命中躲闪速度、当前HP/MP及上限、伤势上限640。消息冻结在TaskCompletion.growth_messages，completion_messages在提交后返回；未显式启用属性基线则为空。

浮点不能精确表示或原生范围异常在提交前拒绝并回滚奖励。640=maxHP是当前无伤势恢复profile的designed值；不会因此回血。SLevelUp的单BE32 no-op未使用。来源与原字段证据见ROLE_GROWTH_UI_RESEARCH.md及role_attribute_protocol.py；本批没有改其实现。

## 方法、产物与必要检查

codebase-design：将选宠、资格、冻结记录、防重及审计集中在task_pet_experience的小Interface；宠物曲线和实例读取留给Inventory公开Interface，角色交易仍由调用方所有。writing-for-agents：启动、首次完成、重试、历史核对、提交后刷新与失败分支共置，完成条件是必要检查与接线步骤可复现，不以“找到字段”代表完整玩法恢复。

产物：task_pet_experience.py；task_rewards.py/task_workflow.py新增可选pet_experience_rules、冻结结果与刷新；verify_task_pet_experience.py及task-pet-experience-check.json。未改主策划参数和宠物Implementation。

必要检查使用临时数据库：原210002只发10000宠物XP一次；25级宠在人物20的cap25存经验；切宠和后续另加7XP后刷新固定key当前10007；放生后留audit；人物5→10仍用完成前cap10；+6/无宠/死亡/原uselevel5排除人物1；未知旧成长及旧completed无记录保留核对；原100192的0不改宠成长；溢出回滚；道具渠道在宠物/人物经验后故障仍全部回滚；19项人物刷新预编码及float精度错误提交前回滚。相关工作流、四段原对话续接、奖励和货币必要检查通过。

未验证：运行时规则注入/后置读取部署、原客户端宠物经验/人物属性界面、并发容量、商业数据库和完整任务玩法。没有操作在线角色、运行战斗、重启服务或打开客户端。

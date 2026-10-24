# 明确后续任务与成长属性接线（2026-10-23）

本批沿用codebase-design：任务续接为纯决定加调用方事务，属性基线与成长快照单独持久化，所有网络输出仍为提交后的逻辑消息。writing-for-agents用于本文件的接线顺序与完成条件。用户要求批量优先，仅保留连续任务和状态写入必要检查。

## 已完成的任务续接

`task_chains.py`使用原PostMissionList，只自动激活唯一、已存在、角色/等级符合且没有未明RequestMissionList的普通type10对话后续。每条原始关联仍保留。多分支、缺失定义、循环、未知前置、动画/战斗/交物/计时等记录chain_status/reason，保留pending，不跳过到更后面的节点。已经接取或完成的节点不重置。

该自动激活顺序为designed恢复策略；关联字段和任务内容来自客户端，不声称完整恢复原服前置算法。没有为角色自动播种起始章节或开放全部任务。

`complete_task_transaction`现在在原完成/奖励事务里调用续接，返回新增started_tasks；`completion_messages`追加原SAcceptScenarioQuest bean，只通知新激活的普通任务。重试不会把已完成后续重新显示为进行中。续接用奖励后的新角色等级重新评估资格，不沿用升级前TaskActor。原effect的奖励和其它剧情待处理状态保持独立，已接后续不代表其它隐藏/传送字段已处理。

`verify_task_chains.py`验证原序列100192→100193→100194→100195连续完成，同事务激活和原生消息，累计1000人物经验一次；后续100113战斗保持pending，原关联不丢。结果见task-chain-check.json，尚未真实客户端实测。

## 显式属性基线和当前快照

主策划维护role_attributes.py/design/role-attributes-v1.json；本窗口未修改它们。物攻公式为主策划designed，命中110不当成攻击使用，其余系数组合成增量也按裁定标注。

新增role_attribute_storage.py：

- prepare_attribute_storage(db)：启动建表，不创建角色数据。
- initialize_attribute_baseline(db,account_id,role_id,epoch,baseline,growth,rules,vitals)：租约事务内登记一份显式AttributeBaseline及当前VitalState。baseline.level必须匹配growth.baseline_level，五维与基础属性必须来自该基线时点；不能把已经成长后的当前属性伪装成初始值重复叠加。旧角色缺少历史基线时保持未启用，不能自动套新角10点五维等设计值。
- read_attribute_snapshot(...)：返回冻结RoleAttributeSnapshot(attributes,vitals)，检查当前角色等级和成长版本，过期快照拒绝发布。
- sync_growth_attributes(...)：在同一成长事务派生并保存新快照；已登记基线但缺规则时明确失败，配置版本改变需显式迁移。没有登记属性基线的角色保持原先行为。
- update_role_vitals(...,before,after)：将可信战斗/消耗品结果以完整前态和版本+1检查保存；最大HP/MP必须与当前属性一致。该入口不能接客户端自报HP/MP。成长将保留最新伤势，而不是登录时旧伤势。

## 成长与任务接线

1. 启动加载load_growth_rules、主策划load_attribute_rules，并准备成长/属性/任务奖励/库存schema。保持配置为只读依赖，热路径不读取配置、不执行DDL。
2. 角色所有者明确普通阶段并建立成长基线后，才能用明确的AttributeBaseline、当前权威VitalState建立属性基线。基线和policy版本都不允许普通初始化请求覆盖。
3. credit_experience新增可选attribute_rules/login_epoch；apply_growth_plan和request_manual_level新增可选attribute_rules。已建立属性基线时，必须传规则与当前epoch，成长、经验、潜能、属性、当前HP/MP和请求回执在同一角色事务提交。派生失败或溢出使调用方整笔回滚。
4. settle_task_reward/complete_task_transaction新增可选attribute_rules，沿任务渠道唯一凭据防重入账。TaskCompletion.attributes提供同事务生成的当前快照，若角色未显式启用则为None。回放读取当前快照，不使用旧成功回执覆盖最新角色状态。
5. 调用方只在commit后更新RoleOwner缓存等级/属性和向连接所有者投递刷新。完整原生SRefreshRoleData/五维/HPMP字段尚未核验，本模块不拼造刷新包。现有经验余额消息和后续任务bean不等于人物属性界面已经同步。

## 本批必要检查

- verify_role_attribute_storage.py：L2自动五维各1再分配力量5，得到HP110/MP106/外攻34/命中64/速度11；保留缺血/缺蓝；分配重试不额外刷新vital版本；成长保留最新存储伤势，旧战斗结果拒绝；倒地保持0HP；属性溢出回滚等级/经验/潜能/属性/vitals。结果role-attribute-storage-check.json。
- verify_task_rewards.py：原100192奖励使已显式启用的角色L2/61经验、潜能、属性/vitals和绑定道具同事务保存；背包失败回滚全部，重试不重升、不重发。结果task-reward-check.json。
- verify_task_workflow.py、verify_role_growth.py仍通过。检查都使用临时数据库，没有修改在线人物。

## 实际接线与未验证范围

本批只维护任务/成长领域、持久化Adapter、必要检查及此交接；未修改serve.py/gateway.py/accounts.py/game_runtime.py/runtime_storage.py，未重启在线服。

最新读取的GameRuntime/runtime_storage源码已接NPC任务、完成事务和completion_messages，因此续接可随该Interface在后续部署被使用；本批未核对运行进程是否加载当前文件。普通成长规则与属性规则、显式角色基线、成长后缓存更新仍需集成窗口接线。真实原客户端续接/升级/潜能/属性刷新、复杂任务、商业数据库/容量与故障恢复未验收。

## 显式钱包与任务货币渠道

主策划维护currency.py、design/currency-v1.json和CURRENCY_DECISION.md。按designed映射MoneyReward→cash、SMoney→bound_silver，原任务金额/零保留；PetExpReward、ShengWang不转换成钱。该映射不是已经核实的原生钱包槽位。

本窗口已给settle_task_reward/complete_task_transaction增加可选currency_rules：

1. 集成方启动加载load_currency_rules并prepare_wallet_storage；角色钱包只在创建流程或明确迁移时initialize_wallet，不因消除pending自动建立。缺少schema或profile时，任务EXP/确认物品仍可按原接口结算，货币保留wallet_not_initialized。
2. 角色租约事务中按task_currency_channels识别原字段；每个非零字段调用apply_currency，稳定结算键为task:角色ID:任务ID:currency:原字段，source_ref保留任务ID/原字段。当前任务实例为一次性角色+任务ID，循环活动实例尚未实现，不通过清除记录重复发放。
3. 钱包专用receipt与task_reward_channels的currency:原字段凭据、EXP/物品凭据、原任务完成与请求凭据共用外层事务。旧EXP/道具凭据不重放；无profile造成的原pending可在明确建立钱包后只补货币。策略或币种映射变动需要显式迁移，不能把已发金额再换一种币发一次。
4. TaskRewardReceipt新增currency_awarded（该任务历史确认入账字段/币种/金额）及wallet（当前余额冻结tuple）。重试先查稳定凭据，然后重新read_wallet，不能用历史钱包回执覆盖之后的消费。未注入规则时已有确认货币凭据仍尊重，不把已付渠道再次标成待付。未知/未配置渠道继续pending；全部渠道未解决时reward_status/整体effect仍未结清。
5. 现银/绑定银显示桥已按下文证据接入completion_messages；元宝等其它UI槽位仍未确认，不发送猜测刷新。绑定银消费/兑换/交易也不在本切片启用。

verify_task_currency.py通过：原210002的20000人物经验只入一次；无钱包时不自动建profile；显式钱包后原SMoney5000只进入bound_silver，cash保持原余额；之后现金消费再重试返回当前90/5000而非旧100/5000，不重付EXP/钱；PetExpReward10000保留pending。钱包策略不匹配拒绝，余额溢出回滚EXP和所有新增渠道凭据。报告task-currency-check.json。任务可接展示未参与结算，未另发一次5000。

本批方法继续是codebase-design的同事务Adapter和分渠道凭据、writing-for-agents的显式初始化/迁移/接线条件。未修改主策划货币模块及共享在线入口，未操作当前手动客户端、在线库或重启运行服；原生货币显示与运行时CurrencyRules注入仍待集成方验收。

## 提交后的现银/绑定银显示桥

主策划的currency_protocol.py已依据原UI布局→面板→wallet getter→原handler链提供encode_currency_balance：cash对应SRefreshMoney.kind1，bound_silver对应SRefSmoney，资料见CURRENCY_UI_BRIDGE_RESEARCH.md。该UI路由证据与“任务字段到币种”的designed映射分开记录。

任务completion_messages已只对rewards.wallet当前冻结快照中的cash/bound_silver返回上述逻辑刷新。无显式钱包快照不发零余额替代；yuanbao/bound_yuanbao等不路由。余额来自settle_task_reward最后read_wallet，不是本次原奖励金额，也不是钱包模块旧成功回执的余额。

调用方必须等待角色事务成功commit并核对当前连接/epoch之后，再将逻辑消息交目标连接所有者顺序加密发送。本模块依然不直接调用Session、writer或任何网络发送；不触碰当前手动客户端。

在既有verify_task_currency中增加必要断言并通过：原5000入账后再发生现金−10和另一笔绑定银+700，重试任务不重付，提交后逻辑消息必须编码cash90/绑定银5700；无钱包时不增加货币消息，也未发送元宝包。原verify_task_workflow仍通过。只验证代码路由和原生body字节，原客户端实际UI显示/新部署仍待集成方验收。

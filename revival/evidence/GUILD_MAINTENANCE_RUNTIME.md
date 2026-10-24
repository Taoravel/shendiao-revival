# 帮派维护生产者整合交单

读取条件：整合正常/基本帮派维护、自动时钟、建筑产量/研究或帮派终末。准确固定源与审查状态查guild-maintenance-current-review.json；本文件不授权生产采用/部署。

第25批新增真实guild小时生产者；规则和所有权唯一细节见GUILD_MAINTENANCE_CONTRACT.md，原字段与公式未知项见GUILD_MAINTENANCE_RESOURCE_BINDING.md。building/research已有接口沿用，可选guild_maintenance_policy默认None，依赖两个显式规则；不补旧档，不写共用baseline。源实现和fixture验证已完成；正式数值、共享入口激活与GUI另验。

## 最小接线

1. 主策划先制定并登记唯一生产规则、适用新建/迁移档案和已有building/research曲线，明确所有designed数值。原小时、48比较和字段宽度不提供缺失曲线。不要从verify脚本拷贝fixture给正式服。
2. 在main当前准确BASE中局部传OrganizationStore/Runtime(...,guild_maintenance_policy=explicit)，既有building_policy/research_policy也须一致。initialize只prepare表，真正create_guild同事务初始化clock/resources；旧known/unknown档案迁移另定，不能默认补0。shared快照仅供独立回归，不能整份覆盖game_runtime/runtime_storage/accounts/serve/gateway。
3. GuildRuntime按非None规则创建GuildMaintenanceRuntime；scheduler_enabled只控制周期任务，scan_interval_ms只控制读取频率，不改变经济digest。每partition有界目录、每guild通过已有organization Owner结算；分区/曲线变化视作需迁移。没有独立全服执行器。
4. 可信手动/恢复调用使用GuildMaintenanceCommand(guild,due_ms,deadline_ms,online=冻结(role,epoch)元组)，经OrganizationRuntime.maintain_guild。客户端不能传费用或XP；source键自动由guild+due决定，必须真实当前clock due。超时使用resume_guild_maintenance(GuildClockResumeCommand)，不给历史补发收益。
5. 终末读取guild_maintenance_terminal(guild,due_ms)得到冻结待办；按其families/members完整代次向各所属Owner交付后才能讨论ack/完成。本批尚无完整角色/任务/地图消费者，不清真人其他所有权状态。已有家族pending解散在此之后可补guild阶段凭据和family ack，源/终末proof均要保留。

## 当前可观察结果

normal同一事务扣正常费、增加独立guild_resources并调用纯研究award；basic只扣独立基础费。两个小时fixture研究从0级0→0级7→1级4，资金10000000→9984000→9968000，资源5→9→13，均是隔离算例。只有选中研究才成长；本批不发任意经验命令。

降级影响建筑上限/选择代次；终末使guild pending/level0、关闭clock、撤职、真实家族离帮历程6及耐久待办。GuildRuntime提交后用现有GuildWake读取当前研究/授权建筑视图；终末用待办成员发送departed唤醒，收件人重新确认当前membership，避免清掉已加入的另一个帮派。提交后的展示失败仅延后，真正DB提交错误传播。

guild_maintenance_snapshot返回资金/人气/资源/level/当前研究力/正常费用及clock。它只供可信内部读；完整原c5624详情仍缺其余真实字段，未将这些已知字段和假0拼成生产mapper。客户端数字切片已验，但没有完整详情GUI可见证明。现有七项修炼资材账未写入本次产量，原同账关系尚unknown。

## 固定验证与未完范围

本批新增12组真实Store/Runtime/加密Peer及5组原生验证，合并旧30脚本共32项回归。准确结果及独立Standards/Spec审查以current-review指向的review-result.json为准，不以本文件草稿声称全部已过。当前候选固定source及原资源都核内容摘要；无Git采用batch24固定baseline/diff，历史版本保留。

未操作游戏、真人DB、服务或生产政策；共享入口和组织地图地址/NPC准入未编辑。完整建设任务/NPC115、成员技能学习/属性/生活生产/战斗效果、终末跨Owner清理、完整面板GUI、跨库及商业容量仍未完成。全量家族帮派和社交目标持续active。

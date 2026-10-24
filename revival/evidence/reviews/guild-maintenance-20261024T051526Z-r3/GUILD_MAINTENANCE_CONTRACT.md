# 帮派小时维护、资源与终末交接

读取条件：采用guild_maintenance_policy、接帮派小时生产者或处理帮派耗尽。第25批范围为显式新建政策下真实小时来源，不等于正式数值采用、完整组织激活或GUI验收。

## 已核事实与本地设计

原生字段、名字、数值宽度和48倍边界见GUILD_MAINTENANCE_RESOURCE_BINDING.md。资金/显示维护费64位，资源/研究力/人气32位；原资金恰等于48倍费用显示白色。原布局说明正常维护增加资源、工坊改善刷新/容量、练功房改善研究速度、人气不足1000费用+50%。这不证明原服计算顺序、取整或任何建筑曲线。

维护时钟每3600000ms推进一次。以下均designed且只有显式隔离fixture，未写共用baseline：在线当前租约采样，先更新人气再算费；人气clamp到显式最大；正常费复用建筑预估base+等级×系数，低于1000向上取整×1.5；扣费前资金>=48×正常费为normal，否则basic独立费用，basic最多扣现有资金。normal才按工坊曲线增加guild_resources并按练功房曲线给当前研究技能XP；研究力显示与小时XP是两个独立曲线。

guild_resources与现有guild_practice_materials并账关系unknown。此批只写前者，后者的许可预留/退款/兑现保持原有规则。未找到原server数值表；研究力、资源增长/cap、资金cap、基础费、人气增减均不能将fixture当作恢复原值。曲线21行非负单调，32/64位各自有界；新资源仅填可用空间，已知历史超cap余额保留。资金cap本批只约束降级恢复款，不声称全部资金收入已接cap。

扣费后资金<1或人气<1：等级>1降一级、超新cap建筑裁剪并清其进度，其余建筑保留；取消选择并推进建设generation；恢复最多5000000资金、500人气，受当前cap/人气最大值裁剪，均为明确设计。此小时不产资源/研究XP。等级1进入dissolution_pending、level0，停止时钟、撤销成员/职位资格、分离家族并保存完整清理待办。不会写角色/任务/地图，不把pending称清理完成。

## Interface与状态所有权

OrganizationStore/Runtime新增可选guild_maintenance_policy，默认None；依赖显式building_policy和research_policy。只在真实create_guild事务创建clock/resource，历史缺档不回填。规则冻结且指纹包含经济参数和两个依赖指纹；scheduler_enabled/scan_interval_ms只控制检查，不改经济版本。partitions改变需迁移，不能悄悄重分旧目录。

GuildMaintenanceCommand(guild,due_ms,deadline_ms,online=tuple(role,epoch))只有可信系统入口，无客户端收费/经验参数，无线包路由。键由guild+原due确定。维护资金ledger、资源、人气、建筑/组织/时钟版本、研究子凭据和父凭据同一帮派Owner事务提交。维护调用纯guild_research.award，不跨Owner等待。回滚尾部失败必须恢复整个事务；显示通知在提交后单独处理，不能吞实际存储失败。

历史凭据先读，经济政策关闭或改变后仍可重放。重放核父摘要及配对资金ledger、研究凭据；缺任何已声称的经济凭证拒绝outcome_unknown。父不存在但有同源资金/研究凭据也拒绝，避免把不明结果再次付款。每个小时以第一次已提交观察为准，重复观察变化不重算。

超过max_lateness_ms需GuildClockResumeCommand；只保存无经济变化的resumed凭据，把下次设now+一小时，不补历史产出。resume和tick共用原小时键，不能两次结算。退出后的旧成功凭据保留，新小时仍受active资格限制。

GuildMaintenanceRuntime按显式分区周期扫描索引(partition,state,next_due_ms,guild)，每次有界batch、全局有界jobs，每guild最多一个job。每轮固定最大(next_due_ms,guild)，容量不够不推进被拒源，轮尾重置以回访旧失败源，不受持续新来源无限拖延。共享job槽按被拒分区先后公平准入，每分区至多一枚目录标记、至多256枚，不保存全服命令；空目录/读取故障移除标记，单一故障分区不能反复抢走唯一槽。每次真正写入仍进入既有该guild Owner；没有全服命令队列/世界锁。长停服由同Owner明确resume。

## 终末与家族解散交叠

guild_maintenance_closure集中终末复杂性：先保存不可变GuildTerminal(guild,due,revision,families,members,state=pending,recipe)及家族代次proof，逐家族生成真实历程6，再删本guild关系。成员包含已知active缓存与真实当前代次，数量有界；不造未知角色经济档案。

若家族已产FamilyDissolution但帮派先终末，既有guild_dissolution消费者仍核真实家族outbox及pending时钟，再核已保存guild终末家族代次proof，补正常阶段凭据供家族ack，不重复离帮历史或经济变化。家族导致帮派非active时也停止已有guild时钟，不为旧档新建时钟。任务/场景/角色清理仍须各Owner消费待办，当前仅持久交接而未完成消费者。

## 验证与明确缺口

verify_guild_maintenance通过公开Store/Runtime、临时DB与实际加密Peer验证，SQL只用于故障注入或显式旧档/目录夹具。覆盖独立字面费用边界、两小时XP、当前租约、降级、双解散顺序、尾凭据回滚、历史重放/缺证拒绝、过期resume、资源超cap与缺档不补、8同源、另一family/心跳独立、当前退出cache和真实周期。目录容量验证含局部内部游标断言，作为补充基础设施检查，不冒称用户玩法端到端测试。

verify_guild_maintenance_native执行真实收据标量→原接收/快照/格式化输入，高64位量、48倍三个边界、人气999/1000及原控件绑定。CRT/字符串出口有Adapter，非完整c5624 mapper，真实渲染、筛选、GUI未验。

本批未改main共享入口、生产规则、真人库、运行服务或启动游戏。正式规则唯一来源、真实建设任务/NPC115、角色技能学习和属性/战斗效果、完整详情/GUI、终末其他Owner清理、跨库与商业容量仍未完成。全量社交目标保持active。

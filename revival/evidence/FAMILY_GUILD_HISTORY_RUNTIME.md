# 家族入帮、离帮历程接入

读取条件：整合第23批组织关系历程、恢复未确认事件或修改其后台扫描时。固定候选与审查状态查 `family-guild-history-current-review.json`；该指针发布前，本页只是实现交单草案。完整社交目标继续执行。

## 接入步骤

1. 启动沿 OrganizationStore.initialize 建立 `guild_family_history_outbox` 和 `family_guild_history_inbox`，DDL 不进入玩法热路径。已有旧关系不补造历史；历史表和原 family_history 一并保留。
2. 原帮派唯一写者在成功创建、同意家族加入时产生模板5，在主动离帮、被逐或终末家族移除时产生模板6。原关系事务同时保存冻结名称、时间、成员代次和唯一源；移除事件在删除关系前记录。已成功命令重放不产生新源。
3. 既有 FamilyMaintenanceRuntime 分区扫描 `family_guild_history_page(partition, after_family, ceiling)`，从持久目录提示最早事件。每轮固定开始时最高pending家族ID，每批最多既有 batch_limit 个不同家族，逐家族索引 seek；容量不足不跨未调度条目，轮次末端同时清游标和上界后绕回。持续新增高ID也可回访旧家族的后续事件；任务按家族合并并共用既有容量。`pending_family_guild_history`保留只读目录查询用途。
4. `family_guild_history_event(sequence)` 读取冻结事件，构造 `FamilyGuildHistoryCommand(event, request_id, deadline_ms)`。经 `OrganizationRuntime.consume_family_guild_history` 到家族所有者，完整核源、要求最早 pending，原历程、家族 revision 和 inbox 同事务提交。
5. 家族所有者返回后，经 `ack_family_guild_history` 到帮派所有者。核同一事件的真实 inbox 与 archive 后确认该帮派 outbox。未确认的旧事件继续挡住该家族后续事件；中断恢复重复消费只读原凭据。

消费与确认分别遵守家族、帮派的唯一写入所有权，调用者不同时占两者。新建帮派沿原创建所有者事务。没有客户端任意传事件的入口，没有新的全服执行器。此 Adapter 用同一 SQLite 读取两份持久证明；跨数据库交付另需独立协议及验收。

## 已知行为与错误

源携带当时帮派名称和时间；当前已经离帮、换帮或更名不改过去。历程按家族所有者实际写入顺序展示最近100条，旧 archive 仍保留，日期沿既有设计格式。5/6之间按持久源 sequence 严格先后，其他等级、族长事件可能穿插。

缺源、篡改源、缺 inbox、档案不一致和乱序明确拒绝，不能空确认。关系事务末尾失败整体回滚；消费末尾失败不留下半条档案；确认失败保留已提交家族历程供重试。已提交后的面板读取或投递失败延后通知，原查询/重登读取当前授权视图；真正消费事务失败仍向调用者报错。

模板5/6及两项 UTF16 参数来自原 cfamilyprogress/CourseInfo；本批原完整 FamilyData marshal 与当前加密 Peer 面板均有自动验证。恢复顺序、稳定源、日期格式、容量和扫描预算属于本地服务器设计。模板7最活跃活动仍无生产者。

## 验证与范围

公开 Store/Runtime/Peer Seam 覆盖真实创建/审核/离帮/被逐/终末源，同源重放、跨帮先后、历史名称、缺档不补造、事务尾失败、消费后重启确认、实际周期、公平目录及阻塞一家族时另一组织与心跳继续。原生验证执行 CourseInfo 与完整 FamilyData marshal，不等于 GUI 实测。

必要验收为固定源码/资源哈希、28项回归和独立 Standards/Spec 两轴记录全部完成；最终数字以批次 JSON 为准。此交单不完成角色/任务/物品/地图解散清理，不提供组织实例准入，不注册 NPC、不改研究曲线/共用数值。实际服务、真人库、游戏 GUI、跨数据库与商业容量均未在本批操作或验收。

固定目录里的共享文件是验证依赖快照。主集成以自身当前准确BASE接入本批9个候选文件及其已有组织依赖，重新固定整合闭包并验收；不能把整份验证source覆盖到当前工作区或正在使用的发布目录。研究/家族历程/捐献指针同步，只用于避免混用不同Store/Runtime版本，不授予共享发布许可。

方法：codebase-design 把跨组织历程证明集中单 Module；tdd 在既有公开 Seam 逐切片先红后绿；code-review 固定22批 r2 文件基线作两轴审查；writing-for-agents 将触发条件、恢复次序、完成判据及未验范围放在同一交单。

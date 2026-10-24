# 家族入帮、离帮历程

读取条件：改变家族与帮派关系、消费关系历程或扩展后台目录前。第23批补原cfamilyprogress模板5/6真实生产与家族消费，模板7最活跃活动仍未实现；完整社交目标保持active。

## 真实源与所有权

成功建帮的创始家族、帮派同意入帮产生模板5；家族主动离帮、被逐、真实终末家族解散从帮派移除产生模板6。拒绝申请、普通成员离开家族、无实际关系变化、已成功命令重放都不生成新事件。原模板parameter1为既有设计日期、parameter2是事件当时帮派名，不从未来名称或当前关系猜历史；原表/FamilyCourse编解码已核验。

关系变化及guild_family_history_outbox在原帮派事务一起提交（新建帮派仍在初始创建事务），失败全部回滚。源保存唯一sequence、guild/family ID、当时family_token、5/6、当时名称/时间和稳定source_id。既有旧关系不回填事件。outbox状态仅由该guild所有者确认，家族所有者不改帮派表/资金/职位。

家族消费经既有organization键，先核完整冻结事件与原持久源一致，并要求这是该家族最早pending源；不同guild的事件也按同SQLite源sequence顺序消费。家族archive、family_guild_history_inbox凭据及家族revision同事务；同源重放只读既有凭据，历史事件即使当前已经离帮/重入仍可记真实过去，不据当前成员代次改写旧事件。GUI读取仍走当前成员/租约授权。

家族面板沿第19批按家族Owner实际写入顺序展示，保留源发生时间作日期；5/6彼此按源sequence，其他族长/等级事件可穿插。未修改既有最新100条窗口和存档保留设计，也不伪造旧关系的加入时间。

家族Owner释放后，后台工作再投递guild ack。guild所有者核家族inbox及真实archive匹配后把自己outbox置done；没有源/没有家族凭据不能空确认。同源重复、提交后断线、家族消费后进程退出/未ack均可恢复。更后事件须等旧pending获ack才消费，避免历程顺序被跨Owner投递重排。此为同SQLite兼容Adapter的双Owner outbox/inbox，跨数据库部署与商业容量另验。

## 有界目录与通知

复用现有FamilyMaintenanceRuntime独立分区扫描，不新增全服执行队列。source存family分区，索引(partition,state,family,sequence)和(family,state,sequence)。每次最多batch_limit个不同family，逐family用索引seek/LIMIT1取最早pending，游标只用family ID，跳过同family后续积压；无结果后下一轮绕回。避免GROUP BY扫完某家族巨大历史或LEFT JOIN整表找未消费。

history_jobs按family合并并与现有维护/捐献/解散任务共用有界容量；扫描只是提示，家族消费与guild ack各自复验持久状态。暂停一家族消费不持guild Owner，也不阻塞其他组织/心跳。archive提交后的展示失败仅延后通知，不伪报消费失败；下一原查询/重登恢复当前家族面板。

目录游标只跨过成功创建任务或已有该家族运行任务的条目；容量不足时停在首个未调度条目之前。不能直接推进到整批预取末尾，否则持续新ID可使旧家族事件一直被跳过。r1两轴审查记录及容量一、批量二、连续新目录条目的实际scheduler反例保留；修复回归使用隔离存储/Owner Adapters验证真实调度，持久事件仍由其他真实Store/Runtime检查承担。

## 验证

沿既有公开OrganizationStore/Runtime/原生Peer Seam逐切片验证：真实建帮/同意、主动离帮/被逐、原终末移除源；关系与outbox/命令receipt晚失败回滚；家族archive/inbox尾失败回滚；缺源/篡改/乱序/缺inbox ack拒绝；先consume后重启恢复ack；重复不加历程/revision；同guild/跨guild离开再加入的真实先后与历史名字保留；未知旧关系不补造；有界公平目录与一家族存储阻塞时另一组织/原生心跳继续；实际周期源/原面板/重登。

方法：codebase-design将关系历史桥集中单Module，复用实体Owner及收件人投影；tdd先在公开Store缺源生产观察红灯，再实现关系源/消费/后台恢复等纵切；code-review固定第22批r2源独立Standards/Spec；writing-for-agents集中源证明、顺序/ack条件、局部设计与未验范围。未改shared/main、生产数值或组织地图准入，不启动游戏/实际服务/真人库。

实际先红：缺pending源查询、缺消费命令、真实离帮无事件、runtime扫描后历程仍缺模板5；分别实现后转绿。其余故障/原生/公平目录为补充验证。末尾organization_receipts的IntegrityError原本在转换之外、周期等待须覆盖既有5000ms扫描间隔，这两项夹具装配修正不记功能红灯。GuildClosureRules新增history_partitions只读取既有family维护分区数，以便终末关系事件落正确目录，没有另设数值政策。源名称与关系权限仍由原Guild事务决定，后台消息不接收客户端伪造事件。

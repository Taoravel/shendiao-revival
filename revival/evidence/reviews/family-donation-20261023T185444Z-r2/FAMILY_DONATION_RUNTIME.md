# 家族银箱捐献与自动升级增量

用于审查、接入或恢复银箱捐献。数值、来源和待主策复核项唯一说明见FAMILY_DONATION_NUMERIC_HANDOFF.md；可执行配置是organizations.family_donation。当前实现和隔离验证不授权真实NPC注册、共享激活或运行服切换。上一批scene-delivery clean候选保持原样。

## Interface 和事务

`OrganizationCommand(actor,epoch,request_id,deadline,family,'reserve_family_donation',(count,))` 只能由可信玩法入口发到现有家族所有者；它校验成员代次、已知资金/建设/声望、数量和未决容量，保存不可变permit。它不是新的线包路由，不从客户端直接接受组织ID或数值金额。

角色所有者在已开始的当前fenced事务调用 `family_donation.pay(db,account,role,epoch,family,reservation,now,rules,inventory,precommit=...)`。该Interface验证角色、Inventory及当前成员/epoch/期限，按统一设计选择真实携带箱子，通过Inventory.apply_settlement扣满数量，和共同付款证明一起落盘。precommit必须来自可信共享资产/资源接线，提交前编码当前背包与source结果；返回冻结DonationPayment含原选中item key审计、当前InventorySnapshot和逻辑消息。函数不连接/提交/发送，不等待家族。

`resolve_family_donation,(reservation,)` 在同一家族所有者校验付款共同证明与inventory child指纹后，一次提交资金、建设/升级、原代次声望、ledger、permit终态和DonationOutcome。显式resolve也可取消未扣物预留；已扣物的预留须完成贡献。重试返回既有家族结果；角色已付重试返回当前物品和当前编码，不重扣、不回放历史绝对背包。

`DonationSweepCommand(family,request_id,deadline_ms)` 是可信内部恢复命令；OrganizationRuntime.sweep_family_donations将它与普通家族管理排入同一SerialOwner。周期目录分区索引、有限批、延续游标、按family合并；维护/解散/捐献任务共用总任务容量。过期未付可取消；未过期未付保持reserved；已付无需客户端再次在线即可完成。关闭时排空已经接受的任务，未决状态留给下次启动。

小时维护事务先结算全部已付捐献、取消未付permit，再以升级后的当前等级/资金维护。历史小时已有凭据时不顺带处理新捐献。维护失败会将该事务内捐献的家族阶段一起回滚，角色扣物/共同证明保留待重试；因此没有跨所有者假回滚或假退款。

## 所有权和恢复不变量

- 家族所有者唯一写permit、家族资产、家族成员声望和结果；角色所有者只写自己的Inventory及role_family_donation_payments。跨所有者传冻结命令/凭据，无锁等待。SQLite是本地共享文件Adapter，远程部署仍需durable outbox/inbox。
- 共同付款证明、child库存证明、指纹必须一致；只有child而无共同证明时保持unknown，不给奖励、不取消或退款。未知旧建设/声望/资产基线拒绝，不补0。同家族关系仍在而成员档案缺失属于unknown，不能当成已经离开并跳过声望。
- 贡献已付后离开，资金/建设仍属于原家族；只给原member generation声望，已删除的旧关系不补给新加入代次。重复结算不得重复资金、声望、升级或ledger。
- 当前数值溢出拒绝家族阶段并保留已付证明，等待可信修复；不能回报成功。家族阶段晚凭据失败必须回滚本事务所有变化。
- 家族通知通过既有FamilyWake、收件人所有者和连接队列发原生UPDATE_FAMILY/名单；慢连接沿现有拒绝/断开策略。消息入邮箱不等于GUI已见。

## 验证与未完成范围

Seam沿用公开OrganizationStore/OrganizationRuntime、当前角色事务与Inventory、原生Peer。TDD实际红灯包括缺捐献Module、维护先于已付贡献导致错误降级、周期目录不恢复付款，然后逐条修复；编码夹具短包和ItemState字段名错误是验证装配修正，不当成功能红灯。其他边界检查不宣称全都先红。

verify_family_donation.py的17组检查覆盖双模板/绑定优先、升级/多级/满级、当前背包预编码、重试/重启、晚失败整体回滚、非法数量、取消/孤儿child、离开重入代次、维护先后、实际5秒周期与原RC4/MPPC消息、另一家族和心跳在受控阻塞时独立推进，以及审查实证的已付后缺成员档案仍保持unknown。后者同样实际先红再绿；初版审查发现保留在固定r1，修订另建r2，不覆盖审查输入。结构化结果family-donation-verification.json。codebase-design用于冻结小Interface和两个写者职责；tdd用于公开Seam纵切；code-review按固定源独立Standards/Spec；writing-for-agents将接入和恢复限制共置。

本批不恢复已退出成员的旧声望，不代替任务/物品/场景解散消费者。原服务296注册、原捐献请求模式/数量/选择语义、真实本家族实例准入和已迁移资源profile的正式precommit尚未接入。已定位通用CSubmit2Npc及任务窗口公开codec，但尚未证实296使用哪个submit_type/字段，不假装普通任务交物就是银箱入口。未经原链验证不发猜测prompt或修改任务窗口Module。

独立两轴结果和固定依赖交付后记入family-donation-batch.json。本批为未激活的组织子系统增量，完整整闭包、数值复核及唯一部署切换仍交主集成。未打开游戏、实际战斗、部署/重启或操作真人数据。真实GUI、生产容量、跨库事务、完整家族/帮派玩法和全量社交均尚未完成。

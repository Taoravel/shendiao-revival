# 银箱与建设：已批准数值与接线条件

读取条件：复核或激活 family_donation.py，以及组织policy中的family_donation之前。数值已按FAMILY_DONATION_ROOT_DECISION批准，当前标记`numeric_review=root_approved_design_not_activation_authorization`；尚未形成实际运行发布的完整激活闭包。社交窗口未改共享入口、部署或启停进程，也未覆盖冻结的social-scene-delivery clean源。

## 已确认与未确认

原包 citemattr 36076/36201、bookanswerconfig 15036确认两个家族银箱模板、每箱建设+1和家族声望+5，交本家族10055特产商；原服务296。cfamilymaintainconfig的levelupnum按下一等级取值为20/50/80/100，目前集中字段family_construction_targets仍标inferred。来源与官方端游检索失败范围见FAMILY_DEVELOPMENT_RESEARCH.md。

**未知原服规则**：每箱资金金额、升级时建设累计/消耗/结转、满级处理、原声望两个UI槽位的消费含义、跨模板选择和批量上限。物品price100000不证明捐献资金100000；本候选没有将其标成原服公式。

## 已批准的设计公式与上限

唯一可执行配置是design/recovery-baseline.json.organizations.family_donation，来源分别写在对应source字段：

- 每箱资金100000，明确designed。funds_after=funds_before+count×100000，必须在非负signed63范围；不读角色钱包、不扣现金。
- 每箱建设+1，达当前目标就扣该目标并升级，可连续升级；阈值20/50/80/100。等级上限5，5级建设归0，但资金和声望仍增长。结转/满级处理为designed，不称原式。
- 每箱原声望+5；投影到原first/second两个槽位均+5，明确designed，两个槽位原消费含义仍unbound，各限非负signed32。主策已批准它们投影同一逻辑5，不能累计为10或分别消费。
- 单批1..100；每家族、每角色各最多64个未决预留；选当前携带栏中两个模板，无明确客户端选择时才按绑定优先、slot、item key排序，允许跨模板拼批，均designed。已有选中请求固定原key/数量，不以默认排序替换。未消耗满批数量即整个角色事务失败。
- 家族原资金/建设/成员声望基线未知则拒绝；不会初始化未知旧档。资金、建设、声望或revision溢出保留待核查，不能伪装成功。

## 跨Owner预留、提交与恢复

1. 家族所有者通过reserve_family_donation保存不可变member generation、角色epoch、count、deadline、policy及fingerprint，暂不修改家族资产。
2. 当前角色所有者在同一fenced事务核对预留仍有效、当前成员代次未变，通过Inventory.apply_settlement扣真实箱子，并保存共同role_family_donation_payments。可信precommit必须在提交前编码当前背包与资源source消费者；失败整体回滚。角色只写自己的物品和付款凭据，不写家族资金/声望。
3. 家族所有者核对共同付款凭据和对应inventory child凭据后，在一个事务加资金、升级/建设、对应旧成员声望、资金ledger及幂等结果。paid后成员离开，贡献仍属于原家族；已经清掉的旧声望不发给重入的新代次，标designed。
4. 实际周期目录按16分区、索引和游标取限定批，投递现有家族SerialOwner，恢复已付或取消到期未付；维护/解散/捐献任务共用容量限制。没有持角色或家族锁等待另一个Owner。
5. 小时维护先在同一族事务确认已付捐献、取消所有未付预留，然后按当前升级后的等级和资金计算维护。角色付款与家族取消通过同库事务竞争；预留取消后无法再付款。历史小时重试只读其原结果，不顺带结算新捐献。
6. 共同付款凭据缺失而child扣物凭据存在，视为unknown并保留，不补奖励、不取消或假退款。断线、重登、换request_id和提交后丢回包不能重复扣物或发奖励。

SQLite是当前本地Adapter；跨库部署须将上述付款证明和消费决定改为durable outbox/inbox，不宣称当前具备跨库原子性。原296分派、选择器回包与选中请求已离线追证，纯codec及固定选择付款已实现，见FAMILY_DONATION_NATIVE_HANDOFF。真实NPC/组织实例准入、历史窗口取值及当前唯一source接线仍未完成，不能按模板1401或NPC10055授权。数值与生命周期已获根批准，实际上线仍须满足ROOT_DECISION完成条件。

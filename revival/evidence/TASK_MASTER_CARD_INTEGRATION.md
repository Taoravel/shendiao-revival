# 师父选择卡与装备目标接线

任务窗口已实现 `task_master_card.py` 的独立事务流程；共享入口仍由集成窗口接线。政策唯一来源 `design/newbie-master-card-v1.json`，原43路线/选项来自 `catalogs/newbie-master-cards.json`。200xx 是卡片效果，不是CG。

最新真人反馈修正：Start读尽只发CCommit，旧End触发是误用Finish phase3。当前源码已按CCommit授权卡，检查直接消费原native输出；部署/中央政策文字待集成/主策划更新，见[FIRST_MASTER_CARD_COMMIT_FIX.md](FIRST_MASTER_CARD_COMMIT_FIX.md)。

## 集成顺序

1. 启动时在既有任务/奖励/新手章节与 Inventory 准备之后，调用 `prepare_master_card_storage(db)`；调用 `load_master_card_rules(resources, chapter_rules, inventory_config)` 一次并共享冻结规则。加载时核对43路线、两件原武器/角色/slot0/数量1、10个type59及各自唯一车夫后继。不在请求热路径读配置或DDL。
2. 当前角色已显式完成intro、原师父任务active时，在地图返回匹配真实实体/位置版本/距离证明后，调用 `open_master_dialogue(...proof, location, generation=..., now_ms=...)`。返回冻结 `MasterDialogueTicket` 和原生完整接取bean→RefreshState3→SVisitNpc；已有bean不受重复接取更新，因此显式刷新不可省。角色所有者保存单个当前ticket；对白文字由原客户端本地配置读取。
3. 原任务解码得到 `TaskIntent` 后，CCommit交给 `authorize_master_card(...ticket, intent, location, generation=..., now_ms=...)`，同NPC/option0及全部ticket检查通过后持久化pending卡授权，事务成功后发SPlayCardEffect。CQuestDialogEnd属于Finish阶段，不是本Start-only链的授权条件。卡分支不交给普通对白完成器或CEndPlayCG。
4. `CGetCardItem 0xc041f` 精确8字节交给 `choose_master_card(...body, location, inventory, generation=..., now_ms=..., **reward_rules)`。函数从显式章节和唯一原路线找pending授权，不从线包猜任务；原选项/epoch/generation/权威位置版本/期限全部匹配才结算。它返回 `MasterResult(choice, completion, messages, replayed, equipment_event)`，choice包含实际获领 `item_key`。
5. 选择内部使用已有 `AssetChange` 唯一结算键，并在同事务公开快照的前后差集中定位唯一新装备。绑定1、普通装备工厂condition/detail保留，领取时不装备。选择凭据、实际实例、原type10完成/公共奖励、type59激活与原卡效果已执行标记同事务。任何异常由调用方整笔回滚；成功提交后才投递messages。无需修改原display_items伪造卡片为普通任务奖励。
6. 已授权章节且处于此链的装备请求，用 `equip_master_transaction(...inventory, item_key, slot, request_id, **reward_rules)` 合并真实Inventory.equip_transaction、同事务当前快照检查、type59完成/公共奖励和唯一车夫任务激活。普通角色仍走原背包装备路径。装备属性贡献由资产/人物窗口接入，此模块不猜baseEffect映射。
7. 重登入场的同一角色事务调用 `master_resume_messages(...)`，恢复当前师父/type59/车夫state0完整bean，不重放卡片。若type59active，再调用 `reconcile_master_equipment(..., inventory, **reward_rules)` 可恢复已经实际装备的精确获领实例；消息同样提交后投递。登录无显式章节时resume返回空；reconcile须由集成方仅在已完成章节/相应链路调用。

`resources/rules` 均为启动只读对象；函数的前三个身份参数依次为account_id、role_id、epoch。`db`始终为调用方角色事务。票据/地图证明是冻结值，工作线程不访问角色所有者的可变TaskConversation。选择/装备完整原型及参数以源码为准，公共奖励参数与complete_task_transaction相同。

## 恢复与重试

同一已提交选项只读当前背包与当前active任务bean，不重新发物、不回放历史任务状态；另一选项拒绝。pending断线/超时保持不变，回到同一真实师父后重新对白结束可换发新epoch/generation的授权，旧会话拒绝。卡表没有任务ID/nonce，不能为任意card/item构造选择资格。

装备判定仅接受当前快照中仍归此角色、template一致、quantity1且slot0的choice.item_key。装备历史receipt不能代替当前快照，其他同模板实例也不能代替精确获领实例。只激活车夫后继，不完成车夫对白、不执行传送；虚拟NPC10390仍是客户端开背包链接。

## 背包公开读取依赖

本批已采用 Inventory 实际新增公开入口 `immutable_snapshot_transaction(db, *, epoch=...) -> InventorySnapshot`，替换上一版建议的read_transaction_snapshot名称。它在调用方已开启事务内检查 account/role/current lease，返回当前冻结 items、inventory_revision，不另开连接、不提交、不建表。选择卡会先读快照，调用已有 apply_settlement，随后再次读快照，从唯一新建装备实例得到实际 key；因此不需要改 AssetReceipt 结构。任务代码不查询 inventory 表、不调用私有方法。

`equip_transaction` 和新快照入口接受正整数epoch；本批重读AccountStore.acquire_lease，确认实际公开返回正整数（uuid整数移位），SQLite role_leases虽为TEXT列但不改变调用值类型。因此此前“正式字符串epoch兼容阻塞”是把存储类型误当公开输入类型，现撤销该缺口。测试已改为直接使用实际acquire_lease，不再人为改写租约。若未来其他Adapter以字符串作为epoch，须显式扩展资产契约后再接；当前实际账号路径不受此假设阻塞。`equipment_bag_messages`继续要求显式钱包；任务不填假现金0。

原公开读取缺口已经消除，当前实际账号租约与资产契约已兼容，可由集成窗口接线。任务窗口不修改 inventory.py 或共享入口。属性总值补齐、背包现金显示需要由原所属窗口完成；这里只调用当前公开刷新，未知钱包直接失败并回滚。

## 本批方法

codebase-design：卡片状态集中在独立模块；跨模块使用公开 AssetChange、冻结快照、EquipmentEvent，事务由角色所有者提交。writing-for-agents：按启动、对话、选择、装备顺序交付，并单列当前依赖和未验证范围。TaskDomain新增两种可信事实，普通supports_plain_dialogue判定保持收窄。

产物：task_master_card.py、task_domain.py的两个事实入口、verify_task_master_card.py及evidence/task-master-card-check.json。限定临时库检查已通过：43路线每种两选项共86次实际普通工厂发物与真实装备，原对话授权及错误NPC/会话/位置/期限拒绝，背包满与领取/装备后继回滚，相同选择与装备重试、另一选项拒绝，换连接回原师父重新授权和已装备实例恢复，以及当前任务bean恢复。本批已删除ControlledInventory读取Adapter，snapshot/grant/equip/背包编码全部使用实际Inventory公开Interface；epoch来自实际AccountStore.acquire_lease，重新获取后旧会话拒绝，未人为覆盖租约。

未验证：共享路由、连续原生连接流、真实客户端界面、在线服务部署。intro全套已有集成窗口独立通过，此批仅为建立受控前置而调用，不重复宣称该运行时验收归本模块。

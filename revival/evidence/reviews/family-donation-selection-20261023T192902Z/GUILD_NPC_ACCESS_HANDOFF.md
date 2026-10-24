# 帮派 NPC 资格与接线交单

2026-10-23。主集成制定组织实例身份/准入政策、接组织 NPC 或迁移当前频道时读取。此批核对真实公开 Interface；未新增组织地图后端或准入政策，未注册真实 NPC、启服、打开游戏或执行实际战斗。当前频道最新 Interface 另见 SOCIAL_SCENE_SCOPE_HANDOFF.md。家族296及FamilyData尾Q的原驻地比较链、选中银箱与接线顺序见FAMILY_DONATION_NATIVE_HANDOFF；该Q不替代服务器完整地址准入。

第十四批资格补充：显式新家族现在有family_maintenance状态；零级dissolution_pending时，guild_scope/职位成员与普通组织权限会拒绝该家族，旧代次排队消息失效。组织表仍无地图绑定，仍不能用诊断snapshot作准入。新公开冻结family_maintenance_snapshot可诊断时钟与pending，完整规则及未完成清理见FAMILY_MAINTENANCE_RUNTIME.md；下文“组织表无active字段”继续成立，不代表新维护状态不存在。

## 组织侧已经存在的能力

| 公开 Interface | 实际结果与资格范围 | 接线限制 |
|---|---|---|
| OrganizationStore.guild_scope(actor,epoch) | 检查当前角色租约，返回 `(guild_id,family_token,member_token)` 不可变 tuple | 两个 token 约束家族在帮派、角色在家族的成员代次；不含地图归属、组织 revision 或准入授权 |
| membership(actor,epoch,kind) | 租约检查后的 family/guild ID 路由提示 | 组织所有者执行命令时须再验成员资格，不能拿提示直接授权 NPC |
| family_guild(family_id) | 家族所属帮派的路由提示 | 不检查请求角色租约 |
| snapshot(identity) | 一次一致读取返回 `(dict(org), tuple(member_ids))` | org 是新建可变 dict；此 Interface 无调用者租约检查，不是冻结准入凭证 |
| guild_office_snapshot / guild_training_snapshot | 冻结领域投影 | 可信读取；实际管理操作仍由组织命令检查职务和成员资格 |
| guild_practice_permit / pending_practices | 当前租约下的冻结修炼预留/有界待处理记录 | 支持角色结算和故障恢复，不证明所在地属于此帮派 |
| OrganizationRuntime.command(command,now) | 按组织有界串行，返回冻结 OrganizationOutcome | 重验租约/组织权限并做持久幂等；未定义组织地图身份 |

组织表当前只有 id/kind/name/aim/leader/level/revision，没有 active 标志、MapAddress、instance/partition 或地图代次。不要将不存在的字段作为已有合同。

**guild revision 不能单独代表成员集合代次。** 真实存储验证中，家族审批新增一位成员，使帮派派生成员从18变19，guild revision 仍为3。成员退出/重入应使用已有 family_token/member_token；未来组织空间授权还需要主集成裁定的地址绑定代次。不能自行猜 `instance_id == guild_id`。

## 地图/NPC 证明能证明什么

现有 MapAddress 包含 map_id、instance_id、partition_id。GameRuntime.map 按完整地址建/取所有者，registered_map 精确查已注册地址。NpcScene.interact 验当前租约/位置版本、完整地址相等、active、实体/placement、地图范围和距离；NpcServices.plan 生成冻结 NpcServiceCommand，携带地址、位置版本、角色租约、NPC/服务及期限。

它们证明“角色在此实例中可与这个 NPC 交互”，**不证明“此实例属于角色当前帮派”**。NpcInteraction/NpcServiceCommand 没有组织 ID 或组织空间绑定代次。NPC entity_key 仍按 `(template << 32) | placement_id` 生成，同模板跨实例可能相同，必须连同完整地址使用。

客户端目录的真实模板1394是动态“练功房/帮派练功房”：p1=10076师爷，位置(624,673)、方向5；p2=10077教头，位置(382,622)、方向3；p3=10221，位置(641,863)。这些是模板与摆放证据，不是准入政策。verify_practice_npc 中10077/location1007/key123是隔离夹具，不是实际绑定。

主集成先确定组织→完整地址绑定、有效代次及角色准入，再向角色路径提供可信证明。即便地图模板、NPC 与角色帮派成员关系各自有效，也不能让另一个帮派实例里的角色使用服务。practice_npc 不具备该缺失政策，实际路由应等待此条件建立。角色层还须检查战斗/loading；Location.active 不能单独证明不在战斗。

## 现有修炼 Adapter 与失败合同

practice_npc 已有 `open_panel → prepare_purchase → OrganizationRuntime.command → finish_purchase → resolve_practice`，具体参数、资源回调和原生返回见 GUILD_PRACTICE_NPC_RUNTIME.md。当前未在 registry/GameRuntime/runtime_storage 注册调用。

prepare 从当前成员关系派生 guild，c36cc 的 Q 只作 NPC 身份，不能作帮派 ID。冻结 PreparedPractice 保存本次 NPC scope/位置/原请求；组织 reserve 校验成员代次并持久保存前态、费用与期限。角色事务须在等待组织命令前退出；finish 重取可信 NPC 证明、核对原 scope/位置/期限和当前租约，再在传入角色事务结算。

相同 actor/request_id 的组织命令指纹涵盖 organization/operation/args；相同意图重试取旧结果，改变意图拒绝。每次仍检查当前租约和请求 deadline；指纹不把 epoch/deadline 当业务意图。客户端包没有幂等 ID，共享入口须为同一已受理尝试保留服务器 request_id。已经付款的角色公共凭据重试返回当前技能/资产值，不重复扣款或消耗丹。

现金预留3资材；丹0现金/0资材，角色事务通过公开 Inventory.apply_settlement 消耗36747并与 XP/公共凭据原子提交。丹正式调用须提供 managed-resource/source precommit，不能用空回调绕过资源围栏。最终编码异常整体回滚，提交成功后才发逻辑包。

resolve 看到公共角色凭据则确认；无公共凭据、无资产/钱包 child 则取消，现金退资材。只有 child 却没有公共凭据返回 practice_outcome_unknown 并保留预留，等待明确修复。超时不等于已撤销，不能据此直接退款。登录有界恢复处理旧 epoch/到期预留，当前 epoch 未到期不取消。这是同 SQLite Adapter 内已验证合同，跨库 saga 仍未完成。

## 当前频道迁移兼容

原七字段快照仅带模板，完整地图工厂本身不能隔离聊天。现已按主策划裁定增加可选冻结 scene_scope 和唯一 scene_key；当前频道 Publish 使用完整键，旧公共调用保持整数键兼容，门派/世界不变。主集成负责从真实角色归属填入 scope、索引同键、同模板切实例也提升快照版本并清理旧成员；具体固定 Interface 和验收见 SOCIAL_SCENE_SCOPE_HANDOFF.md。组织频道保持组织范围，不按地图缩小。

## 本批证据与完成判定

verify_organization_npc_contract.py 使用临时库、真实 OrganizationStore/RoleSocialOwner 验证已有资格与 guild revision 缺口；完整地址仅注入隔离冻结夹具，未验证实际组织入场。organization-npc-contract-audit.json 保存观测与源码哈希。当前频道小 Interface 的红绿和实际 SocialRuntime 输出另由 verify_social_scene_scope.py 验证。

启用真实 NPC 前须补齐并实际验收：组织空间准入/代次，真实服务注册与共享路由，角色状态/两段 NPC 复验，managed-resource/source 消费，价格/上限等完整原生面板，原客户端购买/重登/断网恢复。上述未满足时，全量恢复状态继续未完成。

方法：codebase-design 复用已有深 Module 的公开 Interface，记录真实可变/冻结结果和所有权；writing-for-agents 将能力、限制、接入顺序与可判定验收共置。没有声称代码审查双轴或实际私有地图验收。

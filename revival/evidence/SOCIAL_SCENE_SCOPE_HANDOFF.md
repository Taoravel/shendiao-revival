# 当前频道完整场景范围交单

2026-10-23。按主策划 PRIVATE_SCENE_SCOPE_DECISION.md 实现；本页是社交侧固定 Interface，主集成接角色地址与成员索引时读取。没有部署或重启。

## 可直接使用的 Interface

`social_owner.RoleSnapshot` 原七个位置参数保持原顺序，末尾增加 `scene_scope: tuple[int,int,int] | None = None`。冻结快照在构造时验证：精确三元 tuple、各值严格 int（拒绝 bool）、范围 `[0,2**63)`，map_id/instance_id 大于零、partition_id 非负，map_id 与整数 scene_id 相等。已提供 scope 时不接受可变容器或模板不符；None 保持旧调用契约。

唯一分组入口 `snapshot.scene_key`：None 和显式公共 `(map,map,0)` 均返回原 scene_id 整数，其他返回完整 `(map,instance,partition)`。scene_id 继续表示原模板，profile 与原聊天线格式没有新增字段。完整 scope 由可信角色归属生产，客户端聊天包不能指定。

`Publish.partition_key` 类型合同为 `int | tuple[int,int,int]`。RoleSocialOwner 的 CURRENT_CHANNEL 输出使用 scene_key；门派、世界输出仍是原整数键。SocialRuntime 的现有冻结快照发布/请求及 revision 围栏原样传递该键；没有新增所有者、全局队列或跨所有者可变对象。

发布范围确认：social_runtime.py 的 `guild.initial(self)` 属于此前第十一批个人修炼登录投影/预留恢复，交付在 GUILD_PRACTICE_NPC_RUNTIME.md 与 guild-practice-pill-batch.json；它不是本次 scene_scope 变更。scope 固定副本内记录 social_runtime.py 仅用于验证依赖哈希，主集成可将该旧组织批单独审查/发布，本批不要求混入或回退它。

## 主集成接入与完成标准

主集成负责 RoleOwner.snapshot 从真实完整归属生成 scene_scope；GameRuntime.index 使用同一 scene_key。即使模板没变，换 instance/partition 也须提高 snapshot_revision，并在目标归属激活后删除旧成员、加入新成员。未知私有归属按世界合同拒绝，不能退成 None。当前频道键代表地图实例及分区，帮派频道仍代表组织，二者不替换。

上线前验证真实私有角色同模板不同实例/分区不串频道，同一实例互通；公共 None 与显式公共互通；换图、重登和旧 epoch 清除旧成员。排队中的发送/收件作用域仍须按主集成的完整迁移合同核验；本次快照 revision 拒绝旧请求，不等于已经解决所有延迟广播的跨地图投递。

## 已验证与未验证

verify_social_scene_scope.py 六组通过：旧构造/public 归一化；完整私有身份与冻结；非法值拒绝；真实 RoleSocialOwner 完整 Publish 及原包体；其它频道不变；真实 SocialRuntime 在临时数据库中 publish/request 并拒绝旧 scope revision。前三个实现纵切均观察到先红后绿：缺 scene_scope、接受 list、当前频道仍输出模板。运行时补充与回归不声称曾红。

测试通过公开 Interface 注入冻结身份，未创建真实帮派地图、未验证私有收件人分发或原 GUI。没有编辑共享入口及世界 Module。机器结果见 social-scene-scope-verification.json；固定源码/验证哈希见 social-scene-scope-batch.json。

方法：codebase-design 将规范化集中于快照的小 Interface；tdd 逐个公开行为红绿；writing-for-agents 将兼容规则、所有者分工和验收标准共置。组织 NPC 资格另见 GUILD_NPC_ACCESS_HANDOFF.md。

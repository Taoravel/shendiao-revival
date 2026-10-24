# 普通血脉精华事务接线

2026-10-23。36117的消耗、有效资质、真实潜能和当前原生回复已在所属模块实现并离线验证。共享路由、部署、实机、血脉奖励与完整进阶另验；全量目标保持active。基线与来源分别见PET_BLOOD_BASELINE_DECISION、PET_BLOOD_RESEARCH；数值唯一来源为design/pet-blood-v1.json，本批未改数值政策版本。

## 接线与完成条件

角色Owner完成非战斗、地图/交易/传送资格及稳定request_id受理后，经有界持久化执行调用：

```python
inventory.receive_pet_consumable(body, epoch, request_id, now_ms, precommit)
```

body为原CUseItem的16字节`>iiQ`：实例key、目标kind1、pet key。该Adapter统一支持宠物HP/MP药、食物及36117；调用方无需从实例key猜模板。now_ms为可信Unix毫秒，可无到期技能时传None；有到期map则必须给时间，回复先含原c0007。precommit为同步根来源hook，沿INVENTORY_RESOURCE_HOOK_INTEGRATION约定接收同db/current frozen snapshot及经真实凭据验证的replayed。以上参数可位置传递，适配当前仅支持*args的owner I/O。旧receive(USE_ITEM)继续支持旧普通药/食物，但精华明确拒绝缺上下文路径。

可信组合事务可用`use_pet_blood_essence(db,key,pet_id,epoch,request_id,expected_version)`。db必须为当前角色fenced事务，不开连接或内部commit；expected_version是成长版本，None仅用于Owner从当前状态执行的原生Adapter。返回冻结BloodReceipt，其中before/after是历史PetProgress，replayed表明有效旧凭据；不能把历史after作为当前通知。外层还需构造当前回复、同步根source及完整commit。

验收条件：新命令只消费一次，当前有效租约和owned live pet均成立；同事务保存能量、成长/resources、物品和领域凭据，root source与共同受理凭据由precommit同事务加入；提交前完成原宠刷新与实际cash背包编码。任一环失败整个事务回滚。原生请求若重试，由稳定request_id识别，当前回复保持后来成长、分配、伤势或忠诚，不再次产生效果。

## 重试与来源

新`inventory_pet_consumable_commands`保存role/request_id/body fingerprint。鲜请求的hook为False；已有共同消费凭据严格比对body后为True。若低层血脉凭据已付但尚无wrapper凭据，Adapter验证完整领域fingerprint后同样True，且保持严格只读，不补写wrapper/source。物品实例已经耗尽删除仍可读历史低层凭据。意图冲突、旧租约、他人/已放生目标、未知血脉、封顶均拒绝。

根共享共同受理表的迁移和paid判定仍由集成方负责；通用paid消息入口另见INVENTORY_CURRENT_MUTATION_MESSAGES。此Adapter自己的领域消费凭据不能被解读为已替代所有共享共同命令凭据。LEARN_SKILL_BOOK的可信draw/context factory仍是独立接线事项。

## 实际行为与来源边界

原配置/原生消费者支持每颗+200、普通等级闭区间、颜色等级上限、每级10潜能和原Pet字段。当前版本的服务端取整、颜色封顶取upper bound/余量丢弃、保留缺失HP/MP且死亡不复活为designed；原物品needLevel1与原帮助45级/不参战冲突，按具体物品采用角色1级门禁仍为designed裁定。由Owner执行场景/战斗资格，不借独立c07e7的类名猜测精华协议。

基础Profile不回写血脉加成。每次有效精华增加blood.version和growth.version，即使未跨级；只有真实跨级才增加潜能。白色上限1139/3级，继续使用不扣物；当前普通最大15级。未知旧宠血脉保持None，需要完整可信基础资质与power一次导入。原1160的旧“根骨”名称现已纠正为独立悟性，已知存档见PET_TRAITS_INTEGRATION；蜕变、颜色进阶、放生能量/兑换与奖励、动画通知仍未实现。

## 方法、产物与验证

tdd沿已约定Inventory事务/不可变快照/原生receive Seam，从缺Interface的红例完成精华纵切，并逐步加入真实失败和历史重试。codebase-design让血脉写入和有效成长投影集中，避免基础资质反复叠乘；writing-for-agents按接线、事务、重试分支给出可判定完成条件。

verify_pet_blood_items与pet-blood-items-verification.json证明实际一件扣除、+200、白色1139封顶、30血脉潜能实际分配、旧请求当前回复。L10实例上限262/105→263/106时伤势20/10→21/11，原decoder读到潜能80；真实上限增加仍不复活死亡宠。真实blood/growth/两份凭据abort、外层异常、未知cash和晚期bag溢出均回滚；同失败键随后可正常提交。SQL禁止写入时低层历史重放仍成功，实际opaque LeasedAccounts换租约通过。普通药/食物同键重放不会治疗后来伤势或补回后来忠诚损失；限时技能保持原map并带当前时钟。

verify_inventory_resource_hook已加入实际精华鲜请求False/历史True，与根synchronize_inventory_resource_source共事务；角色70/40及resource version0保持，来源更新只跟当前资产。必要成长、养护、技能/到期/绑定、原生背包、事务/快照/租约、人物资源药及任务宠物经验回归通过。当前验证为临时数据库与原客户端指令执行，无在线角色改动、服务重启、GUI或实际战斗验收。

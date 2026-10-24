# 新手宠物参战状态任务：十一条独立完成能力

2026-10-23。原配置、请求与当前setter研究见 [TASK_FIGHTING_PET_OBJECTIVES_RESEARCH.md](TASK_FIGHTING_PET_OBJECTIVES_RESEARCH.md)。本批按ARCHITECTURE和DESIGN_AUTHORITY实现，只修改任务所属Module；没有修改Inventory、资源/成长Module、共享入口或正式战斗。方法采用research的原PFS/原指令追溯、codebase-design的当前事实reconcile Seam、writing-for-agents的顺序和完成判据；用户要求批量恢复，仅做必要事务检查。

## 能力和明确的恢复政策

原11条为`100189,100289,100389,100489,100589,100689,100789,100889,100989,103289,101014`，均type59、NPC0/地图1006、原EXP200、其余奖励0、无Start/Finish对白、无物品/宠物奖励或宠模板要求。只有这些精确ID且无额外机制才符合`supports_fighting_pet_task`，其余80条type59继续按各自机制处理，包含已有师父武器任务。

采用本地政策`current_selected_owned_pet.1`，来源状态为**designed**：已被可信服务器流程激活的这11条任务，在当前1006/active世界位置，读取同事务实际资产后，若恰有一只自有、未放生、fighting=1的宠物，即可结算。可在实际参战命令成功后、任务激活后或可信重登恢复中reconcile；不要求重新点击一次。无当前参战宠则返回waiting且无写入。原表没有指定模板/实例、HP、血脉或宠经验资格，不附加角色+5/宠HP>0等奖励渠道条件。

这项政策不是原服触发已经取得。原CSetFightPet只带正i32宠key，原SSetFightPet设置当前角色+190并通知宠UI，所读路径无任务ID。任务完成须看实际资产状态，单纯收到请求、缓存key、历史参战回包或客户端CCommit均不构成完成事实。宠选择的等级、忠诚/寿命等合法性由真实Inventory命令执行，任务不绕过它们。

11个原前驱均type40/AI8003，11个后继均type40/AI8028，其中后继Animation30045。前驱赠宠/捕捉和正式战斗未在本批恢复，不能从描述推赠500001或其他模板。完成这组目标后，公共续接将未开放战斗后继保留`pending/successor_gameplay_unimplemented`，不跳过、不模拟胜利、不替代后继奖励。

## 精确接线

启动只读加载`fighting=task_fighting_pet.load_fighting_pet_task_resources(task_resources)`，不做DDL、任务激活、宠生成或位置迁移。

可信角色所有者在调用方现有租约事务调用：

```python
result = reconcile_fighting_pet_task(
    db, account_id, role_id, epoch, task_id,
    task_resources, fighting, inventory, current_location, request_id,
    growth_rules=growth_rules, attribute_rules=attribute_rules,
    currency_rules=currency_rules, pet_experience_rules=pet_experience_rules,
    resource_rules=resource_rules, equipment_rules=equipment_rules)
```

`current_location`由世界所有者提供，鲜完成要求同角色/当前epoch、active、地图1006；不是由线包直接构造。Inventory用实际`immutable_snapshot_transaction(db,epoch=epoch)`先围栏租约，再读公开`selected_fighting_pet(db)`并与同事务完整快照核对唯一选择。后者本身只有角色归属检查，不可单独当作租约检查。

实际`CSetFightPet=0xc07d8`仍走Inventory原4字节请求，不新增任务完成协议。当前可用公开`Inventory.receive(FIGHT_PET,body,precommit=...)`，其实际选择变更后、提交前执行同步hook。组合顺序：

1. 角色所有者校验当前连接/请求/世界状态，将原宠命令交给实际Inventory。`receive`会校验原宠uselevel与当前人物等级；不要用低层测试方便调用取代该合法性检查。
2. hook接收同一个db、Inventory、当前InventorySnapshot和真实replayed决定。先由现有资产命令的持久意图确定fresh/paid；对鲜选择，调用根公开`synchronize_inventory_resource_source(...,request_id,resource_rules=...,equipment_rules=...,replayed=False)`完成inventory_change。它不改变HP/MP/caps数值，只收敛实际资产来源；已付重放严格读当前来源，不能修补。这个阶段归实际资产命令所有者，任务reconcile不隐式补做。
3. 在该db继续调用本任务reconcile。TaskWorkflow严格验证当前source、按原200XP结算成长/资源、保存原任务/后继和`fighting_pet_objective`manifest；manifest保存原定义指纹、原实际宠key/template、资产revision、世界Location及政策。
4. 任务内层编码当前钱包/背包/最终完整属性和完成消息。Inventory原参战回包和任务消息都准备成功才提交。外层提交成功后才发布任务结果并把两组逻辑消息交目标连接发送；异常时丢弃暂存结果，整笔回滚。

若已有外层角色事务，应使用资产所属窗口提供的同事务变更契约或hook，不从任务Module调用`fight_pet`先提交再开另一个任务事务，不访问资产私表或私有`_fight_pet`。

可信恢复可在当前source已精确同步时直接调用reconcile，不重复执行宠命令。已完成任务须有同原定义及政策的持久manifest；可省略旧Location，也不再要求原宠当前仍选中。读取当前成长/资源/资产确认，不重新选择原宠、不付第二次200XP、不重播state1。旧epoch仍拒绝。未知旧完成记录没有manifest就明确拒绝核对。

现TaskChain对唯一合格原边支持激活这11条，TaskConversation只恢复active0跟踪，不把NPC0任务变成普通NPC提交。实际激活仍由原前置可信玩法决定；本批没有开放战斗注册或跳过前置。

## 必要检查和未验范围

[task-fighting-pet-check.json](task-fighting-pet-check.json)为当前`verify_task_fighting_pet.py`结果：11原任务200XP/零项/前后边纯计划及普通对白绕过拒绝；实际`Inventory.receive`正4字节CSetFightPet、同事务precommit和唯一资源Module；没有选择时零写等待、错图/漏source阶段/半规则/旧epoch拒绝；晚期背包编码失败全库回滚真实选择/source/任务/奖励/成长；相同身份重试一次得到原200XP；明确70/40基线自然L2/XP111/free5、80/110HP46/106MP/version1；后来换宠、休息、换租约后确认当前值，不重选旧宠或重发奖励，后继战斗正确pending。

初次夹具误用了500001（原uselevel5）配人物1级，被真实参战入口拒绝。已改成明确临时500138（原uselevel1）再跑原完整检查通过，保留真实等级门禁；此模板只是已知测试资产，不称原故事赠宠已复原。位置和任务offer也是可信夹具，没有自然完成AI8003前驱。旧交钱及86师父武器选择的必要兼容检查通过，未扩大全面回归。

本批7个源码AST及5份交接/研究文档的本地链接检查通过。type13另交原生意图及资产接缝，见 [TASK_PET_SUBMISSION_INTEGRATION.md](TASK_PET_SUBMISSION_INTEGRATION.md)，不能与本11条参战状态完成能力混计。

共享RoleOwner的宠命令hook/任务激活恢复尚须主集成接线；本批无自然完整前置、客户端GUI/实际跟踪、原赠宠来源、正式战斗、在线服务或商业并发验收。领域11条实现与GUI/共享启用数分开记录。

# 宠物绑定存档与绑定秘籍学习

2026-10-23，源码冻结解除后完成。191条原秘籍映射（95普通、96绑定）保留为来源；后续到期恢复已确认其中两条对应200534空标记，当前实际能力书189条（94普通、95绑定）。学习受等级、已学列表、到期有效性、血脉上限及重复/较弱技能检查。时间与空格规则见PET_SKILL_EXPIRY_DECISION.md。共享c07ff Owner路由尚未接入本Adapter；GUI及完整交易流程未验收，源码存在不代表当前部署已包含。

## 接入与持久化

启动调用`Inventory.prepare`加载只读`FlagRules`并建立`inventory_pet_flags`。政策为`design/pet-flags-v1.json`，冻结状态`PetFlags(version,raw)`保留完整一字节，`bound`投影bit1；`PetState.flags`新增末尾默认None字段。装备事务、同事务快照、装备事件及双栏消息的公开签名保持原样。

新发普通宠物与成长/养护/技能同一事务保存明确raw0，属designed初始规则。旧宠没有标记记录时保持None，不能由模板、物品绑定或默认编码推断；可信已知完整原字节通过`initialize_pet_flags(db,pet_id,raw)`一次导入，已有记录及他人/放生实例拒绝重置。标记随当前完整PetState快照传递，重登、学习、加点与养护不重新生成。

调用方继续用`learn_pet_skill(db,book_key,pet_id,epoch,request_id,expected_version,draws)`，参数及可信角色所有权要求不变。绑定秘籍需要已知flags；合法技能计划完成后，在同一租约事务内置bit1、保留其他位、扣精确一本、保存技能与资产版本及幂等回执。已绑定宠物不重复改变flags版本。重复、较弱、旧租约及未知旧标记均在成功提交前拒绝；历史回执增加可选flags_before/flags_after，旧回执缺这两项仍可解码。

`receive_pet_skill_book(body,epoch,request_id,draws)`保留24字节默认末四项全-1分支。绑定学习及其已提交请求重放，除当前完整SRefreshPetData/现金背包外，额外在同一事务内编码当前完整SGetPetcolumnInfo，再恢复当前参战选择；编码或存储失败全部回滚。原因与原指令证据见`PET_BINDING_RESEARCH.md`：单独标记/数据刷新不更新原绑定查询缓存。重放读取当前所有宠物及技能，不将历史技能/flags写回。

`require_pet_transferable(db,pet_id)`是预留前资格门禁：要求已知raw0、未参战、归属当前角色且未放生；绑定、未知标记、其他尚无转移规则的位拒绝。完整跨角色交易仍由独立交易状态机负责，此门禁不交付资产、不启用交易。

## 来源与验证

客户端确认：petbangding映射、Pet+dc字节、bit1、完整栏转换及绑定查询、标记刷新缓存差异。服务端“成功绑定秘籍学习后置位”、新宠raw0、转移门禁是明确恢复设计；数值学习/扩格规则仍沿用pet-skills-v1，无新增概率猜测。秘籍末四项认证符/技能身份及到期map分开见`PET_SKILL_OPTIONS_RESEARCH.md`。

`verify_pet_binding.py`通过公开Inventory Interface和真实临时库验证：精确扣一本与学技能/绑定同时保存；无效学习不绑定、不消费；已经绑定时升级无标记版本抖动；raw128→130保留其他原位；Unicode名字与非空列表不移动错绑定位；旧请求回复当前技能；真实flags保存/回执写入失败、外层失败、缺钱包及过期租约均无部分效果；旧未知、显式导入不重置、他人/放生、转移门禁、重开保存。完整原SGetPetcolumnInfo decoder之后继续执行原转换投影和完整原绑定查询，核对回复所有宠物的raw/bound。

回归通过：verify_pet_skills、presentation、care、growth、native_commands、consumables；verify_inventory_transactions、snapshot_transaction、cash；verify_task_pet_experience。本批未运行在线服务、原客户端或实际战斗，也未改共享入口。后续认证保护/拓格进度和到期领域已补，分别见PET_SKILL_LEARNING_DECISION和PET_SKILL_EXPIRY_DECISION；真实GUI、共享路由、定时/内容渠道、技能战斗效果及高级宠物玩法仍待恢复，全量目标active。

## 方法与产物

沿用`codebase-design`：pet_flags集中完整字节/绑定持久化，pet_skills组合原子学习，Inventory在既有调用方事务Seam组合当前逻辑回复。`tdd`先在公开snapshot/receive处复现“新宠无绑定存档”，通过后再用未知其他位转移反例收紧门禁；没有修改装备公共Interface。`diagnosing-bugs`使用原codec→消费者反馈，并用真实DB中断验证回滚；`writing-for-agents`把接入、来源与完成条件集中本文。

产物：pet_flags.py、pet-flags-v1.json、Inventory局部接入、可选回执字段、research_pet_binding.py、verify_pet_binding.py、pet-binding-verification.json；冻结期仅证据与文档，源码变更均在解除冻结后进行。

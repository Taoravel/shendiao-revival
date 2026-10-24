# 首师父选择卡、装备目标与当前人物总属性：共享运行时接线

2026-10-23。源码接线已完成，当前验收发布PID8724保持不变。本页记录原始集成窗口的共享Adapter；原事务/数值/来源契约分别见TASK_MASTER_CARD_INTEGRATION、ROLE_EQUIPMENT_DECISION。原选项和属性映射来自客户端，绑定、精确实例目标和裸身封印0是集中设计；来源和GUI验收状态分开。

## 实际顺序和完成条件

1. runtime_storage.prepare启动一次加载卡规则、装备属性规则并建表；成功后才公布只读依赖。load_role从独立newbie creation ID取得角色/门派来源，显式保存该角色的seal basis0。无来源的旧角色仍走已登记兼容路径，不从等级、空字段或XP补基线。
2. RoleOwner接地图真实NPC实体/距离/位置版本证明后，由master_dialogue读当前租约和active原师父任务；返回冻结票据，原ready3完整bean和原菜单。NPC访问/移动/关闭/换图清当前对白票据。共享I/O只接冻结票据及证明，不传可变TaskConversation。
3. CCommit仅确认，CQuestDialogEnd经当前ticket/location/generation授权原卡；CGetCardItem选择必须匹配持久permit、原effect及两项之一。master_choose将实际绑定实例、师父任务完成、奖励/唯一type59和当前总属性预编码放在同一角色事务；提交成功才发布角色快照/发送消息。没有使用CG结束包领卡。
4. EQUIP/UNEQUIP均经公开调用方事务Interface。当前精确获领实例穿到slot0后，在同事务完成type59、结算并激活原车夫任务；普通/旧角色仍可经通用穿脱入口。历史命令只应答当前状态，不按旧凭据重穿。编码失败时资产和命令/任务凭据整体回滚。
5. _role_profile_transaction从当前裸身成长、同事务InventorySnapshot和显式basis重算EquipmentRoleSnapshot，输出20项绝对全map，含1230。TaskCompletion原裸身全map被替换，成长/加点也使用同一当前组合；不把已投影总值回写裸身账本。HP/MP用药、客栈等部分刷新保留原局部更新，不追加提交后可能失败的资产改写。
6. 入场RoleLoadProfile含当前growth、装备总投影和恢复任务bean；world_snapshot显式消费growth_snapshot，同源五维/潜能/战斗槽。已完成章可在角色事务核对已实际装备的精确实例并恢复遗漏type59完成；重连只同步现有active卡/59/车夫，与普通对白/章后继按任务ID去重，不自动发卡或装备。
7. 修理走repair_role_equipment→npc_repairs.repair的同事务precommit，公开equipment_projection_messages(db,accounts,inventory,current_snapshot)在修理/费用/凭据提交前编码当前全map。编码异常交外层回滚；该hook也可供未来磨损调用方使用，当前未新增磨损wire或战斗执行。无来源/未知旧属性路径返回原兼容显示，不猜封印值。

## 已执行验证

- verify_first_master_runtime：主策划原反馈在真实Owner首师父处缺ready3而红；本窗口接线后默认绿，主策划独立复跑。自然建角/开场后沿已审计清路的原移动报告到真实古墓师父；提交不提前完成、对白结束才开卡；非法/未授权/另一按钮拒绝；选择一次绑定原武器，不自动穿戴；重登不重发；真实穿戴完成type59/激活车夫；穿脱45/35/8↔20/20/0；重建Owner及原SEnterWorld字段保持45/35/8。
- verify_equipped_growth_runtime：独立受控legacy L10成长/XP/武器/已知basis夹具，真实Owner登录45/35/8→升级49/38/8→力+1为51/39/8；脱装26/24/0、重穿与重登51/39/8。实际最终全map编码处失败，穿戴与其命令凭据一起回滚。这个受控fixture不是自然新角色链，初始错误预期忽略力量对内攻的原系数，按当前已登记属性政策修正检查值后通过，没有改生产数值来迎合检查。
- 主策划verify_role_equipment_repair_hook独立通过：实际共享hook，损坏0→修复45/35/19，伤势HP70/MP40保持；晚期编码失败和seal16777217 float32拒绝均使修理/费用/凭据回滚；重试不重抽。范围是NPC领域fixture+真实shared hook，未冒称含装备profile的NPC wire操作已验。
- 受影响兼容路径必要回归：verify_manual_level_runtime、verify_new_character_growth、verify_role_lifecycle_runtime、verify_task_tracker_runtime均通过。临时库、连续原RC4/MPPC，不涉及战斗、真人端口或现场角色写入。

## 尚未完成

本批未部署、重启或操作客户端，用户验收发布仍为063445Z副本PID8724。真实领卡/穿戴界面、行走、修理UI和原生表现仍待后续授权版本验收。43路线领域卡选择已由任务模块验证，实际共享自然Owner路径本批只测古墓角色9；不将其扩成43组合GUI通过。

本批只激活车夫任务，车夫对白提交、奖励/嘉兴目标与世界durable transfer须按NEWBIE_CART_TRANSFER_DECISION接入统一调用方事务；不能用两次独立提交完成。完整序章、其他装备/高级修饰、战斗数值与商业容量仍未恢复完毕。

## 方法与决定

codebase-design把当前组合投影集中在存储Seam，隐藏资产/裸身读取与编码时序；diagnosing-bugs使用既有自然Owner缺师父反馈和追加编码失败回滚检查；writing-for-agents按启动、授权、选择、穿脱、刷新、重连和修理共置调用顺序及完成条件。没有增加世界锁、全服串行执行器或第二份增量总属性账本。准备期遇到社交规则tuple/list不一致阻断启动，交所属窗口修复，未在共享入口绕过组织初始化。

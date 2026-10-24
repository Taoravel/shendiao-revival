# 交宠type13：原生意图与资产接缝

2026-10-23。原14条完整配置、mode2构包和原限制见 [TASK_PET_SUBMISSION_RESEARCH.md](TASK_PET_SUBMISSION_RESEARCH.md)。本批已新增`task_pet_submission_protocol.py`及`task_session.decode_task_pet_submission_intent`纯解码；**没有开放交宠完成或扣宠，正式完成能力仍0**。不调用free_pet、不写Inventory私表、不从CSubmit2Npc伪造任务完成。归属遵循ARCHITECTURE；实际资产Module与共享入口由所属窗口维护。

## 原协议可以直接接入的部分

`CSubmit2Npc=0xc2340`的mode2为单宠意图：`BE i32 taskID | u64 npcKey | i32 2 | compact count1 | i32 petKey | i32 1`，25字节。返回冻结`TaskPetSubmission(task_id,npc_key,pet_key)`。NPCkey正signed63保留完整64位布局；宠实例key是正signed32，不能把模板ID当实例或截断大于signed32的恢复库ID。

`decode_task_pet_submission_intent(kind,body)`只接受该type和mode2/一个unit/数量1；mode1继续交物，mode3继续交钱，各解码器互相拒绝错误模式。包无资格、宠类型、版本、客户端重试ID或完成证据。其存在不应使共享菜单把未支持的type13投影ready3；当前普通TaskDomain仍拒绝type13的普通对白完成。

原离线构造+marshal输出`00032e14 1122334455667788 00000002 01 12345678 00000001`，对应task208404、宽NPCkey和宠key0x12345678。新codec按这份独立原指令输出核对，完整原14字段/列表与当前任务catalog比对记录在 [task-pet-submission-source-check.json](task-pet-submission-source-check.json)。

## 正式完成仍缺的具体事实

原客户端排除参战key、展示key、加锁宠、宝宝；自动选择要求实例kind1且模板匹配。锁和绑定不同：完整raw flags的mask0x05派生锁，mask0x02派生绑定。mode2此链检查锁，未见绑定检查；恢复服是否允许绑定宠须由主策划另定，不能拿通用交易`require_pet_transferable`的“raw非0一律拒绝”冒充原交宠规则。

当前公开PetState包含owned实例/template、fighting/released、可选完整flags，以及成长/血脉/养护等。已知完整flags可以按原mask识别锁，但**实例野生/宝宝kind和当前展示宠key没有公开权威状态**。宠模板cpetattr.kind和care.grade均不能代替实例kind；后者是血脉/养护等级。旧实例flags未知时也不能补0当作未锁。等级50是原防误交二次确认，非任务最低宠等级；确认本身仍不是服务器资格。

14条中6条`$round$`任务要周期实例和新幂等空间；102508另有Transform6028；其余7条无这些额外字段，但活动/NPC可见和所交宠实例事实仍须满足。208404有MinLevel53、原EXP50000/PetEXP30000/SMoney15000，不能在不扣真实宠时付出这些奖励。原后继、绑定奖励和Finish均保持原表，不用本协议解码完成任何一条。

## 交给资产所有者的最小Interface需求

先由宠物所有者提供同事务、当前租约/版本围栏的公开交付Interface，而不是让任务调用放生包装。建议契约如下（**不是当前已存在的方法**）：

`submit_pet_transaction(db, pet_key, epoch, settlement_id, *, expected_inventory_revision, expected_template, eligibility_policy)`

它在调用方已BEGIN的同一角色事务内重读真实归属/未退休、精确模板、野生kind、非参战/非展示、已知锁和明确绑定政策；未知必要元数据拒绝。成功退休该唯一实例且保留成长/奖励FK和交付审计，推进inventory revision，写同键意图指纹/receipt，返回不可变实际交付事实。相同已付键只确认历史交付并读当前资产，不再退休另一只；异key/template/政策等冲突拒绝。不得另connect/commit或发送；不存在该公开能力前任务Module不自己补SQL。

未来任务组合：鲜操作入口先严格读当前资源→核当前NPC/任务/原模板/许可→实际资产交付→依据真实fresh/paid决定收敛inventory_change→共同TaskWorkflow结算奖励/原Finish和后继→保存原任务支付manifest/公共凭据→提交前编码。已有资源profile时交宠推进inventory source，必须在TaskWorkflow当前来源检查前完成正确来源阶段，不能等到登录或借人物ordinary_growth洗掉资产变化。晚期编码/奖励失败应全部回滚实际宠交付、资源、XP/钱包/道具/任务/凭据。

交付宠本身不能同时作为当前参战奖励接收者；普通任务宠XP仍沿既有冻结接收者政策。重连付过的任务只能按原交付manifest确认当前奖励/余额，不重扣新同模板宠、不重播state1/Finish。资产交付receipt不能替代活动触发/周期/变身事实，也不能从客户端只传petkey判断已交付。

## 方法、检查与范围

research直接原PFS/BXML、原构造/validator/marshal及锁/宝宝/Finish指令片段；codebase-design将wire意图与真实交付Seam分开，复用公共CSubmit2Npc字节结构但不复用itemkey语义；writing-for-agents共置已证形状、缺失的实例事实和所需公开Interface。

本批检查为原14记录完全匹配、新codec与原25字节输出一致、错误mode/数量/空列表/截断/过宽宠key拒绝。未做扣宠/奖励事务、活动资格、自然捕捉/交付、GUI、共享连接、部署、在线状态或战斗。本文是具体资产接缝交接，不能据此声称14条可玩任务已经恢复。

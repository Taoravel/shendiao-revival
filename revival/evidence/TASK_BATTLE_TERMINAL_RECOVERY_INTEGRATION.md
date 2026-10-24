# 首战原终态：新租约恢复与已付当前查询

2026-10-24。按主策 `TASK_TERMINAL_RECOVERY_DECISION.md` 的 `2026-10-24.task-terminal-recovery.1` 实现Task所属Interface。固定候选取 `reviews/task-battle-terminal-recovery-20261024-r2/source`；不要从工作区整批覆盖共享副本。没有改变原战斗事件epoch或原admission，普通settle/ack原入口和拒绝条件保留。

## 调用方与Task分别验证

main经所属公开Interface读取真实durable producer原件，核原正式engine/完整admission和Participant、原事件全量指纹、库存/装备/人物资源/宠物/技能等真实完整前态CAS。仅在当前唯一角色恢复流程中构造冻结 `TaskBattleRecoveryWitness(role_id,current_epoch,admission_fingerprint,terminal_fingerprint,producer_receipt_id,producer_fingerprint,source_fingerprint,recovery_revision='2026-10-24.task-terminal-recovery.1')`。它不是客户端授权，也不能以“DTO里有hash”替代实际producer读取和source核验。

terminal指纹为原 `asdict(finished)` 经 `json.dumps(...,sort_keys=True,separators=(',',':'))` UTF8字节SHA256，与Task既有canonical规则相同。producer/source指纹由main绑定真实producer/source读取结果；Task不通过main私有SQL另造第二份权威。恢复receipt在main消费者中保留原accepted epoch、原terminal指纹、当前settled epoch、上述恢复版本和唯一settlement ID。

Task自行核当前owner/lease、原scope与事件资格、原admission/任务/AI/原定义、engine、Participant角色/原epoch/属性版本和完整事件指纹绑定。pending时核原任务仍active及当前人物任务资格。registry必须仍显式支持该正式能力。源漂移/未知来源由main拒绝并保留producer pending，不覆盖当前资产。只换租约不能换业务前态。

## 两个公开Interface

`recover_task_battle_transaction(db,aid,rid,current_epoch,resources,registry,original_finished,inventory,witness,*,growth_rules=None,attribute_rules=None,currency_rules=None,pet_experience_rules=None,resource_rules=None,equipment_rules=None)` 只消费**旧租约**原真实终态。主集成在一个角色事务内组合当前完整资源/专用梦境恢复、Task原奖励/终态、首技唯一后继、consumer回执及outbox settled标记；最终消息编码通过才提交。Task不自开连接、不commit/send、无新DDL。缺producer时走真正中止，不调用此方法制造胜利。

fresh返回原TaskBattleSettlement，含completion/messages，可按原奖励合并方式处理。已付相同终态返回completion=None/replayed=True以及当前人物经验、钱包显示和人物资源profile消息；不补奖励、不跑TaskChain、不发state1或电影。当前技能/宠物及其余角色投影由各自所属公开读取Interface补全；不得用旧终态覆盖后来合法成长/资产或向未知技能发送空map。

`read_task_battle_current_transaction(db,aid,rid,current_epoch,resources,registry,original_finished,inventory,*,currency_rules=None,resource_rules=None,equipment_rules=None)` 为已settled消费者提供公开纯读，允许与原终态相同或不同的当前租约，要求已有完全相同的原terminal指纹和canonical receipt；pending拒绝。它不验证新producer、不恢复pending、不重新结算。main的已settled分支用它，不调用Task私有函数或会重新协调旧奖励/后继的普通ack。

## 必要反馈与修正

`verify_task_battle_recovery.py` 六组实际通过：真实注册admission/独立producer SQL持久后换lease；原ordinary settle/空ack拒绝；错误角色/原admission/事件/engine/snapshot/恢复版本、training/wild/disabled拒绝；真实late SQLite consumer UPDATE触发器错误回滚120XP/SMoney400/Task terminal，producer仍pending；胜利原奖与defeat/escape无奖；后来合法XP5/银7再换lease，SQL authorizer禁止DML时返回当前125XP/407银，无state1/奖励/后继重放；新增public read在same/new lease均只读且拒pending。

r1 Spec发现P2：SQLite持久lease为TEXT，int epoch和同值str可匹配同一行；原Python不同类型比较误判为新租约。已在真实临时SQLite上新增alias负例实际跑红，再以 `str(original_epoch)==str(current_epoch)` canonical比较拒同租约后六组转绿。r1报告保留；r2独立增量Spec已确认闭合。原六组 `verify_task_battle_binding.py` 回归通过；它仍明确是任务契约fixture。

两验证脚本的Participant/BattleFinished及producer/consumer为明示Task契约fixture；没有用它们替代真正engine胜利或真实source CAS证明。准确shared消费者、实际专属engine/资源终态/进程级恢复与隔离、真实真人角色资格、冻结部署及GUI由main/root另验。最初验证器缺inventory_config和超过本地3角色上限属harness适配，均已改为真实准备参数和合法重试实例，未放宽生产规则。

方法：diagnosing-bugs将独立审查发现变成真实SQLite红例再改单一判断；codebase-design将生产者原件/current CAS留main，Task复用内部已验证writer并提供独立纯读Seam；code-review固定r1/r2两轴分别保留；writing-for-agents将caller责任、参数及完成标准共置。没有操作在线服、真人库、客户端或暂停的Battle目标。

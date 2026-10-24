# 两次梦醒：原对白与未解析意图 Interface

`task_prologue_return_dialogue.py`准备原20任务/43路线的对白和提交入口。它只读取**已经存在且active**的任务，不接取、不完成、不结算、不换图、不分配实例，也不开放通用任务链。本文保留原只读 Interface 的独立范围；后续已发布的正式政策及尚未准入共享的结算候选见 [TASK_DREAM_RETURN_INTEGRATION.md](TASK_DREAM_RETURN_INTEGRATION.md)。本 Module 和新文件存在均不等于玩法启用。

原始依据为[PROLOGUE_DREAM_RETURN_RESEARCH.md](PROLOGUE_DREAM_RETURN_RESEARCH.md)：第一族1501黄药师10085/placement2/2426,640、Start4、Jump3→1006 raw170,70；第二族10140/placement6/5464,1993、Start5、raw335,144。排除旧101007/101021。125/0与450/450原人物/宠XP只冻结和校验，当前不发放；原后继与355/500/200等差异继续由原表保留，不在对白中补奖。

## 调用顺序

1. 启动`load_return_dialogue_resources(resources,chapter_rules,story_rules,placements)`核原43路线依序经过两族、恰20节点、前驱AI8002/type59、原机制/奖励/唯一后继及真实NPC摆放，冻结源指纹。它注入当前已批准世界目录规则，不代写中央政策或决定未来再次入梦的实例策略。
2. 新租约恢复阶段可调用`resume_return_messages(db,aid,rid,epoch,resources,returns,already_projected=...)`，只恢复当前原章节路线已active任务为bean0。若没有本族任务返回空；双任务冲突拒绝。它不创建票据、激活任务、补前驱或播放旧对白。
3. 已加载私有地图Owner返回真实当前NPC证明后，在调用方当前租约事务调用`open_return_dialogue_transaction(...,task_id,proof,current,generation=...,map_generation=...,now_ms=...,deadline_ms=...)`。使用已完成真实创建章节、当前门派/形象、原前驱completed、已有任务active、精确已采用目录/完整Location/NPC实体。返回冻结ticket与原Accept3→Refresh3→SVisit任务菜单；显式刷新避免原客户端忽略重复Accept3。期限由调用方现有NPC政策注入，无默认梦醒时限或读完时间设计。
4. 原对白尾句`CCommit(task,真实entity_key,0)`解码后，先在SQL事务外向地图Owner重新核服务器保存的key，再调用`inspect_return_commit_transaction(...,ticket,command,fresh_proof,current,generation=...,map_generation=...,now_ms=...)`。当前位置、原章节/目录、任务revision、连接/地图世代、NPC及期限必须一致；End、zero key、错误任务/选项、旧租约拒绝。调用方按世界公开契约pin此地图代，并在可观察移动、其他菜单、战斗、换图、断线时撤销票据。地图/网络等待不放在SQL事务内。
5. 输出`RawDreamReturnIntent(ticket,original_jump,successor_id)`，固定`coordinate_space='original_reward_fields_unresolved'`及`settlement_authorized=False`。重复同ticket保留request_id。这是当前服务器范围内的原对白请求，既不是TaskEvidence，也不是世界预留/TransferCommit或奖励许可；不能凭该对象完成任务。后续正式政策由独立结算 Module 消费，不能回写或放宽本 raw 对象的权限标记。

本Module只适用于当前公开目录能验证的实际私有来源，不批准任何新的第二次入梦地址、自动迁移或跨目录兼容。未提交ticket仅由角色Owner暂存，重登重新访问NPC，不把旧ticket持久化为未来完成许可。数据库连接、事务提交、消息投递和票据取消仍由原Owner负责。

## 实际检查和范围

`verify_task_prologue_return_dialogue.py`五组通过：20原节点/43路线冻结；第二族实际MapOwner/NpcScene的10140菜单及ready刷新；原真实key包经既有decoder生成未解析意图；错误key/option/End/placement/revision/时间/连接与地图世代/租约拒绝；恢复已有active0。读取前后全库快照相同，没有任务、奖励、传送或凭据写入。

有效案例复用明确的late-story画卷fixture，再通过真实公共画卷提交/原360奖励/唯一100121 active0进入本模块；不是自然走完前面剧情。师父历史journal、剧情入册、NPC原坐标接近及32px Scene为显式fixture，未宣称v2、客户端自动行走或GUI验收。第一族仅核原资源及同时缺active/缺前驱的上下文拒绝；该负例首先命中缺active，并未单独证明战斗前驱围栏。有效战斗后案例与单独前驱负例仍未验；没有生成或执行任何战斗胜利。

方法：codebase-design把原路径、原NPC/章节/目录及原请求检查集中在只读Module，返回不可变结果；research沿上一批一手报告，保留raw单位和政策缺口；writing-for-agents按启动→恢复→菜单→提交→未解析结果列Interface。没有修改shared、中央配置或现服。此产物不解决当前真人嘉兴入梦部署问题；其专用恢复交单为[JIAXING_STORYTELLER_PENDING_FIX.md](JIAXING_STORYTELLER_PENDING_FIX.md)。

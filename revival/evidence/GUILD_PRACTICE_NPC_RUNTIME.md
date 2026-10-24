# 个人修炼：修炼丹、NPC Adapter与登录恢复

第十一批在第十批现金事务基础上实现七项修炼丹mode1、可信NPC Adapter、已知技能登录投影与旧预留自动恢复。新增代码仍不等于原游戏NPC已经可购买：实际NPC绑定/共享分发、已迁移人物资源source回调及原GUI没有验收。全量goal保持active。

## 可信NPC Interface与共享入口接线

`practice_npc`不注册NPC、不连接/提交数据库、不等待其他所有者、不持Session或发送。它接受由`NpcServices.plan`根据**本次**地图交互证明生成的NpcServiceCommand；service1023、handler=`guild_practice`是接入方须显式配置的服务。Npc模板/placement/entity_key及组织地图实例准入不能由此名称猜出。

组织空间授权是独立的上游接入条件：当前通用NPC证明与当前帮派成员关系同时有效，仍不能证明该完整地图地址属于此帮派。已有公开Interface没有组织→MapAddress绑定/代次，实际路由须由主集成补齐，不能按模板1394一律授权。真实接口、guild revision成员缺口和接线验收见[GUILD_NPC_ACCESS_HANDOFF.md](GUILD_NPC_ACCESS_HANDOFF.md)。

共享角色入口还须检查战斗/loading等角色状态；Location.active不单独证明未战斗。完整价格/上限返回及已迁移资源消费者未接前，不因Adapter存在就发布为完整可玩服务。

1. 服务点击：角色所有者在现有租约事务调用`open_panel(db,account,service_command,current_location,now,rules)`，得到七项当前SUpdateAssistSkill及SFactionPractice七类型map逻辑包。未知角色/帮派设置拒绝，不填全零。当前Location须来自权威地图/角色位置；Adapter验证角色、租约、地图地址、位置版本、active、服务、handler和deadline，不能用旧证明代替重新交互校验。
2. 个人请求c36cc：先由地图/NPC路径以包内Q重验当前NPC/距离/服务1023，再调用`prepare_purchase`，多传原body。仅七项mode0现金/mode1丹；返回冻结PreparedPractice，内含OrganizationCommand及原NPC scope/body。帮派ID从角色成员关系取，不使用包内NPC Q。
3. 退出角色持久化事务后，投递PreparedPractice.command到已有OrganizationRuntime.command：现金reserve_practice预留3资材，丹reserve_pill_practice仅保存授权/前态，0现金/0资材。角色所有者不得持自己的业务锁同步等帮派。
4. 返回角色所有者后重新取得地图/NPC证明和当前Location，调用`finish_purchase(db,account,prepared,fresh_service_command,current_location,now,rules,...)`。准备后位置/实例/租约/NPC scope变化或deadline到期均拒绝；失败由后续组织resolve命令处理预留。cash须注入currency_rules；pill须注入当前角色Inventory与可信precommit回调。返回冻结PracticeAction（凭据及当前逻辑包），提交后才交目标连接发送。
5. 成功/取消分别投递resolve_practice；登录恢复也是投递该命令，不直接写帮派状态。相同受理请求保留服务器ID，新的相同客户端包另分配ID；包本身没有幂等ID。当前Adapter接受1..96字符的服务器ID。

`precommit(db,inventory,current_snapshot,replayed=bool)`复用npc_transactions现有约定，须返回已编码的逻辑包元组。正式接入必须包含受消费影响的背包刷新，以及RESOURCE_SHARED_RUNTIME_INTEGRATION要求的当前资源/source处理；已付重试应只读当前并验证自身凭据，不能借重试再次修补source。这里只验证了显式legacy资产/资源夹具中的真实Inventory bag编码及晚失败回滚，**没有证明已迁移资源人物的正式消费者已接通**。不能把任意空callback当完成。

现金事务不改Inventory revision；丹消费会改该revision，不能忽略已迁移profile的来源围栏。丹领域事务本身不读钱包、也不要求已知资材；实际NPC回调如采用完整背包包仍需要已知现金，未知时须拒绝并回滚，或先完成独立原生物品变更协议。不得补0现金。

新角色/旧存档：七项baseline仍须显式已知初始化。现有new_restoration_role或缺字段不自动授权旧角色补零；真实新建与首次兑现的授权接线由共享集成窗口补，不能从登录/等级推定。本文不操作任何用户存档。

## 修炼丹与原格式

policy单一来源仍是recovery-baseline.json.organizations.individual_practice。36747为原修炼丹，61335为铭文经卷，不可互换；mode1每颗消耗一枚，360001..3增加20XP，360004..7增加30XP，0帮派资材/0现金。原依据是citemattr及gangskillrole.layout，已纳入可运行验证。

原包不携带物品key，角色Adapter按“绑定优先、slot、key”选当前携带堆，明确designed；通过Inventory.apply_settlement同事务扣除，保留其版本trigger与幂等账本。0数量删除堆，保留历史消耗key在role_practice_pill_consumption。角色XP/版本、资产child凭据、公共修炼凭据、历史key与最终原生预编码同事务；任何异常整体回滚。

现金和丹许可分别保存mode/gain/item/recipe。新代码对旧现金许可缺失新增字段使用既有mode0/+10/无item默认，未重写旧记录；发布仍需一致版本切换，不宣称旧进程能解析新丹记录。人物等级/声望/开放/7天共用门槛为inferred，规则范围已集中标记；现金单价和余数转级仍为设计。属性修炼mode3/4、铭文mode及生活技能不套这套recipe。

verify_role_practice_native扩为8组：原现金/丹按钮、NPC Q链、三i32更新、五raw mode；SFactionPractice c5654七节点原std::map编码（全关/部分开）；原14d6770实际分支证明value0关闭、非零开启；原36747/61335和丹20/30文本比对；原14d544b实际执行确认经验条查当前等级+1。此索引是原UI证据，服务器XP消费/余数公式仍分开标设计。

## 登录、故障恢复与所有权

SocialEndpoint join经`GuildRuntime.initial`在目标角色邮箱读当前practice_states并投递七项原更新，未知profile跳过且不初始化。目标连接继续独占RC4/MPPC。退出帮派不会因这条只读投影删除已知个人技能；完整退出失效/战斗资格规则仍另验。

同一入口通过`nudge_recovery(role,epoch)`启动独立恢复任务，不在角色邮箱里等待帮派。每role/epoch合并、角色恢复任务与帮派refresh任务分别以owner_limit有界；持久pending查询按role/status索引且有条数上限。恢复仅处理旧epoch或已到deadline的预留；当前epoch未到期不取消。此批接入登录，未增加离线定时清理服务，未处理完的状态继续持久。

公共角色凭据存在则确认；无公共凭据且无资产/钱包child则取消，现金预留退3资材、丹退0。只有child却缺公共凭据违反本地原子契约，返回practice_outcome_unknown并保留pending/hold供显式修复；不能再加XP或宣称未付款退款。单条异常记录日志后继续处理其余条目，不阻止登录。不推断跨库分片完成，仍为同SQLite兼容Adapter。

## 本批验证与边界

- verify_role_pill_practice：7组，含七类型20/30、0现金/资材、真实资产堆选择/删除与重试当前值、缺物品、最终编码失败整体回滚、未知钱包/资材、孤立child凭据拒绝及不误补偿。
- verify_practice_npc：5组，实际NpcServices.plan与真实围栏事务，面板/准备/现金/丹/背包包/幂等；伪NPC Q、其他技能或mode、服务/handler/租约/位置、准备后移动及过期拒绝。Npc10077/服务绑定和位置是明确隔离夹具，没有修改真实registry。
- verify_practice_login：5组，实际GameRuntime、ConnectionOwner认证/RC4/原MPPC；已知七项恢复、未知不填、旧已付/未付/孤立child恢复、当前epoch预留不取消。暂停真实pending存储worker，另一角色type100四字节心跳先完成；恢复容量满拒绝、同role/epoch合并均验证。
- 必要回归：现金12组、原生8组、帮派管理11组/四连接TCP7组、研究开关10组/启动3组、帮派投影5组、组织运行11组通过。最新记录见guild-practice-pill-batch.json。

Npc Adapter实际角色连接是tuple行，复现guild_projection.scope及guild_training.snapshot的字典下标TypeError后，改为这些Seam使用已选字段的整数下标，兼容tuple/SQLiteRow；没有更改全局row_factory或shared存储。代码编译与policy JSON另检。

方法：codebase-design用于角色/帮派/NPC之间的小Interface和冻结消息；tdd逐条红绿（未知丹操作、缺丹结算、旧孤立child误取消/现金补XP、缺登录投影/恢复、缺NPC Adapter及准备/结算）；writing-for-agents用于明确接入方、原证据与完成标准。补充故障/回归不冒称全部曾红，没有声称Standards/Spec双轴审查。

未打开游戏、部署、重启服务、改真人数据，未编辑game_runtime/runtime_storage/accounts/serve/gateway、NPC注册/资产Module。实际NPC消费路由与已迁移资源消费者、完整面板价格/上限等原返回、原客户端购买/重登/断网、属性/生活/铭文/战斗效果、维护建设生产/活动及其他社交继续未完成。

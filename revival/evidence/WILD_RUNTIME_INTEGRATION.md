# 普通暗雷：实际入口与发布验收

用户要求「那你接入啊」，在说明共享入口冻结后又明确选择「由本窗口完成接入」。本批依据codebase-design，以原MapOwner确认移动、RoleOwner受理/事务和独立BattleOwner作为真实Interface；diagnosing-bugs用verify_wild_runtime的原生连续加密入口形成反馈。临时测试不接现场端口、不操作人类角色。部署及GUI分别记录。

## 要求与已接代码

1. 接受原移动后才可能暗雷。MapOwner.move_for_encounter返回原MoveResult，ROLE_MOVE意图、静止、安全地图、换图、剧情、在战斗中、塔内明雷地图均不触发；默认5秒宽限、每64逻辑像素20%、战后10秒冷却。规则启动加载，角色各自持有WildEncounters。不是客户端自报战斗或奖励。
2. 受理必须有真实已知当前属性/HP/MP、钱包与有效lease，选择原自有参战宠。无属性/钱包者不套训练默认值，也不自动建旧档基线。旧已知资源仅原vitals与当前投影完全一致时接入；已有显式新resource profile走原唯一carrier。入场不自动迁移任何资源档，也不打开新角色资源政策。
3. ScheduledBattle复用独立有界BattleOwner调度，WildBattle替换为原怪模板/模型/名字/背景。原技能完整系统、队伍/多怪尚未恢复，当前普通单人单怪、普攻/防御/逃跑沿已有引擎，实际自有宠可参战。
4. 开场前固定奖励roll、接收宠、角色/库存版本并落盘。预演固定掉落在保存点内回滚，满包在开场前拒绝，不留下物品或库存版本。战斗期间既有world gate拦截库存/成长/NPC/移动变更；各角色独立推进，没有全服锁、队列或网络循环SQL。
5. 每次产生播放消息时先保存实际战斗copy。原终局先写durable outbox，再在同一角色事务应用实际血蓝、原参战宠资源与XP、钱包、人物XP/升级、掉落、资源source和凭据；编码最终绝对状态也在提交前验证。宠物写可提升库存版本，因此人物升级使用宠物结算后的新资产快照与同事务source。提交后才发战斗结束、当前XP/完整属性/余额/背包/宠物刷新，并更新在线人物等级缓存。
6. 结算失败保留原战斗和待投递消息，下次tick重试，不提前发胜利/奖励成功；已经提交的同终局只读当前状态，不再次发奖。断线的非胜利中断保留实际伤害，按draw零胜利奖处理；还原后的旧lease事件无权写入。
7. 登录由当前租约恢复旧outbox：已有原终局原样结算；没有终局则从最后持久战斗copy生成中断零奖。旧原始epoch/终局/随机计划不改，跨lease代收须精确匹配持久outbox的原epoch和终局SHA；不是放开旧回调。

## 来源与范围

普通怪身份、地区、背景来自原包。概率、单怪战斗数值、XP/银两和分组掉率仍沿wild配置标注的designed规则；不宣称原版平衡。普通雷峰塔明雷、护境安民及活动日历是独立模块，本批不把它们标成全部上线。

资源数值新增battle_terminal由主策划接手，政策显式combat_causes和consume-only的纯/存储Interface及两轴审查见reviews/role-resource-combat-20261023；该审查不代表整体wild路线已经审核。

## 验证与发布

verify_wild_runtime已通过10项真实临时Owner路径：连续原生加密移动/战斗/全部奖项/HP一次提交；重连当前值；另一角色连接；中断保留伤害零奖；非终局checkpoint失败后断线的准确中断及Battle邮箱释放；持续checkpoint故障下断线释放Battle/Map、新lease恢复最后持久copy零奖；持久终局失败重试；受控慢结算时另一角色心跳；显式迁移人物与原宠跨lease恢复；胜利人物自动升级保留战斗伤势并同步宠XP/三掉落。

测试只将宽限/概率/冷却与drop roll替换为显式确定性fixture，真实router、MapOwner、RoleOwner、BattleOwner、存储/协议不替换。生产维持5秒、20%、10秒。原怪开场/round script均交原客户端decoder。

当前现场已是NPC33072发布；其中夹带的是本批较早wild快照，不能当本批恢复/资源修正已上线。本批候选从准确的npc-20261023T102110Z不可变source出发，仅覆盖prepare_wild_release.py枚举文件及主策划已审资源四文件；不复制其他窗口后续任务/NPC草稿。具体候选与固定diff见wild-release-candidate.json。发布前在固定runner执行必要回归与SQLite副本迁移，再核对真实PID/文件manifest、at-stop一致备份；仅停止准确当前发布PID，原存档/日志位置保留，失败回启原不可变发布。未启动人类客户端或认证在线人物，GUI待人类验收。

本批最终修正已发布：准确版本与证据见本文末「实际发布」。历史候选描述保留作审计，不代表当前进程。

## 补充入口审查与修复

初始7文件纠正审查没有替代继承入口审查，故另固定entry-scope/entry-changes，补核game_runtime、runtime_storage、battle_owner、完整wild_battle/wild_runtime_storage。两轴均发现同一P2：非终局checkpoint失败后，pending播放重试吞掉close操作，遗留BattleOwner；进一步真实故障反馈发现持续失败会跳过Map leave，重登报Role already in map。原失败报告保留在reviews/wild-20261023T104109Z/ENTRY_*，不以先前0项掩盖。

按diagnosing-bugs，实际Peer回归先红于旧BattleOwner存活断言，再红于持续故障后的真实join；修复后10项绿。因两个独立静态审查已准确锁定分支且实际调用复现同一结果，不扩散到其他猜测或临时日志。RoleOwner先完成pending非终局持久化再执行close；退出finally无论持久化可用与否均释放Battle/Map，未持久部分由最后durable copy按既有恢复规则处理，不宣称故障期间未确认动作已保存。

新固定候选wild-20261023T105951Z仍基于NPC33072，沿原审资源和怪物参数，只增加局部close与对应回归；工作区师门/退出初始化不混入。最终发布须在统一窗口当前master-ready/exit发布后重基，保留它的明确修改，再对合成版运行暗雷/初始化/必要Owner回归和副本启动检查。重基使用已冻结overlay与精确旧函数替换，不复制后续工作区。

## 完整入场资源来源

主策划只读提醒原before_vitals五数不足以证明完整来源。实际原生无宠胜利持久终局后，在同临时事务用真实库存grant及synchronize_inventory_resource_source造成source-only变化，确认resource version/HP/MP/max均原样；旧_settle仍接受并发奖，回归先红于Accepted unrelated source-only change against old combat admission。故无需假定当前UI必可打破battle gate：可信结算Interface本身也必须核对原来源。

修复不改root资源Module或schema。入场在原before_vitals字段保存format2 envelope（原vitals及完整RoleResources，含policy/caps/source各revision）；终局严格与当前完整资源逐字段比较，再把同一已证明快照送consume-only计划。旧已结算行只读当前重放；旧未结算迁移资源行缺完整来源须显式核对，不后贴今日source；旧未迁移原vitals合同保持。现场先前只读统计wild_runtime_battles为0，发布仍备份和逐表保留，未批量改行。

该回归与原10项均已绿，共11项；真实无关来源变化被拒绝的事务完全回滚后，原终局仍能一次结算。真实宠物跨lease恢复、宠XP后source更新、人物自动升级及三组掉落继续通过。该新增拒绝条件将连同合成发布候选重新双轴核对。


## 实际发布

2026-10-23 19:13:49（北京），本窗口按用户直接授权完成发布。当前PID10076，原PID29268（master-ready-exit-20261023T110056Z）；准确运行wild-20261023T110855Z/run_release.py，基于该刚发布版本，保留师父/车夫ready和普通退出初始化5项修复，仅加入本批8文件改动。1425个固定输入hash及启动源码hash吻合，Standards/Spec各0项未解决，详reviews/wild-20261023T110855Z/REVIEW.md。

最终候选实际执行：verify_wild_runtime（11项）、verify_runtime、verify_role_lifecycle_runtime、verify_battle_runtime、verify_role_resource_combat、verify_task_tracker_runtime、verify_resource_npc_assets_runtime；另以隔离输出目录对最终source复跑最新verify_exit_initialization_runtime、verify_first_master_runtime，及只读真实DB一致备份的迁移副本检查，全通过。固定怪物/旧新版奖励独立领域检查沿用原相同文件绿结果，不伪称本次再跑。

停服时一致性备份：runtime/deployments/wild-20261023T110855Z/accounts-at-stop.sqlite3。真实DB quick_check=ok，启动前后107张既有表逐表行数/内容SHA一致；无删除人物、任务改写或自动资源迁移。原本野外待结算行为0；新服务未认证任何现场角色。实际loopback Challenge版本601、未认证心跳和准确listener PID通过。deployment-verification.json及evidence/latest-deployment-verification.json保存原始记录。

切换辅助脚本曾在旧进程已退出后Wait-Process返回1，随后无listener查询也因PowerShell非终止错误返回1；该失败未启动错误候选，已记录并修正仅旧进程准确停止及无listener正常分支，凭原发布记录恢复本次受控切换。完成备份后启动PID10076并通过全部发布检查，未恢复或覆盖存档。此为发布辅助问题，未伪称第一次命令成功。

当前实际范围为普通单人单怪暗雷和真实自有参战宠、普攻/防御/逃跑及既定奖励。生产5秒宽限、64逻辑像素一次20%检查、战后10秒冷却保持。雷峰塔明雷、护境安民和全部活动日历仍为其他待接入范围；完整原技能、组队多怪、商业容量和人类GUI没有据此验收。


发布记录补核：实际命令与唯一listener均10076后，将遗留gateway.pid从29268原子替换为10076，与deployment/latest发布报告一致。发布辅助已加入正常启动及失败回退PID记录维护；此补核没有停启进程、认证角色或改数据库。完整admission source-only风险的真实红绿及11项最终检查记录见前述完整入场资源来源，并非借其他窗口的退出UI验证代替暗雷验收。

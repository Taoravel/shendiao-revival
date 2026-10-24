# 战斗恢复：第一批实现与接线交接

日期：2026-10-23。目标：当前本地1.6.1端游、网络601。已读取根AGENTS.md、ARCHITECTURE.md、DESIGN_AUTHORITY.md及补全配置2026-10-23.1。这里区分领域实现、协议验证与真实客户端验收。

## 本批产物与来源

- `battle.py`：纯回合Module。Interface为submit(round, Command)、resolve、acknowledge(round)、cancel；命令、战斗员与事件是不可变数据。支持普攻、防御、速度与位置排序、施法消耗、治疗、逃跑、死亡跳过、回合上限及播放期间拒绝重复行动。
- `training_battle.py`：按battle_id持有状态的训练Adapter；返回逻辑消息，不调用socket、Session、SQLite或其他角色Module。配置启动时加载为冻结TrainingRules，创建战斗时不读盘。接收角色快照副本及login_epoch/snapshot_version；结束产生冻结BattleFinished，携带唯一settlement_id供角色所有者去重。训练不改角色属性、不发资产、不触发任务完成。
- `battle_protocol.py`：当前客户端原生消息编码及输入解析；8类消息经原x86构造和解码器实际执行。`research_battle.py`为离线Unicorn环境，不读写在线进程；只替代内存分配、CRT复制和STL字符串宿主操作，不替代协议解码。
- `battle-protocol-index.json`、`battle-disassembly.txt`记录当前映像哈希、RTTI/vtable、构造/序列化/解码/处理地址。
- `verify_battle.py`、`battle-verification.json`为最小行为和协议检查。

## 原客户端证据：client_verified

| 消息 | 类型 | 已核验布局 |
|---|---|---|
| SSendBattleStart | 0xc1b59 | 8个i32及2个byte，共34字节 |
| SSendAddFighters | 0xc1b5a | compact数量及FighterInfo；含UTF16名称、外观、类型、HP和嵌套容器 |
| SSendRoundStart | 0xc1b5b | 倒计时秒数、环境i32及int映射；空映射时9字节 |
| CSendAction | 0xc1b5c | Operation三个i32和两个byte，共14字节 |
| CSendRoundPlayEnd | 0xc1b5e | compact数量及i32列表，**不是u64角色ID列表** |
| SSendBattleEnd | 0xc1b5f | i32→i32映射，空时1字节 |
| SSendRoundScript | 0xc1b71 | NewResultItem列表、AIAction列表、两个int集合 |
| SSendRoundPlayEnd | 0xc1b76 | 一个i32 |

回合脚本顺序已经原生探针纠正：NewResultItem在前、AIAction在后。NewResultItem含DemoExecute的9个i32与buff列表、NewDemoResult列表、追加FighterInfo列表及两个int集合。NewDemoResult包含目标ID、buff、DemoAttr列表和int映射。非空脚本中的攻击者1、目标21、HP变化-16均从原生解码对象读回核对，名称同时验证短字符串和超出内联长度的UTF16字符串。

原生处理器的调试字段及跳表在0x1190080、0x1192260显示DemoAttr类型1为hpchange；DemoExecute顺序为attackerid、hpconsume、mpconsume、spconsume、operatetype、operationid、msgid、childskill、passiveskill。FighterInfo的maxHP/受伤上限/HP位于对象0x54/0x58/0x5c。

训练敌人资料来自`knight.gsp.npc.cmonsterconfig.json`行20001：小灰狗、modelID6013。临安战斗背景来自`knight.gsp.battle.cbattlebackground.json`行6；音乐来自`cbattlebackmusic`行1。

## 攻略与设计值

[端游官方战斗规则](https://sdxl.wanmei.com/info/qita/fight/20120729/133541.shtml)，URL日期2012-07-29，本次实际打开核对。历史端游资料支持每回合30秒、超时普攻、200回合上限、速度影响先后、全灭或全体逃跑结束。它没有给出攻击减防御或防御减半公式；不能证明所有规则与1.6.1逐项一致，也不提供协议枚举。手游资料未用于本批。

训练数值唯一读取`design/recovery-baseline.json`：人物缺省100HP/100MP、攻20防5速10；敌人60HP、攻12防4速8。普攻=max(1,攻−防)，防御向下减半后至少1；确定性排序、无随机/暴击/闪避均为designed。30秒/200回合为guide_supported，目标版本匹配未验证。已有属性快照可覆盖训练缺省值，但本批网关未接属性Module。通用Battle的调用方自选Skill数值只是执行能力，未配置原版门派招式，也未提供原技能按钮。

## 基础指令的后续原生核验（第二批修正）

- 第一批Operation顺序、防御/逃跑编号及回合倒计时均为错误推定，现已通过原客户端代码纠正，不再采用旧值。第二批`research_battle_commands.py`执行原人物分支0x11962bf→0x11962e7和原CSendAction序列化器，确定三字段顺序为**操作类型、目标、操作ID**，人物标志1、手动标志0。
- 防御按钮是characteroperatedlg.layout的skill2，注册到0x11bb230，实际压参操作号4；逃跑按钮skill7注册0x11bb470，其发命令分支0x11bb644压参9。原回调压参亦由仿真实际执行。普攻1/防御4/逃跑9及字段顺序现为client_verified，证据见battle-command-native.json和battle-command-disassembly.txt。
- SSendRoundStart首i32由0x1196013读取，乘1000后写计时器；是秒数，不是轮次。训练每轮发送30秒，客户端自己的轮次由原处理器递增。没有把离线代码执行称为真实GUI点击。
- 玩家位置1、敌方21、fighter_type人物1/怪物3、enemy_side=0仍为inferred。原解码接受字节不能证明站位、敌我、动画或自动战斗正常。
- 原回合结束回复没有轮次字段，因此Adapter只能按当前播放阶段拒绝重复回复；跨轮恶意重放还需连接所有者的序号与入站命令契约。
- 未设置死亡结果位、未知属性映射、技能动画及通用奖励字段。HP变成0后在播放确认时发结束消息，倒地表现待实测。
- 训练逃跑暂确定成功，断线直接清理训练；与官方普通战斗的掉线托管规则不同，仅限零奖励训练。

## 共享入口现状与集成窗口接线

在新ARCHITECTURE约束发布前，已局部接入gateway.py的start_training、tick、战斗消息分派和战斗期间移动/任务/资产请求拒绝；serve.py新增`--training-battle`实验参数，收到首次CAfterEnterWorld后开一场训练，训练期间1秒tick。默认不开启。没有重启现有服务；共享文件此后移交原始复原聊天统一迁移，不再并行重写。

**当前仍为同步实验接线**：TrainingBattle由Session直接持有并调用，不满足独立战斗分区调度；没有完成商业运行架构迁移或容量验收。没有新增全局锁、全服队列或线程池。

集成需要：

1. 在启动阶段调用load_training_rules，向战斗分区传冻结规则。角色所有者构造带role_id/login_epoch/属性版本的快照，只传不可变命令和快照；按battle_id建立有界邮箱及满载拒绝策略。不同战斗独立推进，不能共用一条阻塞业务队列。
2. 连接所有者解码输入后投递战斗命令；TrainingBattle.receive/tick返回的(type, bytes)由目标连接所有者按generation检查后编码加密发送。不要跨线程调用Session.send或writer。
3. 调度器发送定时tick；回合输入30秒超时自动普攻。第二批BattleOwner已提供由部署方明确配置的播放超时取消；没有硬编码正式服托管策略。训练取消不产生胜利或奖励事件。
4. 战斗结束取finished()，按settlement_id交角色所有者。训练task_event_eligible=false且奖励为0，**不能拿训练胜利完成真实任务**。正式PVE需敌人模板ID、任务实例ID、双方参与快照和持久outbox，并由角色事务同时写任务/资产/结算凭据。本批没有持久结算或“恰好一次”承诺。
5. 地图所有者在入战时冻结移动、移除/标记AOI；结束恢复归属和原坐标。世界/NPC/任务战斗触发接口待集成，不能将CStartbattle的u64字段猜作怪物ID使用。
6. 属性/宠物Module提供版本化属性、已学技能、参战宠物和效果消耗快照；战斗不直接写背包或宠物数据库。本批只有训练人物与单个怪物，尚无原宠物参战协议/技能表现接入。

## 本批方法、验证与未验证范围

- diagnosing-bugs：先确认缺失战斗分派，原生反馈循环用于查错；`verify_battle.py`非空回合脚本探针首次因容器顺序错误红灯、非空播放确认因宽度错误红灯，分别单点修正后全量消费并读回字段。整体是缺失子系统实现，未套用旧故障的3–5个根因假设。未宣称TDD。
- codebase-design：以submit/resolve/acknowledge作为纯领域Seam；编码和训练Adapter分开，不将数据库、资源扫描或连接对象放入回合结算。
- 8项行为检查通过：训练四回合胜利、播放屏障、防御/超时、非法输入不占回合、逃跑/取消、死亡跳过/同速、治疗与MP、回合封顶及网关世界夹具。
- 8类原生消息验证通过；既有verify_gateway.py（认证/加密压缩/创建/世界/位置保存）和verify_world_bootstrap.py通过。报告不证明战斗画面实测。
- 未验证：真实按钮/敌我/站位/动画/结束回图、原版门派招式、宠物/组队/PVP、实际任务战斗、正式奖励、重连恢复、并发故障隔离及容量。现有在线服务未重启，实验入口未对真实账号执行。

## 第二批：独立战斗所有者与原生指令修正

新增`battle_owner.py`，每个BattleOwner拥有一个训练实例和独立有界邮箱。此批没有修改共享gateway.py/serve.py/accounts.py。配置读取仍在启动阶段，战斗执行没有磁盘I/O、数据库、Session、writer或全服工作队列。

对集成窗口的Interface：

- 输入`Participant`为冻结快照，包含role_id、login_epoch、connection_generation、attribute_version及可选Fighter属性；不传账号/连接/背包Module对象。
- 启动时明确提供mailbox_capacity、receipt_capacity、playback_timeout_ms与单调now_ms；播放超时是宿主训练策略参数，本批测试用90秒/50毫秒仅作夹具，不是新的统一策划值。
- `initial()`返回一次开战Delivery。之后连接路由器将原生输入封成冻结BattleCommand，附battle_id、请求ID、连接内顺序、当前state_version/round_number、deadline_ms。submit仅做不可变身份/大小校验与有界入队，process_one由本battle_id唯一调度者执行，并重新校验过期、状态与序号。submit返回accepted不代表命令执行成功。
- 队列满返回backpressure；收据容量满拒绝新命令而不删除去重凭据。部署方应按最大回合及拒绝流量选择容量；不能设置成只能完成半场的容量。实例结束后由角色结算/地图归属确认后回收。
- 同一request_id与相同内容重试返回replayed收据，不重复动画、结束或奖励效果；同ID不同内容拒绝。收据截止时间可延长，内容不可改。原生包不带服务器轮次，因此版本/序号来自可信连接路由器，不能声称已经抵御客户端把旧字节伪装成新的合法命令。
- `advance(now_ms)`由调度器驱动30秒普攻和明确配置的播放超时取消。调度器应按入站/时钟的顺序处理本实例命令，避免把已接受输入排在超时之后。定时操作只由该实例调度者执行。
- `BattleOutcome`是冻结结果，含冻结快照、Delivery与可选BattleFinished/BattleAborted。Delivery目标有role_id/epoch/generation，由目标连接所有者校验后编码发送。不得把它变成对其他Session的直接调用。
- `terminal()`提供稳定结束消息供宿主持久outbox重试，close重复调用返回同一终态。胜利包含唯一settlement_id和属性版本；取消/播放超时只产出BattleAborted，不能触发任务或资产奖励。战斗本身没有完成持久化/原子发奖。

已验证的领域迁移路径：战斗所有者内的纯状态、入站有界邮箱、租约/版本/顺序/截止时间核验、重试去重、不可变逻辑投递、结束事件、宿主指定播放超时。此批后半段共享集成已接入game_runtime.ScheduledBattle，详见下节；老gateway.Session仅作兼容验证Adapter保留。

`verify_battle_owner.py`新增10项检查，并用现有runtime_core.SerialOwner做受控隔离验证：阻塞A场的异步处理，B场仍在限定时间内结算到播放阶段，随后释放A。它证明两个实例在该夹具中独立推进，不等于在线服务器或多进程容量验收。

另复现并修正残血进战上限错误：原TrainingBattle保留hp40/maxHP100，但fighter编码将三处都写成40。先增加实际“属性快照→进战包→原生解码”失败探针，再让maxHP/受伤上限/当前HP分别编码，原生读回100/100/40通过。原生完整行动出包探针也先在旧适配器报错，再修正字段顺序与4/9操作号；每轮倒计时修为30秒。

本批方法：沿用codebase-design，在连接与战斗状态之间放置Seam；沿用diagnosing-bugs，以原生探针红灯/字段读回验证实际错误，未宣称TDD。验证结果：原8项行为、8类消息解码及残血/3类原生按钮出包检查通过；新增10项所有者检查通过；verify_gateway.py现有加密认证/进图/移动持久化回归通过。未启动或重启真实服务，真实客户端表现、技能/宠物与正式任务奖励仍未验收。

## 第二批收尾：共享运行时已集成的验证

集成窗口新增game_runtime.ScheduledBattle，以每个battle_id的SerialOwner调度本Module；serve.py新源代码已使用GameRuntime，旧Session不在新监听入口的玩法路径。战斗窗口未并行修改这些共享文件，按用户AGENTS交付了接口与原生修正。

新增`verify_battle_runtime.py`在临时数据库中走实际ConnectionOwner→角色所有者→ScheduledBattle→BattleOwner路径：

1. 完整认证、预检和进图后捕获训练开场，真实持续RC4/MPPC输出由原生解压器读取；开场三种报文再交原消息解码器校验。客户端计时字段30秒。
2. 四轮输入使用原SendBattleCommand字段设置和原serializer生成的普攻包，不用本实现反算期望输入；每个实际下行回合脚本经原解码器验证。最后返回SSendBattleEnd，角色battle引用与runtime.battles登记均释放，连接心跳仍可往返。
3. 将宿主明确可配置的播放超时在夹具中缩为5ms；原生防御包进入播放后超时触发BattleAborted，返回结束消息并释放角色。原集成只传finished会遗漏aborted，已向集成窗口说明并由其修正；本检查通过，取消没有伪装成胜利。

`battle-runtime-verification.json`保存以上结果；`verify_runtime.py`亦通过，包括受控存储等待期间另一连接心跳、另一地图和另一战斗继续推进。没有启动新监听或重启在线服务。现有源代码路径的迁移与临时环境验证已完成，不等于当前运行进程已加载新版本，也不证明真实GUI表现或商业容量。

仍待接入：真实属性快照与资产版本（当前ScheduledBattle用位置版本作训练占位，不能用于正式发奖资格）、正式AOI入战/退战归属、宠物/技能、持久outbox、原子任务/奖励、断线托管恢复、真实客户端画面验收。站位、战斗员类型和自动标志非零的语义仍须进一步原生/实机核验。

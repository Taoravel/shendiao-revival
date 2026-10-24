# type22道具使用：真实实例与任务候选只读检查

2026-10-23。本批将原58条type22/41种道具的资料落为可调用的独立只读Module，未开放任务完成或扣物。原包/范围/时条证据见 [TASK_USE_ITEM_NATIVE_RESEARCH.md](TASK_USE_ITEM_NATIVE_RESEARCH.md)，本批动态范围/资格核对见 [TASK_ITEM_USE_ADMISSION_RESEARCH.md](TASK_ITEM_USE_ADMISSION_RESEARCH.md)。原字段完整目录见 [task-use-item-catalog.json](task-use-item-catalog.json)。

2026-10-24后续：三本type73教学书原factory→TaskRelative→右键handler→本地kind2→CUseItem已闭合，当前仅精确206104/50190、206204/50191、206304/50192从原生use未知改为无静态物品地图限制，同时明确增加server_learning_rule_unconfirmed。新源见 [QINGGONG_BOOK_USE_NATIVE_RESEARCH.md](QINGGONG_BOOK_USE_NATIVE_RESEARCH.md) 与 [原表/官方版本核对](QINGGONG_BOOK_SOURCE_AND_GUIDE.md)；旧研究N3/N4为历史未闭合状态。36843【师授】秘籍是另一类，不能套三书规则。

## 已实现与当前范围

`task_item_use_protocol.py`沿既有库存原CUseItem0xc03ff解码16字节：BE i32实例key、i32目标种类、u64目标ID。任务物品的已确认普通角色路径要求kind0/当前本人，保留完整64位角色ID，没有taskID、扣量、坐标或计时字段。另提供原空体SUseTaskItemFail0xc4a53逻辑消息构造，不能向空体填入猜测任务/错误码。本Module不接管库存的CUseItem路由，也不处理药品或指定宠物使用。

`task_item_use.py`启动加载不可变TaskItemUseResources：复用真实InventoryConfig.items，并加载/接受已加载CTaskRelative；58条定义按41模板预索引，原任务和物品矩形分别保存，readtime与ProcessBarTime保留原整数。每条原任务+ItemAttr+TaskRelative形成来源指纹。请求路径无配置I/O、DDL或全任务表扫描。

原58条分为51条常规type25静态准用范围、4条50204春联动态范围、3条原生发送已核的type73教学秘籍。普通type25中usemap>0按原四边×16半开区间观察，usemap0只表示静态表不限制，不代表任务自动成功。50204保留动态范围未实现；50081/50029虽也有原动态分支，但不在本58条UseItemID中。50205原itemtype150，亦不在本58条，不能借这些分支把它归入常规type25。

## 调用顺序和完成条件

1. 库存/角色所有者按原CUseItem路由并识别实际实例所属玩法，原请求经 `decode_task_item_use(body)`得到冻结TaskItemUseRequest。角色目标须来自完整原字段；原taskID并不存在于此包。
2. 角色所有者按实体顺序确认当前连接generation、请求身份/期限、当前不在战斗、经世界所有者验证的active Location。构造冻结TaskItemUseCommand；Location包含真实地图实例/分区、角色租约和位置版本，禁止从客户端输入直接当作权威位置。
3. 在当前调用方角色事务中调用：

```python
inspection = inspect_task_item_use_transaction(
    db, account_id, role_id, login_epoch, registry, inventory, command,
    generation=current_generation, now_ms=trusted_now)
```

它只用真实公开 `Inventory.immutable_snapshot_transaction(db,epoch=...)`和 `load_task_state`，校验账号/角色/有效租约及背包中的当前实例、数量、绑定、格子/装备状态、原needLevel/outbattleuse。没有影子背包或独立连接。纯 Interface为 `inspect_task_item_use(registry,actor,tasks,assets,command,...)`，两者返回同一冻结检查结果。
4. 结果附带当前资产版本、任务版本、位置与原始任务候选。没有active目标时为no_active_objective；唯一候选时unique_active_candidate只确定候选身份；多个active任务同用模板时ambiguous_active_objectives且unique_candidate_id=None，全部候选保留。即使只有一个任务提示矩形匹配，也不会以此代替未确认的服务器选任务规则。
5. 每个候选分别报告物品准用范围、原任务地图是否匹配、原任务提示矩形、两个原时条值、附加机制及尚缺政策。所有返回值固定completion_authorized=False。它不是TaskEvidence、消费许可、计时收据或任务完成计划；没有角色状态写入、发奖、扣物、创建战斗、显示动画、offer或发送消息。

只读检查没有持久回执。同一request_id稍后重新检查可以观察到新的真实状态；将来任何正式结算仍须在其调用方事务重新检查当前版本/实例/任务与已批准消费政策，不能拿旧inspection执行扣物。世界碰撞、移动能力、活动资格、前置和周期实例仍由所属规则提供；矩形观察不赋予轻功或传送。

## 确认保留的完成缺口

所有候选都保留server_completion_rule_unconfirmed和consumption_rule_unconfirmed；readtime>0另列server_timing_rule_unconfirmed，轮次另列cyclic_task_instance_unimplemented。原AI/动画/传送/任务计时等非零字段单独列出，未由“实例合法”抹平。

原TaskRelative矩形是客户端允许发送使用意图的范围；ActiveInfo任务小矩形已确认用于本地提示，服务端完成比较规则仍未知。本批特意验证50057在(1300,800)可处于物品准用范围而不在102109任务提示区；不得将两者合并成统一完成条件。原50057三件/四使用节点及50065重新发物事实也不确定每次扣量/扣时。缺发物来源的50011/50409/50411仍要求真实已有实例，不自动补给。

三书原客户端usemap0/readtime15与原CUseItem已核；服务端学习授权、扣物和计时仍未知。春联动态活动实例、9条AI战斗时序、7条动画和2条传送仍需各自规则。本批没有给TaskDomain/TaskChain新增type22完成能力，当前正式完成开放数仍为0，不能将58条检查索引报告成58条可完成任务。

## 必要检查、方法与未验证范围

`verify_task_item_use.py`通过，报告 [task-item-use-inspection-check.json](task-item-use-inspection-check.json)：

- 原16字节布局保留0x1122334455667788角色ID；截断/错误目标布局拒绝，原失败消息保持空body。
- 41个原模板逐个通过真实Inventory测试发物/读取，对58个原任务逐项检查；使用显式夹具cleanup保持真实背包容量，没有扩大生产容量。第一次将41种同时塞入默认背包时正确报Bag full，调整的是测试发物顺序。
- 实际102109任务记录、50057实例与世界Location下，检查前后完整数据库dump一致，物品数量/绑定保持；50057准用与102109提示不同，右边界2320不命中；两个active同物品任务即使提示只有一个命中仍保持歧义。
- 精确三书原生请求实际进入同事务真实Inventory/current journal检查，全库dump与完整资产快照不变，保留学习/消费/计时/完成未授权；动态50204与轮次/附加机制保留缺口；错误本人目标/key、已装备/非本人物品、战斗/loading、旧generation/期限/旧lease拒绝。没有为只读新增进行奖励回归或重跑root自然链。

research后台核对原范围/资格/动态特例及消费规则窄检索；codebase-design将原生请求、启动只读索引和当前角色事务检查放在明确Seam，输入实际库存/任务快照，避免把观察结果变成完成授权；writing-for-agents将调用顺序、结果含义和后续正式结算条件共置。产物为两个独立模块、必要检查、原生研究及本接线说明。

未验证：正式服务端消费/完成/计时政策、原任务自然发物与全部接取来源、type73完整右键GUI/自然读条和学习授予、实际读条、正式战斗/动画/传送、周期重置、共享路由端到端及GUI。全程临时库/隔离原指令，没有操作在线服、当前客户端、真人角色或修改库存/世界/shared所属实现。


本批收尾反馈：verify_task_item_use.py七组通过，16项关键源码/目录输入前后哈希稳定。原factory/dispatch/kind2完成分段执行；真实流逝定时器和完整右键前置GUI未执行，完成kind2为明确fixture。TaskRelative15仅原float阈值，不采用server15秒。当前loader拒绝三书原身份/类型/准用参数改变或缺教学节点，不把其余73/2198默认加入。decoder复用现有16字节CUseItem，未增加猜测协议。

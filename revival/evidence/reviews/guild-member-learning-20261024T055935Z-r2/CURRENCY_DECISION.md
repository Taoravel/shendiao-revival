# 货币账本与任务奖励接线裁定

2026-10-23，主策划；适用本地1.6.1/network601的显式恢复钱包。原包与端游资料见CURRENCY_RESEARCH.md，数值与支付策略的单一来源为design/currency-v1.json。

## 证据与补全

客户端当前任务MoneyReward全为0，SMoney有明确原金额，零保持为零。任务210002的SMoney5000保留原值；可接任务展示不另发一次。PetExpReward、ShengWang继续使用各自渠道。

字段到钱包的完整原版语义尚未证明。主策划按用户补全授权设计MoneyReward→cash、SMoney→bound_silver；此映射标designed，金额来源仍按原任务记录。四种币分账，绑定银仅开放NPC_SHOP_BOUND_PAYMENT_DECISION的独立普通购买用途，交易用途继续拒绝；现金仅按配置中的明确用途扣除。没有自动混合支付或兑换。此账本不执行现实充值。

原生显示桥后续已闭合现金/绑银两路，详见CURRENCY_UI_BRIDGE_RESEARCH.md：ui.pfs背包money/Xianjin对应面板+3c，10ef250读取wallet+b0；reserve/绑银/Chubeijin对应+44，10ef340读取wallet+c8。currency_protocol.encode_currency_balance据此提供cash→SRefreshMoney.kind1、bound_silver→SRefSmoney。kind2写+b8不能冒充绑银。此证据证明显示路由，任务字段→业务币种映射仍为designed。重试凭据保存历史结果，刷新角色缓存/界面时重新读取当前余额；运行显示仍须客户端验收。

## 接入步骤与完成条件

1. 集成窗口启动时加载不可变CurrencyRules并运行prepare_wallet_storage。运行中由角色所有者经有界I/O调用，传入已BEGIN的当前登录租约事务；模块不另开连接或提交。
2. 新恢复角色可在明确创建流程初始化零基线；已有角色只做显式迁移，保留已知余额。无钱包时抛WalletNotInitialized，调用方继续保留未结算货币，不为消除pending静默建钱包。初始化重试不得重置现有余额。
3. 任务窗口用task_currency_channels分离原字段，可信任务实例生成稳定结算键、purpose与source_ref（含任务ID/原字段）。apply_currency和经验、物品、任务状态及总凭据共用外层事务，任一失败全部回滚。重试不得再次授予；原pending只经明确迁移一次，已发凭据不得改币重放。
4. 社交窗口的家族/帮会费用仅引用cash的可信扣款凭据；申请批准/组织建立即使幂等也不能自行增加或消费另一角色钱包。跨角色交易交给独立交易状态机，本模块没有实现转账。
5. 提交后的任务刷新和加载/重连当前钱包，对已证实cash/绑银返回encode_currency_balance逻辑消息，经目标连接所有者顺序发送；无钱包不发虚构零余额。元宝两字段后续也追通：encode_yuanbao_balances只接受完整当前元宝、绑定元宝二项，各为0..2147483647（原UI的保守兼容域，不是已知原服上限）。消息同时覆盖两项，未知另一项不能填零；超过兼容域明确拒绝，不截断账本。各接线方分别提供临时数据库事务证据及原生显示证据；仅本文件与模块存在不计入运行服已接线。当前手动测试现场不部署或重启。

## 方法、产物与验证

codebase-design：将租约校验、余额上下限、用途限制、稳定键意图冲突与重试回执集中在currency Module；Interface接收事务和启动规则，现有任务/组织调用方无需分别实现钱包。角色所有权沿用ARCHITECTURE，不引入全服锁或货币执行队列。writing-for-agents：按启动、初始化、奖励、费用、完成标准给集成方明确触发条件。

产物：currency.py、currency-v1.json、verify_currency.py、本裁定及DESIGN_AUTHORITY指针。一次必要检查在临时AccountStore执行公开Interface，通过任务5000绑定银与现金隔离、同键重试一次、冲突拒绝、绑定银交易拒绝、现金100−30、外层失败同时回滚余额/角色/凭据、初始化重试不重置和旧epoch拒绝。结果currency-verification.json。未接触在线库或客户端，也未宣称完整TDD流程。

原生codec必要检查：verify_currency_native.py离线执行本包x86原序列化器0xe4e9a0、0xe40e70，与encode_balance逐字节相同，包含4294967303、1099511627899与9223372036854775807余额，防止32位截断；新增0xe5bb70核对元宝123456/绑定元宝2147483647字段顺序与8字节body。未知槽、负数、bool、浮点和溢出拒绝。证据currency-native-verification.json，原映像SHA-256一致。序列化布局与UI槽位分别由原codec和原包/原生getter链证明，未验证真实屏幕。

运行时接线进展：集成方已在启动注入货币/成长/属性规则，标记明确新建角色来源，角色加载/首次世界完成时读取当前钱包并返回现金/绑银逻辑消息。主策划verify_currency_runtime.py通过Owner→连接连续RC4/原生MPPC解码、旧档未知不发零、新档零基线、显式大额基线重连及重建运行时回读；临时库/内存Writer，未监听现场端口。任务窗口已接同事务货币渠道及提交后的当前余额逻辑消息，主策划verify_task_currency.py独立通过，未证明该非零奖励任务自然触发/完成。

未验证：组织实际扣款/恢复、原pending显式迁移、非零货币任务自然流程及原生余额GUI、元宝运行时成对刷新、现金流通全规则、跨角色交易、商业数据库及容量。本批源码未部署到手动现场。SQLite只是本地Adapter，文件单写限制仍在。

## NPC仓库存取款追加裁定

2026-10-23，主策划审阅NPC窗口交付后认可currency-v1的追加用途`npc_depot_transfer`，沿用既有政策版本及旧凭据；新增用途不重写既有余额、币种或结算意图。完整原生证据见[NPC_DEPOT_MONEY_NATIVE.md](NPC_DEPOT_MONEY_NATIVE.md)：CDepositMoney/CDrawMoney均为NPC实例key与金额两个BE64；钱包携带现金与仓库分别使用已证实的独立槽位，不与绑定银混用。

端游窄查使用“仓库/存入/取出/银两/现金”。[2012年官方商会说明](https://sdxl.wanmei.com/info/newplayer/50to69/20120705/132374.shtml)提到部分税款返还进入玩家仓库，支持仓库可持有金钱；该页没有给NPC普通存取的手续费或1.6.1余额上限。其商店投资税属于另一业务，不移植到角色仓库。故同角色cash钱包↔显式仓库cash、等额无费、无自动兑换的业务配方仍标`designed`，不是原服费用事实。跨角色交易继续使用独立交易所有者。

每次正金额必须在同一个当前角色租约事务内校验双方已知余额、修改钱包和仓库、登记账本/仓库审计及共用命令凭据。两边各限非负signed64，先验证金额、余额不足与目的余额溢出；任何晚期异常整体回滚。旧角色任何一边未知即拒绝，不填0、不消耗请求键。新角色仓库0只可由既有明确新建来源授权。相同已受理命令读取当前双方余额重发，冲突意图拒绝；原线包没有请求ID，角色所有者为每次新受理操作分配内部身份，不能按同金额永久去重。

codebase-design把同角色转移保留在既有调用方事务Seam，currency集中用途/余额/账本校验，NPC Module持有仓库授权和审计；没有新增全服执行队列。writing-for-agents将来源、配方及完成条件集中于本段。主策划独立运行`verify_npc_depot_money_native.py`通过原64位codec和两个钱包消费者的相互隔离；`verify_npc_depot_money.py`首次在全局启动准备阶段被帮会冻结配置校验错误拦截，所属窗口修复后独立复跑通过：4294967303存入/4294967301取出、总额守恒、未知基线/不足/溢出拒绝、晚期凭据失败整体回滚、同键只一次和旧租约拒绝。`verify_npc_depot_money_runtime.py`先准确报真实Owner存款无回复并保存红基线；共享NPC仓库分支接入MONEY_TYPES并校验当前ticket的实例key后，root原样独立复跑转绿：连续加密连接双64位余额、不开仓/错NPC拒绝、内部同键一次、重连访问失效及当前余额保持。源码路由已验，未部署/GUI。

root另新增并实际运行`verify_npc_depot_money_guards.py`通过访问权限增量：只替换game_runtime时钟依赖越过真实ticket截止，过期存款撤销ticket且之后取款仍拒绝，双方余额、钱包账本、NPC命令和仓库审计全部不变；重新开仓恢复合法访问；两个相同的新线包各转一次，区别于同内部受理键重试；零/负/截断/尾字节/错误NPC均无写；实际原MOVE/STOP撤销仓库访问。未替换event-loop时钟，没有实际战斗或跨图；loading/battle门禁的哨兵验证范围见主集成NPC_DEPOT_MONEY_SHARED_INTEGRATION。当前8724固定发布、真实数据库与GUI均未改变。

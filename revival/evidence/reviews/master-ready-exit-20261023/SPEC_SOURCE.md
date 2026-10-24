# 陆无双“你现在还没有完成此任务”修复交接

2026-10-23，本任务窗口。优先级：先打通当前角色的序章入口，暂停无关任务类别扩张。修复状态为工作区源码已实现、隔离检查通过；尚未部署、尚未真实客户端验收，不代表序章全部完成。

## 人类反馈与确定的源码缺陷

最新截图中角色4位于古墓派109,46，陆无双显示原文“你现在还没有完成此任务。”，任务追踪仍是拜见陆无双。该提示对应客户端 message141714 和任务UI分类2。早先102,51处的无对白与通用ValueError日志不足以证明实体key或距离错误；本批没有给NPC添加configID别名或扩大交互半径。

`open_master_dialogue`及`open_cart_dialogue_transaction`原先只发送SAcceptScenarioQuest(state3)，随后发SVisitNpc。任务在自然intro/装备完成后已经以state0下发。原SAccept处理`0x125d5c0`查找已有bean；`0x125d5d4 jne 0x125d5e5`直接返回，重复接取不覆盖state。因此“发出了state3的接取bean”不能证明客户端已有任务进入ready。原UI分类`0x1257b20`对普通type10已有state0返回2，对state3返回3；前者正走截图的进行中提示，后者才读Start对白。

补充原生证据、key调查及最新截图判定见[FIRST_MASTER_NATIVE_NPC_KEY_AUDIT.md](FIRST_MASTER_NATIVE_NPC_KEY_AUDIT.md)及[TASK_PROTOCOL.md](TASK_PROTOCOL.md)。该缺陷足以解释现象，但没有声称已取得此角色全部真实线包。

## 实现与集成

- `task_master_card.py`：合法师父凭据建立后，发送完整接取bean（保留客户端尚缺bean时的初始化），再发送同任务SRefreshScenarioQuestState(state3)，最后发送原任务NPC菜单。
- `task_cart_dialogue.py`：相同次序修正车夫。所有任务ID、选择卡、奖励和传送政策保持原来源；不提前完成任务或发武器。
- 公开Interface及共享调用签名不变，无需改`serve.py/gateway.py/accounts.py/game_runtime.py/runtime_storage.py`，无需迁移或修改角色存档。
- **当前运行的不可变版本`npc-20261023T102110Z`早于本修复，不会自动读取工作区新源码。** 由统一集成窗口按项目发布流程把这两个Module纳入下一版，不能仅要求玩家反复点击旧版本。
- 曾报告的`supports_npc_progress`临时导入断裂已经消除；本批实际导入`task_conversation/task_domain/task_chains`通过。NPC进度条暂时仅保留研究，不对外宣称实现。

## 方法、反馈与范围

采用diagnosing-bugs：以人类最新截图收窄到已有任务状态，执行原客户端接受处理分支；旧检查只解码服务器发出的bean，未消费客户端已有状态，导致假绿。修改前在真实临时事务的师父开菜单处加入“已有任务必须在菜单前收到ready刷新”的回归检查，实际失败`Existing first-master bean remains active: duplicate acceptance cannot enable Start dialogue`；修复后通过。

采用codebase-design：保持地图所有者先发可信NPC凭据，任务Module只改变逻辑消息序列，不改共享入口、地图权威或数据库所有权。保留CCommit确认→CQuestDialogEnd授权卡→CGetCardItem领取的既有流程。

已完成的必要检查：`verify_task_master_card.py`（原43路线、两种选择、10个车夫与事务原子性）；`verify_first_master_runtime.py`（临时数据库、实际Owner和连续原生协议，intro→师父→选武器→真实装备→车夫任务）。均通过。检查期间不连接在线服，不操作人类客户端，不改在线存档。

新增原生反馈`research_task_existing_quest.py`执行未修改的客户端接受/状态刷新处理与UI分类函数，仅适配外部查表和界面通知。实际旧序列`Accept3→Visit`在已有bean0时得到state0/UI2并触发回归失败；修正序列`Accept3→Refresh3→Visit`得到state3/UI3。现有师父/车夫临时事务检查已直接将实际Module输出喂给该反馈，代表师父及全部10个车夫通过，结果保存在`task-master-card-check.json/native_existing_quest_checks`。这比只查看发送包里的state3多验证了客户端的真实消费行为，仍不是GUI实测。

未验证：新版本部署后的真实客户端师父Start对白/卡片显示、用户角色的实际状态与序章后续全部玩法。后续100106及正式战斗不能据此记为完成。


# 原生退出确认入口初始化

2026-10-23，root裁定。人类反馈为“点右上角X完全没有反应，也没有确认窗口”，不是已点确认后缺ACK。先读原生来源ROLE_EXIT_NATIVE_REAUDIT与role-exit-native-reaudit-check.json；单一Adapter政策为design/role-exit-ui-v1.json。原客户端/服务器既有生命周期回归绿不能反驳该现场反馈。

## 已执行的原状态反馈

verify_role_exit_native在原x86解释器实际执行应用reset、消息ctor/marshal/unmarshal/Process及原安装WndProc。显式worldstate2/非battle夹具，reset后退出mode=-1，同原WM_CLOSE被消费且没有确认窗端点调用；解码并处理SFirstDayExitGame后，同WndProc按有符号字段选择普通或首日窗。root独立复跑全部五例通过，终端UI创建函数只记录调用并返回，无实际GUI、客户端启动、OS窗口调用或战斗。

确证原消息type0xc0039，4字节BE signed32；字段<0设本地mode0，>=0设mode1。wire -1/INT32_MIN到普通ExitGameDialog，wire0/1/INT32_MAX到首日窗。应用reset明确设-1，原系统菜单退出也有该本地门禁。缺消息是与现象吻合且可复现的源码前提；尚未采样人类实际客户端全局变量，不能单靠此报告宣布其现场根因已经唯一确定。

纠正初次速报：SRoleOffline的[0x2244c30]是DefWindowProcW，不是PostMessageW，已通过原PE Import Descriptor/OFT→FT和实际指针别名确认。不能继续用异步投递/等待普通WndProc递归解释它。退出确认按钮发送原空CRoleOffline及服务器ACK布局本批未发现wrong-wire；本次修复针对确认窗出现之前的初始化。

## 设计值及共享接线

原首日退出业务及其非负字段含义尚未恢复。当前恢复服默认普通退出，明确采用signed32=-1（ffffffff），标designed；协议类型、signed分支与窗选择为client_verified。**发送0会开启首日窗，不能把0当普通退出默认。** 不借此启用首日任务、奖励或改变玩家存档。

由共享集成窗口在启动加载冻结政策/逻辑消息，加入每次合法角色入场回复，含重连及退回选角后再次进入。应用reset可能重新禁用入口，不能只在进程首次登录发送。经过当前ConnectionOwner按原RC4/MPPC顺序投递，放在允许世界交互前；不在热路径读配置、DDL或访问GUI。该消息本身不修改角色属性/资源/任务/费用，已有退出保存/lease清理/ACK合同继续使用。

## 完成条件

先让当前实际入场回复驱动原reset→解码/Process→WndProc观察，旧source缺包应红，新source应恰含一条准确c0039/-1且显示普通确认窗端点；重连/再入场重复验证，不能只检查源码字符串或未执行消息的body。保留原退出/返选角/返登录/旧lease与位置保存必要回归，全部只用临时库/内存连接/离线原指令。

固定候选、适用用户授权及发布交接由主集成保存，独立核对不可变发布是否包含这项修复。助手不打开游戏或执行GUI/战斗；部署完成与真实画面仍分开记录，不要求用户为定位这条前提反复重开。人类后续确认窗/退出结果才是GUI验收，当前尚无这项证据。

方法：research以原资源/原PE进口和实际WndProc为一手来源，纠正初报错误；diagnosing-bugs用人类具体无窗反馈收窄到本地前置状态，构造真实原指令红→绿而非只重跑服务器ACK；codebase-design保留连接投递与角色状态所有权；writing-for-agents将普通模式设计、已证原事实、实现和现场验收分别记录。

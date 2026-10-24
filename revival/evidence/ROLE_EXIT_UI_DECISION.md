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

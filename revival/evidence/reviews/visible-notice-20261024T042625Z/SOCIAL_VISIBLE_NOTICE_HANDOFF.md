# 当前连接的可见拒绝原因：P0纯消息交单

读取条件：main接正常NPC100107首战、缺profile或已有pending battle等拒绝路径，需要把原因送回当前玩家时。纯Interface已经验证；本页不修改拒绝业务、不写DB、不启动游戏/服务。当前冻结/审查指针查visible-notice-current-review.json；指针产生前可查visible-notice-pending-review.json及实际原验证文件。

`from visible_notice import visible_notice`；调用`message=visible_notice('已有战斗正在准备或进行，请稍后再试。')`，取`message.kind`、`message.body`作为一条逻辑消息交当前连接Owner。DTO冻结，kind固定已核social_protocol.CHAT_RECEIVE=0xc1772。只投当前有效connection/role epoch，沿既有连接发送/加密顺序；不经世界/当前频道广播，也不以此重新执行原操作。纯函数没有连接、目标角色、钱包、任务、Battle或发送器。

本地designed selection：复用已有chat_message，sender=0、name='系统通知'、level=0、channel=CURRENT_CHANNEL=2，正文为1..256个可打印Unicode字符。文本由服务器明确选择，例如“当前角色资料尚未准备好，暂时无法进行该操作。”；不传原异常/堆栈，不填真人ID/姓名。无效文本编码前ValueError，调用者在已确定拒绝的路径选择固定正常文案。

原证据（1.6.1/network601映像SHA256 2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791）：

- 原SSendChatMsg vtable0x22849bc，构造0xf142c0写0xc1772；原marshal0xf143c0与纯函数body逐字节一致。
- 原unmarshal0xf74b60完整消费实际body，保留sender0、系统通知、level0、channel2及中文正文；probe只适配宿主CRT分配/UTF16赋值，不替换OctetsStream读取。
- 由该原unmarshal得到的同一对象执行完整原Process0x15b8a40。chat manager全局0x294455c非空时传给原ChatManager入口0x15b7f40，实参为(channel2,senderLow0,senderHigh0,level0,name指针,text指针)。sender0跳过原0x1277d60玩家黑名单查询，没有伪造一个玩家身份。
- 测试只在ChatManager入口用无副作用Adapter返回，完整Process正常返回。未执行后续聊天管理器渲染、真实UI或系统弹窗；当前频道可受客户端显示筛选影响。主集成在游戏内另验实际可见位置；需要强制弹窗时另核真正系统通知协议，不能改一个猜测type。

未提供SGetSysMsg封装。已查到SSendMsgNotify的独立RTTI/Process，但其完整配置消息语义尚未核验，不作为本交单输出。此处明确是带系统标识的本地聊天回显，不能称原系统频道或原系统弹窗。

验证脚本verify_visible_notice_native.py：原marshal、完整unmarshal→Process→ChatManager入口、source0黑名单隔离、冻结DTO与输入边界4组通过，结果visible-notice-native-verification.json。精确Module/依赖/映像/报告哈希及双轴审查结果见固定目录。适用方法codebase-design（纯DTO与发送所有权）、tdd（缺Module先红后实现）、code-review（独立两轴）、writing-for-agents（调用条件、可验证字段和GUI边界共置）。未改shared、资产、服务、批量消息或运行服。

# 社交协议恢复记录（2026-10-23）

对象：本地原版1.6.1端游、网络版本601。原生映像SHA256及16个序列化布局探针结果见 `social-native-verification.json`，可重跑 `verify_social_native.py`。执行原x86序列化函数；仅分配、释放、内存复制与安全cookie由宿主适配，不替换协议编码。

|消息|编号|原生序列化地址|布局|
|---|---|---|---|
|SFriendsInfoInit|0xc4e21|0xedcb90|vector<FriendInfo>, i32|
|SFriendIsOnline|0xc4e22|0xe48580|u64 roleid, i32 state|
|CSendMessageToRole|0xc4e23|0xed8270|u64 target, UTF16 text, UTF16 extra, i32 mode, vector附件|
|SSendMessageToRole|0xc4e24|0xee6790|身份、3文本、2byte、2int、文本、byte、3int、byte、2vector|
|CBreakOffRelation|0xc4e25|0xe46930|u64 target, UTF16 name|
|SBreakOffRelation|0xc4e26|0xe48030|u64 target|
|CSearchFriend|0xc4e28|0xe477f0|u64 target|
|SSearchFriend|0xc4e27|0xee5160|角色资料，未知资料字段保留默认|
|CSearchRole|0xc4e3e|0xe47830|UTF16 name, u64 target, i32 mode|
|SSearchRole|0xc4e3f|0xee56d0|角色资料，未知资料字段保留默认|
|CAddFriend|0xc4e32|0xe467d0|u64 target, UTF16 name|
|SAddFriend|0xc4e31|0xe47bb0|身份、分组/等级/在线等资料，未知字段默认|
|CSendChatMsg|0xc1771|0xf127b0|i32 channel, UTF16 text, UTF16 extra, vector附件|
|SSendChatMsg|0xc1772|0xf143c0|u64 sender, UTF16 name, i32 level, i32 channel, UTF16 text, 2vector|

字符串按UTF16LE字节串加原生compact长度；所有标量使用网络大端。FriendInfo单独在0xedc7b0原生序列化比对，非空好友初始化整体也已执行原生vector计数与FriendInfo序列化器，比对42字节结果通过。尚未执行非空初始化的原生解码器。

频道不能直接使用按钮后缀。0x15988d7起循环把按钮1～8映射到0x22be000表 `[1,2,10,4,3,5,11,13]`；布局 `chatinputdialog.layout` 的按钮2=当前、5=门派、6=世界，因此协议编号分别为2、3、5。当前实现只允许这三类；队伍、家族、帮派等没有成员目录时拒绝，避免向其他玩家外泄。

生产接入：`Session(..., social=hub, deliver=writer.write)` 在原世界加载确认 `CAfterEnterWorld` 后注册在线角色并回复好友初始化。`Session.close()`移除在线角色并推送离线通知。`SocialHub`管理单进程在线目录、持久化联系人及收件人路由。推送与直接回包共同使用各收件人Session的持续RC4/MPPC状态；写入顺序由同一事件循环保持。社交只处理SOCIAL_TYPES中的编号，不截获移动、背包或任务消息。

根因：原Session缺少全部社交处理分支；原TCP循环只有请求触发的直接回复，没有跨连接主动投递入口。修正已以加密Session双账号测试验证，不以单纯字节编码成功作为功能完成证据。聊天正文不写入gateway事件日志。

# 首次拜见师父：对白与武器选择卡的原生协议

2026-10-23。沿用research的一手来源追溯和diagnosing-bugs的单变量原生反事实。来源为当前1.6.1原映像`native-image.bin`（SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`）、原配置`knight.gsp.task.cmainmissioninfo`和`knight.gsp.task.ccardeffect`。未修改他人任务模块、共享入口、角色或在线状态；未打开客户端/GUI、未启动服务。

## 可接线的结论

少林角色9任务103286为MissionType10、ActiveInfoNpcID13291、地图1110、ScenarioInfoAnimationID20044、后继103288；古墓角色9任务100186同为type10、NPC10014、地图1100、AnimationID20006。20044/20006均存在于原CCardEffect表，指定师父头像、两个按钮、武器表现和两个物品。二者item1/num1=49009/1、item2/num2=49006/1，其余item3/4为0。**这是武器选择卡，不能把20044/20006当成11001那类CG电影，也不能把这两个type10任务当type50处理。**

恢复选择卡的明确下行是 **SPlayCardEffect `0xc001c`，body=BE signed i32 effectID>0**。两个原按钮发 **CGetCardItem `0xc041f`，body=BE i32 effectID + BE i32 itemID**。没有questID、NPCkey、数量或CG结束字段；服务器必须用已保存的可信演出/选择ticket把请求关联到这一次合法任务，不因客户端填入某个物品ID直接发放。

独立协议模块 [world_card_protocol.py](../world_card_protocol.py) 提供`play_card_effect(effect_id)`与`decode_get_card_item(body)`；后者仅解析原标量，不做业务授权。编码示例20044为`00004e4c`；选择49009请求为`00004e4c0000bf71`，选择49006为`00004e4c0000bf6e`。

## 原生调用和字段依据

`ScenarioInfoAnimationID`原解析器`0xbb6751..0xbb678a`把值写到任务配置+0x2ac。SPlayCardEffect RTTI对应vt`0x22704e0`，constructor`0xd54b80`写type0xc001c，marshal`0xe40e40`、decode`0xd54c10`只读/写一个BE i32，原decoder要求值>0。

SPlayCardEffect Process `0x1744540`经getter`0x89eb50`查原CCardEffect表；表getter指向config root+0x1010，其类RTTI为`CCardEffectTable@task@gsp@knight`。不存在的表项id=-1不显示；id<40000走`0x17444a0`取得UI，再`0x1744070(effectID)`填充卡面；>=40000是另一卡UI路径，本批不外推玩法。20044和20006两个原Process fixture均落入武器卡UI。

填充函数`0x1744070`保存effectID至UI+0x40（`0x17443d0..da`）；配置+0x90和+0x98分别写到UI+0x44/+0x48（`0x17443dd..f6`）。两个按钮callback `0x1743990`、`0x1743a10`在原栈上构造vt`0x2276640`、type0xc041f，取UI+0x40为首字段，次字段分别取UI+0x44或+0x48，发送后调用`0x1743740`关闭卡UI。原CGetCardItem constructor`0xd919d0`、marshal`0xe4c480`、decoder`0xd91a70`确认两份定长BE i32；decoder本身没有验证这对值是否属于角色/任务/可选项。

## SAccept、NPC访问、完成对白与结束报告的边界

沿用已证实普通任务路径：SAcceptScenarioQuest建立本地bean；SRefreshScenarioQuestState state3使type10归入可交付分类；SVisitNpc第二vector放任务ID，菜单点击本地对白。普通type10对白提交`0x1643360`构造CCommitScenarioQuest。不能因为任务含AnimationID就绕过NPC距离、已接状态和对白提交票据。

原task后置表现函数`0x1255e70`读取任务+0x2ac。对于本批两个ID且配置+0xc8=0，原指令会调用`0x12550c0`→Scene `0x11ca790`的普通effect边界，**没有调用SPlayCardEffect武器卡UI，也没有构造SStartPlayCG**。普通effect函数使用`CQuestEffect`资源表，不能仅凭同一个数字就说选择卡自动出现。两个原fixture明确记录此边界；本批没有执行该边界内的实际资源加载/GPU显示。

原对白结束片段`0x1644c1a..0x1644cf8`在UI阶段+0x60=3时读取任务配置；+0x2ac>0进入`0x1644cb6`，调用上述本地表现函数后，原栈构造并发送 **CQuestDialogEnd `0xc4a52` + BE i32 questID**。以103286/20044和100186/20006两组fixture执行，捕获到该报告，未发送CEndPlayCG。阶段3是fixture前提，本批未声称已执行整个UI状态切换。

后续Start整链复核纠正：上述phase3是合成fixture前提，不能外推到43首师父。原Start第三句读尽仍为phase2，经164b530→1643360仅发CCommit，1644b50清理时直接跳过phase3 End分支。当前接线以合法当前Start提交建立卡ticket，再发SPlayCardEffect；CGetCardItem匹配角色、源任务、effectID和原合法item/数量，在调用方事务完成一次选择。原服务器精确发卡时刻仍未知，该时序为显式设计；旧“等End才发卡”方案已撤销。复核脚本research_first_master_dialogue_end.py、实际Owner回归verify_master_commit_card_runtime.py及FIRST_MASTER_CARD_COMMIT_FIX提供证据。

## 验证和未验证范围

[verify_world_card_native.py](../verify_world_card_native.py)运行16项通过，结果 [world-card-native.json](world-card-native.json)，指令 [world-card-native-disassembly.txt](world-card-native-disassembly.txt)：6项原codec encode/decode、2项原Process分支、4项真实按钮发送、2项原后置表现调用、2项原对白结束报告片段。仿真保留原比较、参数读取、消息构造和调用指令；系统堆/字符串基础适配复用独立离线Replay，配置lookup、网络发送和UI/资源边界用host adapter捕获参数。不是Python重写按钮协议后自证，也不是完整客户端UI实测。

尚未验证：真实NPC点击到对白全状态机、原服发卡精确时序、卡面GPU显示/动画、选中物品入包表现与装备流程、断线重入和重复选择事务。没有用未知动画字段放宽现有supports_plain_dialogue，也没有增加无授权发奖路径。集成应按任务/选择会话所有权接入，而非扩大全服锁或在共享入口内直接结算。

## 43条路线的原卡与物品身份清单

新增只读数据产物 [newbie-master-cards.json](../catalogs/newbie-master-cards.json)，重建入口 [research_world_master_cards.py](../research_world_master_cards.py)。它重新从原`artres/config.pfs`读取5份BXML并CRC校验，结合已验证`newbie-routes.json`检查角色约束、type10、任务AnimationID与卡ID一致；不把先前人工字段重写成新来源。43条路线对应43份不同卡、86个选择、10个不同物品，所有选择各有CItemAttr、CEquipEffect和CItemType关联，issues为空。产物SHA256=`c45158c080fafac38e98803ffd73f6d1879e476466de4e6ccce7cb6ed527c338`，验证记录 [newbie-master-cards-verification.json](newbie-master-cards-verification.json)。

每条route保留character/school/map/master task/NPC/card ID、完整原card attributes、两项原始item/num字符串与解析整数、原button及weapon表现字符串。`items`字典另保留物品基础属性、装备属性、类型/武器资源前缀；`sources`列出原PFS条目、extracted/decoded/catalog路径、原条目SHA256、CRC和大小。任务后继保留原PostMissionList，不在此生成奖励或完成策略。

| 原物品ID | CItemAttr原名 | itemtypeid→CItemType | 原weapon前缀 | 关联 |
|---|---|---|---|---|
| 49006 | 师承的铁环 | 1544→环圈 | shuanghuan_ | CEquipEffect同ID存在 |
| 49009 | 师承的油纸伞 | 2312→伞 | san_ | CEquipEffect同ID存在 |

两者原CItemAttr均写needLevel=1、maxNum=1、使用方法为右键穿戴装备、effectdes为1级见师父主线奖励武器；由物品类型、装备表同ID及原说明共同确认它们是**直接武器物品**，不是待转换礼包。其它8种为师承重剑、白纸扇、木枪、柴刀、铁剑、竹弓、绣刃、双铁剑，原字段完整保留。卡表weapon1表现字符串与CItemType.weapon是不同字段，例如卡20044的weapon1原值sidai，而item49009装备类型前缀是san_；这里保留两份来源，不擅自统一别名。

本批只确认原数据身份与一致性，没有创建装备实例、推定实例属性/绑定/耐久初值、写包裹或自动装备，也没有将卡请求本身当作发奖授权。

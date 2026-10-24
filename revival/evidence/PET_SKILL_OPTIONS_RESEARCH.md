# 秘籍认证保护选项与技能到期显示

2026-10-23，1.6.1原客户端离线字段证据。认证保护/扣除/拓格进度当前规则见PET_SKILL_LEARNING_DECISION.md；旧decode_skill_book仍只解默认分支，生产完整Adapter使用decode_skill_book_request。到期存档、有效快照与空格复用已实现并离线验证，接线见PET_SKILL_EXPIRY_DECISION.md；共享接入与GUI仍待完成。

## C07ff六项身份

原CPetSkillDlg选项发送`142d6f5..142d784`在网络投递前构造六个BE32，经原ctor`dbc7a0`、marshal`e53610`、decoder`dbc880`验证：

| 顺序 | 身份 | 空选项 |
|---|---|---|
| 1 | 宠物实例key | 不适用 |
| 2 | 秘籍实例key | 不适用 |
| 3 | 初级认证符实例key | -1 |
| 4 | 高级认证符实例key | -1 |
| 5 | 第一个受保护技能ID | -1 |
| 6 | 第二个受保护技能ID | -1 |

原模板门禁`142edab`要求31254（0x7a16），`142eeeb`要求31255（0x7a17）。原citemattr分别名“初级认证符”“高级认证符”；描述明确初级保护一个技能并增加拓格几率，失败额外加1点必成进度；高级配合初级保护另一个技能，失败额外加3点。描述没有给出精确概率、必成进度消费顺序或每种失败的扣除条件。

受保护技能是精确原ID：原图标函数`12d8120`将ID经`4d3a90`保存在widget+590，选择处理`142d48d..142d4ba`通过`4d3aa0`读取并写入选项widget ID，发送端读取该widget+26c。选项中12是UI空选择哨兵，发送时转-1；不能把12或所选技能ID解释成数组下标。

四个原发送/codec算例已验证：无选项、仅初级、初高配合、仅高级形状。最后一个仅证明发送格式能构造，**不证明服务器会接受高级单独使用**。服务端接入时仍需验证认证符归属/携带/类型/数量、配对、受保护ID在当前已学列表且不同、普通书与认证符不能同一实例；根据固定随机及版本化规则排除受保护项后原子扣除/更新/回执。

结构化产物：`pet-skill-protection-request-native.json`。

## Pet+c4到期map语义纠正

原Pet+c4是skillID→64位绝对到期值映射（内部Pet+4c），不是仅凭结构就能确认的“保护map”。非空原Pet marshal/decoder保留compact数量、BE32 ID、BE64值；原刷新`11353c9..1135429`实际执行已学列表与map复制。再运行原图标循环`140dfb2..140e0ed`，经原树查找与64位比较：当前时钟≤到期值时显示该技能并传入原到期值；严格过期时显示原200534“技能空”，参数到期0；没有map项的另一技能正常显示且无到期参数。

原cpetskillconfig中200534描述为“造型特效消失了，留下了个空空的技能格，可以学习一个其他的宠物技能。”因此过期占位与保护认证必须分别建模。学习覆盖、默认技能生成及战斗快照今后还需明确处理已过期技能，不能仅替换图标就声称状态已正确结算。

初批14组原codec/原map复制/原UI比较见`pet-skill-expiry-native.json`。后续已由原SGameTime codec/process、2945088/294508c赋值、原signed64除1000及匹配CRT的_localtime64_s调用确认Unix毫秒，九组边界见`pet-skill-clock-expiry-native.json`。两次同步包之间客户端时钟自增仍未证明。

## 方法与后续完成条件

下一步已有定位：原CPetOpenGridProgress构造dbcab0，type c0800，空请求；SPetOpenGridProgress构造f21090、marshal f213f0、decoder f21450，type c0801，compact数量后每项BE32宠物实例key+BE16进度原位。空请求和5个非空回复值已执行原codec，见pet-skill-progress-native.json。原UI的142f0aa使用movsx word，意味着原位≥32768会显示负数；后续服务端范围必须考虑有符号16位，而不能因网络占2字节就允许65535。

后续已执行原消费者：142f870合入窗口map，142f061..142f0b6按当前pet key查询；142f0ba..142f106按内部Pet+48已学数量取89d870表record+4并计算进度条。d4234e安装CPetSkillSuccessConfig vtable225718c于root+658，关联已确认。18组原codec/合并/查询/阈值/算术见pet-skill-progress-consumer.json；终端表查找提供原提取行、GUI只观察，原服服务器算法仍不能由UI推定。

`diagnosing-bugs`按单变量差分，先执行原发送及codec，再以非空map和确定时钟检查真实消费者；原UI终端调用仅观察参数。`codebase-design`将后续认证学习/进度账本放在角色事务，时间由可信所有者提供，完整快照供战斗独立读取；`writing-for-agents`分开字段事实、实现步骤与未验证范围。

认证学习当前裁定见PET_SKILL_LEARNING_DECISION.md；到期领域及可信时间Interface见PET_SKILL_EXPIRY_DECISION.md。下一步继续共享Owner接线、GUI及battle有效技能接入；当前无实机或原服整套算法还原声明。

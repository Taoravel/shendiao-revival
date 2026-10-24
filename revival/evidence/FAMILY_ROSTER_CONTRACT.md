# 原生家族成员名单

编码或接原生名单时读本文。FamilyMemberWire已绑定等级、声望显示数字对、职位与离线文字，刻意保留+2c未绑定元数据，所有调用者必须显式提供；未知旧声望和离线状态不填虚构值。

第六批运行名单已接，见FAMILY_MANAGEMENT_RUNTIME.md。新成员有来源标记及持久generation/声望/离线状态，已有未知state不补零。原格式现29项，原任命/审批函数9组；本页下方25/7为之前范围，原GUI仍未验收。

## 已核对格式

FamilyMemberData vtable 0x22733a4、marshal 0xe45d20：role_id Q(+8)、name字符串(+10)、元数据i32(+2c)、声望数字对(+30/+34)、等级i32(+38)、position i32(+3c)、离线文字(+40)。SUpdateMemberData 0xc55fa在+8嵌入同bean，marshal 0xd74260。

原名单渲染0x14c7b00：缓存+30经0x18be2e0的原等级格式器入列1，缓存+28/+2c经数字格式与原“/”入列2，缓存+38入列3。由bean到缓存的复制链分别对应+38、+30/+34、+40。家族布局列头为等级/家族声望/上次离线时间；离线文字与原空串比较，空串以绿色及cstringres1698“在线”显示，非空原样显示。两个声望数字的可消费/累计语义仍待追通，不因显示顺序擅自启用扣声望。

SAddFamilyMember 0xc55f9、marshal 0xe8c120为计数及成员序列。原对象内部是std::list；verify_faction_native构造真实链表头、两个节点和各自bean vtable，直接执行原始序列化。空/一/二成员结果均逐字节匹配，包含非空中文、不同数字及64位角色ID。

SRemoveFamilyMember 0xc55fc与SExpelFamilyMember 0xc564d均为Q角色ID；SLeaveFamily 0xc5602与SLeaveFaction 0xc560c为空体。撤权通知的语义还须结合原生管理流程接线，不以发现ID当作已完成GUI。

## 职位与当前族长

SAddFamilyMember.process 0x149ba80将bean+3c复制到客户端缓存成员+34，缓存复制函数0x1486960保留此字段。SUpdateMemberData.process 0x149b9b0走同缓存布局；它未设置缓存+24，对应的bean+2c仍需后续调查。

原查找函数0x1496ec0选缓存+34==2；0x1496f20选==1。名单渲染0x14c7bc9分别插入原图标字符串Zuzhang与Fuzuzhang。对应member=0、deputy=1、leader=2；0x14c72a0起的管理按钮启用分支也按1/2与2区分管理和族长权限。

verify_faction_native额外直接执行这两个原查找函数，验证重排成员后的族长/副族长选择、缺族长返回null和空名单返回null，共4例。图标原字符串也直接从同一映像核对。这里只证明客户端职位消费者，不声称审批同意/拒绝枚举、当前族长转让按钮与完整界面已跑通。

完整格式校验共25项，结果见faction-native-verification.json；反汇编片段见family-roster-disasm.txt、family-management-disasm.txt。verify_faction_ui另执行7组原任命/退位/巡察使分支，见ORGANIZATION_FUNDS.md，家族职位与帮派职位不得混用。FamilyData创始人与当前族长的区别仍以FAMILY_VIEW_CONTRACT.md为准。完整成员持久状态与原名单发送仍待运行接线和真实客户端验收。

# 背包元魂珠四字段数据与详情

本批为纯数据及原生详情 Adapter，未开放穿戴/摘除/融合动作。原来源与可复现代码见 `PET_SOUL_ITEM_SOURCE_RESEARCH.md`；实现/验证和审查清单见 `pet-soul-item-data-batch.json`。全量恢复目标仍在进行。

## 正确数据来源

背包 type145 原类为 CYuanHunZhuObject，其 PetSoulPerlItemTipsOctets 仅16字节：四个BE32，依次是累计经验、魂技ID、穿戴bean的raw5、穿戴bean的raw4。`OrbTips` 四项均显式提供，前两项非负signed32，后两项原有符号signed32保留。`encode_tips/decode_tips` 仅处理这个精确内部结构；六字段或截断/多余字节不能拿来当背包珠实例。

穿戴后的 `SoulBean` 仍为六字段，和之前已封签的元魂来源/完整map存档不同。`display_tips_from_worn` 只作原显示投影，交叉放置raw5/raw4，并把raw6!=0转为显示标志0/1。完整原raw6不会被修改，函数故意没有逆转换：显示结果相同的raw6=1、2、负数，不能从四项或显示标志还原其原整数。`bag_marker` 是明确提供的原基础旗标uint32的bit0，**与穿戴raw6非零判断不同**，不得把这两个结果当作完整基础旗标或资产绑定授权。

这也纠正此前“背包元魂六字段待恢复”的措辞：六字段属于宠物已穿map；背包珠必须独立恢复四字段实例及完整来源。原28珠均maxNum1；当前 Module 不创建或合并任何物品。raw4/raw5名字、raw6完整业务域及原服逆转换仍未知，后续资产策略须保留已知历史原值并明确设计新实例取值。

## 详情 Interface

`carried_tip_reply(positive_item_key, current_orb_tips)` 编码原column1的0xc03fe SItemTips：两个BE32 column/key，加16字节内部Octets。调用方必须先经真实角色租约事务取得当前完整已知的背包实例来源，验证模板与container，在提交前编码，并在提交成功后由连接所有者投递。编码器本身不校验数据库所有权，不授权仓库、人物装备列、扣费或玩法。

## 验证与方法

TDD 在既有纯数据/原生编解码 Seam 实际经历缺少 Module、缺少完整详情 Interface 两个红灯，再实现。`verify_pet_soul_item_data` 对原四项构造d98f90、marshal e4dc30、fresh decoder d994a0逐字节核对，另对完整SItemTips d9c110/e4e5c0/e0a240核对column/key/Octets。

`research_pet_soul_item_data.native_marker` 执行原CYuanHunZhuObject构造10743c0、非空parser107a020和原六→四对象转换1402f90。0/1/2/160/161/-1/-2/-2147483648共16个parser/转换组合独立核对字段布局和显示位，原bean精确raw6仍保持。宿主只隔离已独立认证的等级函数为固定2，以及原31277的soulType2配置查表；本批不重新证明等级公式。原构造、16字节decoder、字段赋值和自然返回真实执行，没有GUI观察者。

codebase-design 用独立 OrbTips 保持背包四项和宠物六项的 Interface 差别，显示投影不提供有损逆写入口。research 后台直接跟随原PFS、RTTI、工厂及原码执行，纠正近名类和字段数误用；writing-for-agents 将数据、显示、所有权与投递条件同接口并置。code-review 在固定文件清单下按Standards/Spec独立复核；没有Git/tracker，不制造提交或issue。

未验证：四字段物品实例持久化及完整旗标/品质来源、历史raw6的无损资产往返、实际选择宠物/空槽/战斗锁与技能权限、穿戴/38045摘除/融合材料费用和幂等、宠物最终战斗属性、全部共享消费者/加密投递/发布/GUI/容量。原工厂和确认入口只证明客户端路径，不替代服务器准入。此前22个生产文件以及共享入口、真实数据库和当前服务本批均保持不变。

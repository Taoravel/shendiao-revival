# 普通宠物血脉的原字段与等级证据

2026-10-23，端游1.6.1/网络版本601。原指令与原配置已核对；血脉元数据/有效资质与真实潜能预算见PET_BLOOD_BASELINE_DECISION，后续精华消耗事务及原生Adapter见PET_BLOOD_ITEMS_INTEGRATION。奖励及完整进阶、共享部署与实机仍未完成。血脉、颜色及进化是不同状态；已有PetCare.grade表示颜色。

## 已执行原消费者

research_pet_blood.py和pet-blood-native.json包含113组原Pet marshal/decoder→原刷新字段赋值→完整11297d0等级查找→原潜能显示算术。刷新113532c..1135373将Pet bean+30/+34/+38分别赋给1140血脉当前值、1150上限、1160悟性；颜色bean+3c仍是独立pet+2c。旧“根骨”名称已由还童UI真实Wuxing绑定与1160 getter纠正，独立原证据和持久化见PET_TRAITS_INTEGRATION。存在字段不证明上限或悟性原分布/领悟概率。

原89e290 getter返回root+b68，安装位置d43510明确为CPetBloodConfig vtable225c648。完整11297d0使用原内存28d0b1c的颜色上限3/5/7/9/12/15，按原表lowpower..uppower闭区间查0..15记录，超过颜色最大记录范围时返回该上限记录。普通潜能显示1435a01..1435a0b明确level×10。仅原提取配置行查询和属性map存储作终端Adapter，原分支/区间/颜色上限/算术实际执行；没有替代等级算法或实机画面。

原cpetbloodconfig共16行：0级0..63、1级64..229、2级230..565、3级566..1139，最终15级52611。ratio对应0、0.002、0.005、0.009…0.15。后查原bookanswerconfig150确认五项资质当前值和最大值按强化比例提升；服务端具体取整/资源顺序仍不能仅由字段证明，现基础取整设计见BASELINE_DECISION。原cpetxuemaiconfig同时有普通maxstarnum及蜕变tuibianmaxstarnum两套上限，原1129830另走cpetchangebloodconfig，普通证据不扩展成蜕变实现。

## 道具、版本冲突与后续Interface

原36117“血脉精华”itemtype1510，描述确认增加200能量，needLevel1，outbattleuse2；原宠物物品页发送通用CUseItem时target kind1和指定pet key，而不是仅凭CUpgradePetXueMai类名就判定该包用于精华。该独立c07e7实际含三个BE32和一个BE64，业务身份尚未证实，当前不接猜测含义的服务器入口。

[2012官方端游血脉资料](https://sdxl.wanmei.com/info/qita/pet/20120729/133553.shtml)支持精华增加能量、血脉提升资质及每级额外潜能。后查本包bookanswer36027也保留45级和“不得参战”，与具体item36117.needLevel1、任务“无等级限制”和参战宠物使用文本冲突；这属于客户端内部证据冲突，不能只解释成攻略跨版本差异。当前政策选择具体物品1级门禁另标designed，所属精华消费Adapter已实现，共享路由仍须按交单接入。取得/兑换精华、放生奖励和颜色进阶授权分别恢复。

新宠0/未知旧宠导入、原阈值/颜色上限状态、基础与有效资质、真实潜能预算及成长/加点/用药的当前投影，现已补基线，见PET_BLOOD_BASELINE_DECISION。后续真实36117消耗、稳定请求凭据、资源/血脉/物品同事务和原生Adapter已通过验证，见PET_BLOOD_ITEMS_INTEGRATION；共享CUseItem接线、奖励渠道及实际战斗/GUI仍待完成。当前有可用状态和预算仍不等于血脉整套玩法完成。

codebase-design保留基准Profile并采用单一有效投影，避免加成反复写回基准导致每次读档叠乘；原生probe按diagnosing-bugs的单变量字段/边界反馈执行，首个probe缺初始化EDX导致1140缺失，补实际slice前置寄存器后同循环113例绿。随后基础状态/真实预算已按tdd补齐；按根当前共享优先级先完成药品和INVENTORY_RESOURCE_HOOK_INTEGRATION，再继续血脉精华事务。无服务/GUI/实际战斗，原生成功不当作完整玩法验收。

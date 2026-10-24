# 新手领武器与穿戴任务：原始来源和装备条件

2026-10-23。本批采用 research 逐条追溯原包，diagnosing-bugs 用离线原指令及反事实验证装备部位，codebase-design 将只读配置、物品实例和任务推进的 Interface 分开。未开启客户端、GUI或服务；未改共享入口、任务或背包代码。

**43条师父任务的奖励武器已经找到：MissionType10 的 ScenarioInfoAnimationID 对应 CCardEffect，两个按钮各指定一件 49001..49010 师承武器、数量1。任务表本身没有 RewardItem 字段，并不等于整个原包没有奖励来源。10条后继 MissionType59 明确要求装备师父赠送武器，但原服的精确完成 predicate 仍未找到。**

## 真实来源链

机器表 [newbie-equipment-sources.json](../catalogs/newbie-equipment-sources.json) 保留43条角色/门派路线、53条完整任务原值、43张奖励卡、31件对照物品的 CItemAttr/CEquipEffect 及原解码行号。`reward_template_and_count_resolved=true`；`reward_policy_resolved=false`只指下发时机、绑定解释和原服完成 predicate 未确证，不再代表武器身份未知。

以云夕为例：

- 古墓100186：原 [CMainMissionInfo:391](../decoded/config/autoconfig/knight.gsp.task.cmainmissioninfo.xml:391) 为 type10，NPC10014，AnimationID20006，后继100188；少林103286：[源行16480](../decoded/config/autoconfig/knight.gsp.task.cmainmissioninfo.xml:16480) 对应 NPC13291、20044、后继103288。
- 卡20006/20044：[CCardEffect:8](../decoded/config/autoconfig/knight.gsp.task.ccardeffect.xml:8)、[行46](../decoded/config/autoconfig/knight.gsp.task.ccardeffect.xml:46)，分别给按钮1“获得伞”→49009×1、按钮2“获得环圈”→49006×1，其余item3/4为0。这是二选一，不能同时发两件。
- [49009:5807](../decoded/config/autoconfig/knight.gsp.item.citemattr.xml:5807) 是“师承的油纸伞”，itemtypeid2312；[49006:5804](../decoded/config/autoconfig/knight.gsp.item.citemattr.xml:5804) 是“师承的铁环”，itemtypeid1544。原说明都是“1级见师父主线任务奖励的武器”，needLevel1、maxNum1、右键穿戴；CEquipEffect同ID存在。物品直接是装备，不是待打开礼包。

实体研究方的 [newbie-master-cards.json](../catalogs/newbie-master-cards.json) 为奖励卡资料唯一主表；本表独立重读同一原包后，逐条比较43个card ID及86个物品/数量。卡原生发送/选择协议与时序限制见 [WORLD_MASTER_CARD_PROTOCOL.md](WORLD_MASTER_CARD_PROTOCOL.md)：SPlayCardEffect 0xc001c、CGetCardItem 0xc041f，不能用CEndPlayCG代替选择确认。配置中的200xx不是缺失movie文件，不能只在movie目录找奖励。

## 师承武器与适用角色

以下是 CEquipEffect.roleNeed 原列表；所有物品的装备部位均为0。

|物品ID|原名|itemtypeid|角色ID|
|---|---|---|---|
|49001|师承的重剑|264|1、3|
|49002|师承的白纸扇|520|2、4|
|49003|师承的木枪|776|3、5|
|49004|师承的柴刀|1032|4、1|
|49005|师承的铁剑|1288|5、2|
|49006|师承的铁环|1544|6、9|
|49007|师承的竹弓|1800|7、8|
|49008|师承的绣刃|2056|8、6|
|49009|师承的油纸伞|2312|9、10|
|49010|师承的双铁剑|2568|10、7|

原 [CItemAttr:5799](../decoded/config/autoconfig/knight.gsp.item.citemattr.xml:5799) 开始连续10行，装备规则从 [CEquipEffect:15918](../decoded/config/autoconfig/knight.gsp.item.cequipeffect.xml:15918) 起；机器表逐件保留真实行号。create-role `weapon`/`showweapon` 是另一个字段，不能拿高阶预览物品代发。普通40100..41000以及“天赐的”新手礼包装备只作为对照，不是本次师父卡的奖励。

## 原穿戴请求和服务器事件 Seam

原调用点 `0x10e1dd4..0x10e1dda` 读取物品对象+8的itemtypeid，算术右移4位后与15求与，即 `(itemtypeid >> 4) & 15`。紧接着在 `0x10e1ddd..0x10e1e0e` 构造 CEquipement vtable0x2276528/type0xc03f5，字段为物品实例key及算出的部位。原构造0xd90f70、marshal0xe4c2d0、unmarshal0xd91020证明两个BE signed32，key>=1、slot>=0；请求没有任务ID、奖励卡ID或完成标记。

本批 [原指令摘录](newbie-equipment-native-disassembly.txt) 和机器表记录26个slot案例：10种原武器类型及16个不同槽号反事实，防止仅以“所有输入恰为武器”自证slot0。另有3个实例key/slot原编解码往返通过，包含key1与signed32上界、slot15。原解码只要求slot非负；恢复服仍须按装备表验证允许范围、角色、等级与归属。

恢复实现应让角色/资产Owner在实际装备变更成功后，依据当前物品实例快照提供可信事件；不可由客户端点击、物品入包、卡选择请求、任意物品ID或NPC10390访问直接完成type59。最小事件证据应包含 role_id/login_epoch、物品实例key、真实template、equipment_slot及资产版本，并验证这是本次合法卡选择的师承武器。这个“关联本次选择实例”的规则是稳健恢复设计建议，**不是已证实原服只认该实例**；原服可能仅查武器槽或指定模板，当前证据不能裁定。

静态检查现有 [Inventory.equip](../inventory.py:688) 会校验物品归属、roleNeed、槽号、等级，并在自己的legacy事务内提交；[receive](../inventory.py:928)随后返回栏1/4刷新。它目前没有独立装备成功领域事件，不能把协议收包当作提交证明；任务接入应由集成方按角色Owner事务/版本约束补齐，不能由本研究脚本另开数据库、建立影子任务或增加全局锁。

## type59目标与报告的证据边界

10个任务是100188、100288、100388、100488、100588、100688、100788、100888、100988、103288。它们ActiveInfoTargetID/Num、UseItemID和AnimationID均为0；任务文案指定“装备师父赠与的武器”。原任务完整属性已保留，不能凭0自行填某个template判定。

例如 [100188:427](../decoded/config/autoconfig/knight.gsp.task.cmainmissioninfo.xml:427) 的 `<G npcid="10390">武器</G>` 关联 [CNpcConfig:3788](../decoded/config/autoconfig/knight.gsp.npc.cnpcconfig.xml:3788)：名字“包裹栏（别动）”、标题“自动打开包裹栏”、npctype4、mapid0、坐标0。它是UI导航配置，不能生成地图NPC或作为NPC对话完成条件。

在完整原映像RTTI中搜索 CReqTaskCheck/TaskCheck 没有匹配；已查相关CCommitScenarioQuest调用点中有矩形区域type40、普通type10对白和通用窗口分支，未找到确切type59穿戴完成报告。**这只能证明未找到该名字，不能证明不存在另一个通用报告。**不能造CReqTaskCheck消息ID、复用CCommitScenarioQuest放宽NPC权限，或把CGetCardItem误称穿戴完成。奖励绑定也不能直接把CItemAttr.givetype=0译为实例binding=0，须沿已核验绑定规则或主策划裁定。

## 复现、结果和未验证范围

运行 `research_newbie_equipment.py`：6份原BXML长度/CRC校验通过，43路线/53任务/43卡/86选项一致，10种真实师承奖励均满足原roleNeed，26个原slot指令案例与3个原codec往返通过。脚本只写来源JSON和反汇编文本；同一路径可重复重建。首次草稿曾只检查任务奖励字段并将来源标未知，后已通过CCardEffect链完整纠正；未依赖该草稿产生任何道具或玩家状态。

未验证：原服发卡精确时点、选择与type10完成的持久化顺序、绑定/品质/耐久实例初值、type59真实完成predicate、装备事件接入任务事务、真实包裹显示和实机穿戴。资料与离线原协议已核验，不等于运行服已发物或完整客户端流程通过。

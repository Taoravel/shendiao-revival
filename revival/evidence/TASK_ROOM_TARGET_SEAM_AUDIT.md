# 任务NPC外层/室内地图：来源与现有接缝

2026-10-24。仅研究102002/NPC10157的已复现地图差异；当前没有任务地图alias政策或实现。调整任何任务目标匹配前，应读此页、NPC原诊断及独立原生导航报告；原通用地图检查继续有效。

## 来源和版本

本批直接读 `artres/config.pfs` 的 `autoconfig/knight.gsp.task.cmainmissioninfo.xml`，PfsArchive核原长度2026233/CRC3f7ab7b3、成员SHA ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706。原表中以10157为ActiveInfoNpcID的五行恰为：

| 原任务 | 原类型 | 原ActiveInfoMapID |
| --- | --- | --- |
| 102002 | 10 | 1007 |
| 102005 | 12 | 1376 |
| 102006 | 10 | 1376 |
| 200490 | 10 | 1376 |
| 200602 | 10 | 1007 |

原始属性/列表及当前源码SHA留 `task-room-target-seam-audit.json`。这份原表混用事实不能证明ActiveInfoMapID总是只供外层导航，也不能证明前两项已过时；需原消费者或正式设计。

NPC窗口原7PFS成员报告 `npc-task-room-original-sources.json` SHA f5ddb3f304d916610559d755a6d9bdc5596b894b2fc98ac1c62207f912c5c7e0：10157定义/唯一原静态摆放在1376/p1(532,920)，1007没有此NPC，两图goto双向各25格。1376原map配置bShowInWorld=false/findpathin=true，没有本记录可直接当parent的字段。门连接是旅行来源，不能自行转为任务受理等价。

本批实际只读核最新NPC覆盖报告SHA94bbaac542926cebc5ef8676c3022b113815adb9d6f4174a102ff7ff48566c33、最新red probe SHA6be4f23ff86cd30af2fc74b63b7a2c0f9bc7d2562b0cf6bad37b66cdb56267fd；probe记录工作区TaskDomain11f93e8e…。初次7153e…probe已归NPC-owned history，本页没有重跑或把新旧当同一结果。最新真实临时RoleOwner：拜访1376原NPC成功、trusted offer102002后菜单无任务、CCommit拒绝Task acceptance NPC mismatch，任务不变；这是NPC窗口执行，本窗口核其报告和源码，不是现服/GUI证明。

## 端游官方支持及局限

定向三条官方域查询后，2012-07-28端游[剧情任务](https://sdxl.wanmei.com/info/renwu/script/20120728/133491.shtml)明确把初入临安叙事放在临安客栈投宿，并把临安客栈老板列入NPC。它支持找室内客栈老板的叙事，未给数字地图ID、实体placement、服务器任务受理比较或所有室内目标规则。不将手游/另一版本攻略当本端游事实。具体外层1007/室内1376接受契约仍unknown，若原消费者也无法闭合，则需根设计者发布精确allowlist。

## 任务侧实际接缝

`TaskConversation.menu_messages`先用target.npc/map过滤active，offered又过`plan_accept`；`open`和`plan_accept`分别执行同样的地图相等。即使单改菜单，`TaskDomain._completion`的普通对白事件仍比较实际evidence.map_id与原target.map_id，最终提交会拒绝。因此别用只改展示/菜单的“修复”绕过未闭合的受理规则。

当前`TaskConversationTicket.address`保存真实完整MapAddress，`_interaction`及`_current_ticket`核本人epoch、地址、位置version与active状态，CCommit另核原NPCkey和option0。NPC距离和摆放由World原NpcScene证明；这些都是正确的物理准入，必须继续以1376实际实体为权威。不能把proof.address改写成1007、伪造1007第二实体或使用任意可达图闭包。

若后续有正式精确映射，合理Seam应是一个显式启动冻结的任务目标匹配Interface，供菜单、接取和纯Domain完成消费同一项任务/原逻辑目标/真实物理NPC许可，原资源保持字面值。许可携带政策/来源身份；ticket、实体key及World完整地址仍保留实际值，未批准任务继续走原精确比较。此为接线需求，不是已批准的接口形状或本批实现；原server具体容许范围仍待来源/根裁定。

102005/102006/200490原本已经指定1376，不需要为解决102002而扩域；200602的原1007差异另需任务范围核准。更远的309个摆放缺口包含动态/私有/历史内容，不由此一例批量等同。

## 方法和边界

research按直接原PFS→端游官方→仍未知分层，后台代理独立查原生导航消费。diagnosing-bugs沿已存在且两次复现的真实临时red loop，当前只核信号与代码，不重跑游戏/GUI；codebase-design找到真实重复目标比较接缝，保留物理所有权；writing-for-agents把版本、未采用规则及后续条件共置。产物为本页和task-room-target-seam-audit.json。未改任务/World/shared实现、中央政策、在线服/真实DB；没有开放alias或正式战斗。

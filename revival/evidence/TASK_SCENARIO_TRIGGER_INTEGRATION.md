# type50空表现节点与剩余触发缺口

2026-10-23。原指令和原配置证据见 [TASK_SCENARIO_TRIGGER_RESEARCH.md](TASK_SCENARIO_TRIGGER_RESEARCH.md)。本批新增三个真实NPC交接节点的独立模块支持：203601“千军万马来相见”、205701“蜕变”、233701“年的传说”。与此前122条完成对白、2条开始对白合计 **127条静态NPC type50能力**；独立intro10条另计。全234条中的其余97条仍按原机制和触发缺口保留，不因表现字段为空自动完成。

## 三条NPC交接的接口与完成条件

新增 `supports_npc_empty_scenario(task)`复用已有静态NPC条件：type50、地图>0、ActiveNpc真实且非999999、没有轮次占位、动画/传送/分支/计时/交物/变身等额外机制、Start/Finish/Note均空。当前原表恰好三条符合，目标为临安10958/蝴蝶谷11224/临安13914，原最低等级29/50/40；原所有数值奖励为0，保留0。

1. 可信任务或活动策略先提供offer，再调用既有 `TaskConversation.plan_accept`。可接目录只证明展示入口：203601有原可接说明，205701和233701没有该条目；本批不从缺失条目猜接取来源或开放节日活动。
2. 既有active0同步后，真实NpcInteraction/当前Location经 `menu_messages/open`建立原有单个ticket；`opening_messages`发送ready3+SVisitNpc。该族 `TaskDialogue.lines`为空是原行为，原客户端菜单进入后直接提交，不必补正文或等待对白结束。
3. 当前CCommit必须匹配taskID、真实NPC实体key和option0，期限/位置版本/租约检查沿用既有会话。证据为 `npc_empty_scenario_committed`；TaskDomain再次校验族、NPC和地图。CQuestDialogEnd不能首次完成，任意NPC0提交不能冒充该证据。
4. `complete_task_transaction`仍在调用方角色事务中结算当前任务、原奖励、可支持唯一后继与幂等凭据。调用方在同一事务完成当前背包及最终装备属性等必要消息编码，提交成功才清ticket、发布缓存并投递。没有新codec、DDL、TaskPlan字段、额外账本或共享入口变更。

原state1在本族只进入既有后置清理，不读Start/Finish/Note，因而本批未增加Finish重播抑制标记。首个完成仍按普通任务移除当前bean；公共重试返回当前资产且不再次激活已有后继。源码支持不是GUI确认，SVisitNpc投递也不是玩家已点击确认。

`TaskChain`认识该能力，但三条当前没有原incoming边；这不是自动offer授权。它们后继203690/205702/233702均为原type10，仍经已有唯一原边、等级/形象、未知前置等判断。当前203601的真实事务验证确实只激活203690一次，没有把整条支线全部完成。

## 不同表现下的触发范围

原type50共234：已支持127条静态NPC能力与10条原intro，剩余97条按原表现分组为电影2、开始对白16、完成对白20、Note20、空表现39。完整原字段及本批派生支持/缺口分组见 [task-scenario-catalog.json](task-scenario-catalog.json)。这些是当前独立模块覆盖，未包含运行服部署和每条GUI验收。

- Note20全部是轻功修炼NPC0/map0入口。原文字虽说“恭喜获得”，实际在state1处理时显示；重复state1即使无bean也会重显Note。每条唯一后继均为本ID+1的type56，20个后继全部已符合既有静态到区能力；缺口在入口授权而非这20个区域的解析。当前仍缺可信接取/完成触发和实例/前置政策，因此尚未开放这20条，更没有用Notice显示代替获得轻功。
- 空表现42中本批只接三个真实NPC，余39条仍有NPC0/999999或章节、福利、活动触发问题。零目标/零奖励并不赋予立即完成权限，不能把ActiveMap或可接名称当服务器事件。
- 剩余Start16含NPC0、999999、入城传送与四个轮次；剩余Finish20含额外机制、NPC0或占位NPC；电影10020/10026保留独立授权和结束事务缺口。各自原证见此前Start/Finish/电影报告。
- `SNotifyStart0xc4a9c`经原marshal/handler确认是一个u64倒计时时刻，消费者计算与当前clock之差后显示倒计时；它没有taskID，不作为通用空/Note任务启动接口。

下一步无NPC节点需要所属规则提供明确触发身份，再按角色事务完成及衔接。原客户端能够显示完成提示与原服什么时候授予/完成是不同证据；原生调查未闭合的部分交主策划统一补全，不增加凭空命名的剧情启动包。

## 必要验证与本批方法

[task-scenario-empty-check.json](task-scenario-empty-check.json)记录三条纯原定义计划与203601/NPC10958临时库事务：

- 真实NpcScene目标、显式offer、active0/ready3、原空对白和匹配CCommit；未offer、错误NPCkey、移动版本变化及DialogEnd拒绝。
- 原0奖励与唯一203690同事务，重复请求不重奖/不重置后继；新租约回读完成及后继，旧租约拒绝。初次夹具未注入当前背包需要的钱包规则而正确拒绝；补齐显式钱包基线后通过，生产代码未增加兜底钱包。
- 因公共会话和续接分支新增，两个Start与122个Finish的既有必要检查再次通过。公共写事务沿用既有晚期失败回滚检查，本批不重复全面回归/root自然链。

research后台用原PFS/原指令和少量离线探针确认三条空Start直接CCommit、Note显示时序及SNotifyStart真实用途；codebase-design将三族差异收于纯能力/证据判断，复用原会话、角色事务和奖励Interface；writing-for-agents将可信offer、当前NPC、提交、消息编码和成功判据按顺序共置。产物：领域/会话/续接增量、原生研究、派生覆盖目录、必要检查和本交接。

未验证：三个节点自然领取来源及完整支线、13914节日NPC真实生成、其余97个触发/附加机制、共享连接端到端、GUI画面、在线存档和正式战斗。NPC位置/角色等级/offer是明确可信测试夹具，没有操作当前客户端、在线服或改共享文件。

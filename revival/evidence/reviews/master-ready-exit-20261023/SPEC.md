# Spec

0项可确证缺陷、遗漏或越权。

沿用code-review独立Spec轴、codebase-design的逻辑消息/连接所有权Seam，审scope.json固定5文件；基准为真实npc不可变发布，非Git，无提交列表，不评继承wild/care。

SPEC_SOURCE.md:15要求“再发送同任务SRefreshScenarioQuestState(state3)，最后发送原任务NPC菜单”，:16要求车夫“相同次序”。current/task_master_card.py:207–214与task_cart_dialogue.py:152–161均为Accept→Refresh3→Visit，保留原任务ID、凭据与奖励时序。

Spec:48要求“signed32=-1（ffffffff）”，:50要求“启动加载冻结政策/逻辑消息”“每次合法角色入场”。current/role_protocol.py:21–32严格生成c0039及BE signed -1；game_runtime.py:1013启动保存tuple，:343–363在每次合法AFTER_ENTER_WORLD回复首项加入。原c0011/c0031及资产状态未改。

只读候选checks的初始化/生命周期/原已有bean结果均passed，未替代本轴静态证据。未执行代码、数据库、服务、GUI或战斗，未改候选；真实现场确认窗、对白及部署后效果仍待验。

# Spec

0项可确证缺陷、额外行为或本批需求遗漏。

沿用已读code-review与codebase-design，以Interface/Seam追踪固定增量。基准按scope.json逐文件固定；无Git，未声称执行提交/merge-base比较。

依据ROLE_RESOURCE_STORAGE_INTEGRATION.md:55“完整source与数值caps完全一致”、:59“HP/MP/version保持”、:63“同一资产版本”、:67“0XP不写资源凭据”，已核对current/role_equipment.py:96、role_equipment_storage.py:95及:116、role_resource_plan.py:190、role_resource_storage.py:174、role_growth.py:199–230与role_growth_actions.py:22–75：纯属性组合严格匹配；来源差异只拒绝；source-only不治疗；成长先验当前profile，再只写裸身、结算资源；零变化跳过资源收据；动作刷新重读当前最终profile。旧默认writer围栏保留。

仅静态审查；未运行测试、服务、真实库、GUI或战斗。药品/NPC/任务、共享load和六槽未接入不属本批缺陷，亦未据此宣称全流程完成。

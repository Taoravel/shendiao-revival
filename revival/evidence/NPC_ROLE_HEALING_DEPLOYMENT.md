# 人物治疗294最小发布

2026-10-23 21:05:06（北京时间）部署 `npc-role-healing-20261023T125539Z`，PID36632，唯一监听 `127.0.0.1:28993`。实时状态仍应读取 latest-deployment-verification.json 并核实际进程；旧39796为历史。

## 已发布范围

仅原NPC10380/placement34的294治疗：已知无伤势resource.1资料、当前HP>0、普通等级1..155，恢复当前最终HP/MP上限并收取等级×30银两。已付重试只读当前状态；后来受伤或死亡不会被旧请求再次治疗。未知资料、满状态的新请求、死亡、错误NPC/服务及loading/battle占用均拒绝。规则与来源见 NPC_ROLE_HEALING_DECISION.md，完整领域交单由NPC所属窗口维护。

对实际原39796固定基线仅7生产输入、255行差异：6份已审治疗/数值输入，加由BASE提取的game_runtime.py三行路由。没有复制工作区共享入口；私有地图、血手印、交互距离、社交scope、care、新角色资源和v2均未混入。

## 已完成验收

- 同一实际加密Owner检查在旧BASE准确失败（无294菜单），新候选10项检查绿；领域11项、实际连接3项及guards7项由主策划和NPC窗口分别对精确source/config独立复验。Standards/Spec均0项，固定报告 reviews/npc-role-healing-release-20261023/REVIEW.md。
- 停服前精确身份、唯一监听和Established=0门控；停机一致备份保留在固定目录 accounts-at-stop.sqlite3。启动1429份源码/配置及启动记录哈希匹配，版本601握手/未认证心跳和数据库quick_check通过。
- 107张旧表（含sqlite_sequence）逐行不变，仅新增已审空表npc_role_healing_receipts。未删除角色、重写任务、发放货币或自动迁移资源。

机器记录 npc-role-healing-deployment-verification.json。主策划已独立只读核精确runner、PID/port与1429manifest+runner哈希，未访问真人库。两份候选metadata已标deployed/PID36632。

## 未验范围

没有打开客户端、真实认证或执行战斗；实际画面由用户验收。未知资料的已有角色保持未知，发布本身不会把其初始化成可治疗状态。剧情实例及全部生命周期/发送围栏仍属于后续源码批次。

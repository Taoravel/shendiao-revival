# NPC首次授权部署记录

2026-10-23 18:25（Asia/Shanghai）。用户在NPC聊天明确要求“直接部署啊”，本窗口据此执行实际发布；不再沿用此前“保持PID8724”的状态。

后续统一/怪物发布已替换本页历史进程；当前现场以runtime/deployment.json与evidence/latest-deployment-verification.json为准。

- 本次发布进程（历史）：PID33072，监听127.0.0.1:28993；未开启training。
- 固定发布：`runtime/deployments/npc-20261023T102110Z/run_release.py`；1044个源码/政策/目录输入逐文件捕获并回查工作区哈希，额外包含原生验证镜像。源码、design及catalogs都从发布副本加载，原artres资源和持久runtime路径保留。
- 切换：核对旧PID8724的精确命令行及监听所有权后停止，保存accounts-at-stop.sqlite3一致性备份，再隐藏启动新进程。旧发布目录保留以便回退；没有改写工作区shared源码。
- 存档：启动前对备份副本运行prepare，启动后对真实库与停机备份逐表逐列比较。原有84张表的所有行一致，quick_check=ok；角色、任务、资产未被重置。新增启动表不作为旧数据改写。
- 发布前检查：在固定副本运行11项启动/NPC/资源/背包/新手自然链/Owner隔离检查，结果在发布目录preflight.json。实际原生解码依赖缺少native-image.bin的打包反馈已补齐，再跑原检查转绿；校验脚本参数也在runner中隔离，不修改玩法实现。
- 发布后检查：真实TCP Challenge版本601、合法4字节未认证heartbeat回显通过；runtime/deployment.json的PID和全部Python启动哈希与本发布manifest一致。没有登录、移动或发奖给真人角色，原客户端GUI仍由用户验收。

精确结果见[npc-deployment-verification.json](npc-deployment-verification.json)及latest-deployment-verification.json。codebase-design用于固定代码/启动输入与持久角色状态的Seam；diagnosing-bugs用于固定副本启动反馈与协议探针修正；已有原子事务及原生Peer验证沿用前批tdd，未把备份存在当作数据一致性证明。

范围：本次部署的是捕获时已验证的工作区版本，并非NPC全量目标完成。购买/出售/回购/仓库已接新资源Owner；修理和宠物恢复的新profile共享临时门控仍保留在捕获版本，未迁移旧角色的对应功能已通过真实Owner检查。新profile自动迁移及六槽v2未激活；动态NPC生命周期/巡逻等未接入口不因文件已进入发布包就宣称启用。后续工作区修改仍需另一次明确发布才影响运行服。

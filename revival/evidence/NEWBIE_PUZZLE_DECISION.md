# 序章画卷完成声明

2026-10-23，主策划采用`design/newbie-puzzle-v1.json`。客户端原任务、553菜单、2×2本地交换和最终CCommit(taskID,0,0)已由原PFS及原指令验证；原请求没有棋盘、步数或解题时长。服务端接受经当前章节/私有地图/NPC许可约束的客户端完成声明，明确`server_verified_board=false`。

按客户端→同款官方攻略顺序核对，见PROLOGUE_PUZZLE_RESEARCH与PROLOGUE_INTERACTION_POLICY_RESEARCH。官方40级杂学拼图与本族原对象不同，不能套限时、评分或杂学奖励。原服本族时限/失败重试仍未知，因此最短等待0、许可300000ms和取消/重登行为全部designed。0只表示不再加服务器时间门槛；五分钟是菜单能力有效期，不是棋盘倒计时或防伪保证。

仅十任务/43真实原章，精确1501私有目录、11106/placement16。先获当前地图证明再开553菜单，提交用服务器保存的完整实体key重新证明；客户端zero key不授予查找任意NPC的权力。NPC距离统一由地图启动选择的独立交互政策证明，画卷不另授免距或例外；新候选见NPC_INTERACTION_CELL_DECISION，旧隔离32近点仅保留其验证范围。一次只持有一个当前ticket，已观察的移动、其它菜单、任务/场景/战斗状态变化及断线使其失效；没有上行的本地关闭无法直接获知。重登只恢复任务bean0，再访问取得新许可，无失败扣罚或重开冷却。

原人物EXP均360；桃花100719宠EXP350，其余360。公共宠物奖励资格、固定接收宠及幂等规则不变，原其它渠道零，不补比例奖励。完整完成、奖励、后继和最终回复编码同一角色租约事务；已付恢复不得重复奖励或Finish。现公共奖励恢复可能更新投递effect，不能宣称全库只读。

任务窗口单写Module及正式policy启动loader，原始集成窗口单写共享路由。中央JSON为参数唯一来源，启动冻结，不把测试1000ms复制到生产；当前已有`isolated-unapproved-puzzle-fixture`验证须保留来源并另补正式0及300000边界。后继仅原黄药师任务active0，不自动梦醒传送，不越过暂停的正式战斗前置。

方法：research限制跨玩法外推；codebase-design把声明、许可、地图证明和角色奖励藏在专用Interface；writing-for-agents共置来源、实施顺序及验收条件。root此前独立fixture六组绿见task-prologue-puzzle-root-fixture-verification，真实后续入册/接近是明确fixture。

正式loader完成后，root独立原样默认正式policy检查七组绿，六文件含中央policy执行前后SHA稳定，见task-prologue-puzzle-root-policy-verification。minimum0即时、deadline-1可受理/deadline拒绝、过期/新lease重新访问、strict policy、错误当前证明拒绝、调用方最终编码Seam受控异常全表回滚、公共人物/宠360与350和paid不重奖均有实际反馈。该晚错是编码Seam受控抛错，不冒充原codec某字段自然异常；后续任务入册/接近仍fixture，没有完成前置真实战斗。尚未shared、GUI/部署或自然走完前置故事，任务窗口固定双轴交单另验；目标继续。

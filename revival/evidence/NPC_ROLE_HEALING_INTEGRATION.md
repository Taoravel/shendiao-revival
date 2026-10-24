# 女大夫294人物治疗接线

接入294、调整费用或重放行为时，先读NPC_ROLE_HEALING_DECISION.md及唯一配方design/npc-role-healing-v1.json。本批实现按该设计授权；原CNpcService294和菜单“等级×30”文本为client_verified，实际治疗范围及NPC关联为designed。其它治疗服务92/459/1957/2037仍分别核验，原10009无静态摆放，家族郎中10054不获得294权限。

## 当前完成条件

所属Module及注册已完成：npc_role_healing.py，npc_gameplay.prepare调用其启动prepare，原女大夫10380/map1007/placement34开放294。固定四文件双轴Standards硬0/判断0，Spec缺失0/额外0/错误0，报告reviews/npc-role-healing-20261023。数值cause和货币purpose六文件另由root审查，报告reviews/npc-heal-resource-20261023。

本功能已由唯一集成方部署到npc-role-healing-20261023T125539Z/PID36632，继承39796全部已发布功能。共享RoleOwner三行接线及两个真实菜单/路由红例均完成实际Peer转绿；verify_npc_role_healing_guards.py另通过7项实际入口/重登/重放检查。当前版本以runtime/deployment.json为准，GUI仍未验证。

发布前，NPC窗口独立核对1429项manifest、六ready输入和共享三行，恰七个生产输入改变、无删除；不含工作区private/radius/social。优先导入候选全部生产Module，验证器仅将报告OUT指向独立工作区目录，基础3项/guards7项/领域11项全绿，整个候选source所有文件前后逐字节不变，证据npc-role-healing-candidate-audit.json。

发布后，NPC窗口独立核对唯一127.0.0.1:28993监听PID36632及准确runner命令行、1429项manifest和runner SHA；启动记录437个源码哈希均匹配manifest子集。真实未认证socket收到601 Challenge及合法heartbeat；只读事务核quick_check并与停服一致性备份比较全部107旧表（含sqlite_sequence）逐行不变，唯一新增空npc_role_healing_receipts。独立结果npc-role-healing-deployment-npc-verification.json（owner-audit同内容别名）；main主发布记录npc-role-healing-deployment-verification.json保留其固定release原字节。没有登录真人、修改角色或验证GUI。工作区private/局部距离等后续增量仍未包含在此进程。

## 最小共享接线

main已在共享game_runtime.py导入npc_role_healing，现有NPC_SERVICE经地图当前交互证明及NpcServices.plan后，在角色邮箱内调用：

```python
if command.handler=='role.heal':
    return await self.io(npc_role_healing.settle,self.rt.accounts,self.inventory,command)
```

此调用使用既有有界I/O；Module返回逻辑消息，由原连接所有者统一编码投递。运行时需要启动加载root已审的resource cause npc_heal和cash spend purpose npc_role_heal。无需新增网络包、全局调度、热DDL或另一资源记录。

## 领域行为

启动冻结配方并建receipt表，严格检查原10380摆放34。每次受理要求有效角色租约、当前完整MapAddress/原NPC/服务/位置证明、期限与请求身份。角色必须具有明确已迁移resources.1、当前装备/成长来源；旧未知和pending source均拒绝，不由治疗初始化、迁移或同步来源。

新请求仅在HP>0且HP/MP未同时满时执行，普通权威等级1–155每级30现金，补至当前最终HP/MP上限。费用、根资源transition、领域及共用凭据、最终原生属性/余额编码在同一角色事务；原生编码或晚期存储失败全部回滚。活力、伤势、宠物、耐久、经验和章节不改变。

paid先核稳定原意图及冻结admission（含原等级、费用、before资源和目标），再读取当前权威。新租约重新取得有效证明后可重放；后来的伤害、死亡、满状态或成长不再次治疗、扣款或重算旧费。domain/common凭据不一致拒绝。

## 验证证据

verify_npc_role_healing.py实际执行公开NpcScene→NpcServices.plan→settle，共11项通过：70/40补至100/100、等级1收费30、绑银500及背包不变；已满/死亡新请求拒绝；paid保留后来80/60及死亡；真实消耗89经验升2级后旧费30/新费60；旧租约拒绝、新租约paid不再治疗；资金不足同失败ID补足后可成功；未知profile及真实背包改变导致pending source拒绝，来源owner明确同步后原失败ID才可结算。

真实SQL触发器在费用/资源/领域凭据写入后阻断共用凭据，完整状态回滚；真实hit16777217触发最终原生float编码失败，完整回滚。直接SQL比较用于验证明确的原子性要求。未以回调、手造已付receipt或替换dispatcher制造成功。领域结果见npc-role-healing-domain.json。

实际连接基础脚本通过原10380菜单294、70/40至100/100、cash1000至970、bound500/背包不变及唯一资源v1。补充guards先由原线包生成真实paid记录，再观察服务端受理ID交公开角色邮箱重试；后来canonical资源损耗夹具80/60保持，当前cash970不变。新认证租约重登仍80/60，旧paid不再治疗；新收到相同线包才治疗并再扣30，cash940/资源v3。满状态、92、假key、畸形、未知profile以及受控battle/loading占用拒绝均不产生资产/凭据变化。伤害和占用明确为fixture，未执行实际战斗/切图。结果npc-role-healing-runtime.json和npc-role-healing-guards.json；新增验证及车夫夹具单独冻结两轴均0于reviews/npc-healing-guards-20261023，Spec独立复跑两脚本绿，Standards为静态及结果核对。

方法：tdd以真实Peer菜单红、领域公开Interface红、共享路由红逐个纵切推进；codebase-design将校验/单事务/当前回包集中在settle，保持共享调用很小；code-review按实际39796固定发布与四文件冻结字节作独立两轴；writing-for-agents集中接线条件与证据。所有验证均为临时库及内存连接，未启动客户端、执行实际战斗、操作真人角色或证明商业容量。

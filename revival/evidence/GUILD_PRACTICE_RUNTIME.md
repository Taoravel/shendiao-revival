# 七项个人修炼：资材预留与角色结算

第十一批已扩展修炼丹mode1、可信NPC Adapter、已知技能登录投影和预留自动恢复，详见[GUILD_PRACTICE_NPC_RUNTIME.md](GUILD_PRACTICE_NPC_RUNTIME.md)。本文保留第十批现金事务说明；原NPC正式注册/分发、完整面板与GUI仍未完成。

第十批实现七项战斗修炼现金mode0的后端事务，接入既有有界帮派所有者，并完成原NPC上下文/按钮/更新格式核验。尚未接真实NPC购买路由、完整修炼面板/登录恢复和战斗效果，不能称游戏内修炼已完成。原生type c36cc未加入SOCIAL_TYPES，防止绕过NPC凭据直接购买。

## 状态所有权与调用顺序

`role_practice`提供显式七项基线、read、plan、settle；技能等级/剩余修炼XP/版本和购买凭据归角色。`guild_practice`提供资材余额、持久预留、成功确认或取消补偿；资材和预留状态归帮派。启动由OrganizationStore.initialize统一建表；新建帮派的已知资材0为designed，历史缺失不回填。角色旧技能未知同样拒绝，不因查看/登录自动初始化。

可信NPC接入方按以下顺序使用既有Seams：

1. 地图/NPC所有者重新核验entity_key、placement、服务1023绑定、角色位置版本/距离和login_epoch。practice_protocol.request只解原Q+i32+i8，不能把解码成功作为NPC授权；Q不作帮派ID。服务菜单显示与当前购买均须核验。每次新线包分配新服务器request_id；同次受理重试沿用该ID。
2. 从角色所有者读取已知七项状态/版本，按权威成员关系获取帮派。调用OrganizationRuntime.command，operation=reserve_practice，args=(skill_id,expected_skill_revision)。该命令在帮派事务校验入帮7天、开放类型、当前成员代次/声望与人物等级，持久预留3资材，保存价格、技能前态、租约、两层成员代次和deadline；不动现金或角色技能。
3. 返回角色所有者，经其有界持久化执行role_practice.settle(db,account,role,epoch,guild,reservation,now,rules,currency_rules)。必须传入已有登录围栏事务，函数不开连接、不提交。它再次检查资格和预留，原子提交cash扣款、技能XP/等级、版本和角色凭据；异常须回滚调用事务。不得在帮派所有者中同步等待此步骤。
4. 通过新的组织命令resolve_practice，args=(reservation_id,)，由同一帮派所有者读取持久角色凭据：已付款确认committed；未付款取消并退资材一次。取消后迟到的角色购买被拒绝。成功角色凭据存在时不可因断线、超时或退出而退款。
5. 新租约恢复先调用OrganizationStore.pending_practices(actor,epoch)，返回有索引且至多政策上限的冻结预留；按帮派ID分别投递resolve_practice。恢复确认可在已经退帮后进行，不要求继续持有原成员资格。旧租约不能查询或购买。第十一批已由目标邮箱登录入口启动独立有界恢复任务，当前epoch未过期不取消；孤立child保留待核对，不误判退款。
6. 只在目标角色发送所有者中用practice_protocol.UPDATE_ASSIST_SKILL及update编码当前绝对技能值；钱包也重新读当前绝对余额。成功重试返回当前技能/钱包，不把历史余额写回缓存。第十一批已接已知七项登录逐项更新，不将七项伪造成全生活技能替换列表而清掉其他技能。

这套是同SQLite文件的兼容Adapter：角色写角色表、帮派写帮派表，各自事务读取对方持久决定；SQLite串行提交保证取消与迟到购买不会同时成功，没有添加世界锁。跨数据库/进程需可靠outbox/inbox与同等撤销围栏，当前不宣称跨分片结算完成。

## 数值来源与缺口

单一政策：recovery-baseline.json.organizations.individual_practice。原表51行levelneed/expneed/reputationneed保留，不拟合经验曲线。

| 规则 | 来源 |
|---|---|
| 七项360001..360007 | 原clifeskill和GangSkillRole，client_verified |
| 现金修炼每次+10XP、消耗3资材；丹分20/30XP且不消耗资材 | 原gangskillrole.layout说明与144184，client_verified；本批仅结算现金 |
| 入帮7天 | 原cmessagetip144156，client_verified；有效加入时间取角色入族/家族入帮较晚者 |
| 0现金按钮、1丹按钮 | 原14d4020/14d4150实际执行，client_verified |
| 现金费用前三项30000、后四项20000 | designed，针对性官网检索未找到原成本，不能当原服数值；替换须保留已发预留中的政策/价格，旧政策显式迁移 |
| 下一等级行消费XP、余数保留、受限时整笔拒绝 | designed，原表值不变；不出售会被丢弃的XP |
| 50级上限 | cadvancedability51哨兵推定，inferred；不是本地所有特殊阶段已恢复 |
| 当前guild_member_state.prestige与原reputationneed比较 | inferred，原字段及原显示已证，完整服务器比较未证 |
| 仅cash支付 | designed，currency的skill_training用途已允许；未将官网生活技能储备→游戏币→存款顺序套到战斗修炼 |

普通人物等级只接受1..155。原等级门槛1129完整保留，不能减1000猜特殊段；相关高阶修炼继续未接。修炼丹mode1、属性修炼mode3/4、铭文、生活技能人物经验/混合支付、完整NPC返回均不走此现金recipe。研究进度及资材生产尚未实现，测试中的补资材/声望/等级/组织资金是明确夹具，未加到真人。

## 原客户端核验

verify_role_practice_native固化4组。实际执行原七项按钮14d4020、14d4150，截获CPractiseSkill c36cc、Q+skill+mode0/1；原AssistSkill e56a90及SUpdateAssistSkill dd0a80与>iii一致，后者原构造器给type c36b7。原c36cc序列化0..4均保持原字节，不给未证模式编造消耗。

NPC switch按原范围797..1054的第二级表163f5f0/163f578查service1023，落1639b1f；实际执行该分支→14d86d0，NPC UI+d0/d4复制到对话框+168/+16c，注册type13上下文同Q。不能将所有service ID套低段2..233的163f1c0表。本次证明客户端Q来源，未证明服务端地图资格或NPC实例已存在。

## 验证与完成条件

verify_role_practice：12组通过。包括七项已知基线、经验升级、7天/等级/声望、三资材预留和现金/经验同事务、幂等、末端receipt写失败整体回滚/一次补偿、8次角色付款与帮派取消竞争、deadline/关闭/余额不足、租约替换、退出/重入、重启和未知资材拒绝。实际GameRuntime组织所有者竞争最后3资材只有一个预留成功。

实际AccountStore的FencedConnection没有executemany，首次通过真实围栏初始化已复现并改为7次execute；角色连接默认tuple行曾使复用guild_offices.member失败，改为该Module返回冻结前的独立命名字典，组织调用者继续使用同一Interface。没有修改全局row_factory、AccountStore或围栏。

帮派管理11组、四连接TCP7组、职位10组、研究开关10组、实际冻结政策启动3组、组织现金支付13组本批回归通过；组织运行回归结果另见其JSON。原生4组不算GUI。未部署、重启服务、打开游戏、改真人/持久用户存档；共享game_runtime/runtime_storage/accounts/serve/gateway未改。

下一步完成条件：接地图验证过的NPC服务和个人请求、完整最大等级/开放类型/费用响应与登录恢复，完成丹/属性/生活技能结算及属性/战斗消费；再验真实客户端购买/断线/重登和结果。跨分片、生产/建设/活动、全量社交仍未完成。

方法：codebase-design集中状态所有权、冻结预留和小Interface；tdd沿既有组织/角色事务Seams逐项真实红→绿（缺Module、缺初始化、未知命令、缺结算）；research并行官方primary资料核对并由父检查；接口故障通过真实围栏反馈收敛，writing-for-agents集中接入前提和可判定完成标准。补充回归不冒称每条断言都经历红，未声称Standards/Spec双轴审查。

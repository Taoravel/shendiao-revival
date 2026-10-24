# 宠物已学技能、秘籍事务与当前接线

2026-10-23，端游1.6.1/网络版本601。PetSkills冻结存档、普通/绑定秘籍、认证保护与拓格进度领域及原生Adapter已实现。当前数值/进度唯一裁定见PET_SKILL_LEARNING_DECISION.md（pet-skill-learning-v3），绑定见PET_BINDING_INTEGRATION.md。共享RoleOwner尚未接入c07ff专用Adapter，现场/GUI/战斗技能效果未验收；完整目标仍active。

限时技能现已补领域/原生验证，学习、查询、可信发放、到期事件和battle有效ID接口读`PET_SKILL_EXPIRY_DECISION.md`。旧回执兼容，旧到期未知不自动永久，空标记书拒绝；原191条映射中实际能力书189条。带时间学习使用`receive_pet_skill_book(body,epoch,request_id,draws,now_ms)`，draw仍固定0..9999；共享实际接线与GUI状态维持待完成。

## 接入顺序与完成条件

1. `Inventory.prepare`启动加载只读SkillRules及其LearningRules，准备技能/回执/拓格进度表。pet-skills-v1保留原ID存档及确定生成基线，当前学习概率/认证/进度归pet-skill-learning-v3；114条原技能定义、158个原宠物候选集合、191条原秘籍映射（95非绑定、96绑定）保留。绑定书依赖pet-flags-v1下已知完整标记。
2. 新发宠在物品/成长/养护同一事务生成已学技能：按原候选顺序取最多2个不同正ID，忽略0，占位与候选不视为全部必带。**选择数量和确定性选取是designed恢复基线**，不是已还原原服随机概率。旧宠缺skills仍None；可信、已知完整普通且无到期扩展的旧实例才可调用 `initialize_pet_skills(db,pet_id,learned_tuple)`，已有状态禁止重置。flags独立显式初始化，不能从已学列表推断绑定。
3. 调用方fenced角色事务使用 `learn_pet_skill(db,book_key,pet_id,epoch,settlement_id,expected_version,draws,*,options=None)`。要求自有未放生宠、已知成长/养护/技能/历史进度、当前租约、携带秘籍与人物等级；两个服务器draw为0..9999，固定于同一受理命令。可选SkillBookOptions携带认证符实例和保护ID。扣书/认证符、技能、进度、可选绑定、资产版本和回执同事务；调用方保存公共凭据，提交后发送。
4. 原生CPetLearnSkillByBook0xc07ff走 `receive_pet_skill_book(body,epoch,settlement_id,draws)`。RoleOwner校验joined/非战斗/非传送，固定服务器draw及请求键，在有界I/O执行Adapter。完整24字节解析pet/book key、两认证符实例和两个受保护ID；待学技能由书映射，不接受客户端指定随机值/颜色/版本。当前Owner顺序状态使用expected_version=None；同键指纹含学习政策、全部选项和固定draw。
5. Adapter同事务预编码当前完整Pet、实际cash背包和当前受影响宠物进度；绑定学习/对应回放还编码当前完整栏并恢复参战选择。缺钱包或无法表示全部回滚。跨Module调用方也须提交前编码当前逻辑回复。历史回执只确认当时before/after；重放读当前技能/进度，不写回历史。c0800空查询返回当前c0801进度map，旧未知保持pending。

完成条件：相同公开Interface下，正确技能/保护/进度、精确消费、重试无重复效果、旧回执不覆盖后来状态、存储/编码失败回滚、重开保留；运行时仍需共享路由与原客户端验收。**INVENTORY_TYPES当前16类，c07ff普通二参数receive仍明确pending，须用上述上下文Adapter；c0800查询已提供。16不作为完整玩法计数。**

## 已实现规则与数值来源

已学技能为有序精确原ID，普通/高级使用不同原ID。当前扩格几率采用2017官方端游公示的按数量/认证组合表（guide_supported，1.6.1完全一致未证），替代首批统一250/1000设计；两draw范围0..9999。追加失败只从未保护位置替换；同系按ID//10、阶按ID%10及进度保底顺序仍designed。格数上限4/4/6/8/10/12来自原客户端。当前规则归pet-skill-learning-v3，初始最多2技能的生成基线仍归pet-skills-v1；完整来源与失败消费见PET_SKILL_LEARNING_DECISION.md。

原cpetskillsuccessconfig.progress完整保留0/10/20/40/80/100/200/400/1000/2000/4000/10000/0；原UI已确认它是按当前技能数取的进度条阈值，概率另用官方表。绑定书已按pet-flags-v1恢复，认证保护及独立进度存档已补；到期技能和其余容器仍未恢复。常规item→skill来自cpetitemeffect.petskillid，并与技能表反向映射核对；如沐春风反向两项0仍保留显式原item映射。

[2012-07-29官方端游技能资料](https://sdxl.wanmei.com/info/qita/pet/20120729/133549.shtml)与[2012-12-31官方宠物介绍](https://sdxl.wanmei.com/news/gamenews/20121231/139075.shtml)支持同款端游有这些技能及初始技能外的培养途径，未给出本版精确初始抽样、覆盖概率、保护/绑定算法。后期2022/2025扩格上限与其他游戏/手游结果未移植。

## 原生证据

- Pet构造f89ba0、marshal f5df70、decoder f5f1f0：bean+b8是list<i32>，compact数量、按原顺序若干BE32 ID。空名字原默认187字节，计数位在wire138；两个ID的原marshal结果与独立拼接逐字节一致。生产pet_record在固定标量尾部129处替换这一空列表，并保留之后所有独立容器/字段，不因列表变长改错后段坐标。
- 原SRefreshPetData构造f9d7b0/decoderf9d880后，执行11353c9..11353fa把message+c0（内Pet+b8）经原825860 list复制到内部pet+40。再执行140dfb2..140e0ed原图标循环，经迭代/到期map查找传给12d8120；宿主仅观察终端调用，不执行GUI，不同格确实收到200091/200061等原ID。
- 原请求构造dbc7a0、marshal e53610、decoderdbc880为6个BE32。原拖入分支142d844..142d885生成pet/book实例key及4个-1；完整认证发送分支142d6f5..142d784也已执行，生产完整Adapter接已验证的选项身份并作领域校验。
- CpetItemEffect表由89d860返回root+650，其RTTI是CPetItemEffect。原UTF16 petskillid2265878经a6e49b..a6e4c7写record+4；petbangding2265860经a6e4d7..a6e503写+8。142d805检查的+8因此是绑定标志，不能误当技能ID。

详细结构化结果为pet-skills-native.json及pet-skill-protocol-verification.json。native_gameplay_probe仅新增可选解码后observer供原消费者执行；原有默认签名返回不变，不参与生产服务器。

## 方法、产物、验证与未验证

codebase-design将配置/计划/存储/回执集中pet_skills，Inventory只做当前租约、权威状态和逻辑回复的组合；PetState.skills传冻结值给任务/战斗所有者。tdd在既有公共snapshot/pet_record/事务Seam先复现“新宠仍无skills”，接入后验证真实扣书及原消费者；概率249/250边界采用明确设计算例。diagnosing-bugs以原非空marshal、原刷新复制和原图标循环组成独立反馈，真实SQLite技能保存abort及外层异常验证回滚。writing-for-agents将可信上下文、来源和未接模式集中本文。

产物：pet_skills.py、pet-skills-v1.json、pet_protocol请求解析、Inventory局部接入、原生研究与两个新验证脚本；没有修改共享入口。

已通过：默认技能持久化/冻结/原图标参数；追加、升级、满栏覆盖、重复/较弱/旧版本/旧租约拒绝；同键意图冲突、历史回执与当前列表区分；真实DB中断及外层失败/缺钱包回滚；保护、绑定、短包拒绝；喂养后技能保持、重开；旧宠不自动生成、显式初始化不重置、他人/放生拒绝。原pet_growth、care、presentation、native_commands、consumables、inventory/transactions、cash、同事务快照回归通过；任务宠物XP接口继续用完整PetState.__dict__保持skills。

未完成：共享RoleOwner c07ff上下文路由/0..9999服务器draw/可信时间生命周期、现场部署和GUI；到期定时刷新/内容渠道/专用提示、学习通知与动画；技能被动属性、主动技能与战斗效果；血脉升级/进化和特殊技能渠道。进度保底/失败规则的设计来源已明示，不能称原服公式。当前落盘与同步不等于战斗生效，也不作为完整宠物系统完成。

## 部署交接状态

首批技能源在主集成的短暂部署冻结通知前完成；冻结期间仅继续只读/文档。主策划通知PID8724从不可变063445Z发布启动后，已解除所属模块冻结并完成后续绑定批次（PET_BINDING_INTEGRATION.md）。新源码不会自动进入该发布；共享Adapter路由与部署仍交集成方统一处理。

## 冻结期原生字段补证

宠物绑定位及原客户端缓存见`PET_BINDING_RESEARCH.md`、`pet-binding-native.json`；256种字节值通过原codec→原转换投影→原绑定查询，bit1确定。原标记刷新不更新绑定缓存，后续绑定学习回复需采用已证实能重建状态的完整栏同步，或另证明专用刷新路径。

**语义纠正：**内部pet+4c/网络Pet+c4是绝对到期值map；初批14组原UI比较见pet-skill-expiry-native.json，后续九组SGameTime/原除法/匹配CRT与图标边界确认Unix毫秒，见pet-skill-clock-expiry-native.json。原服具体道具时长仍未知；领域存档和有效快照当前见PET_SKILL_EXPIRY_DECISION.md，认证/进度见PET_SKILL_LEARNING_DECISION.md。

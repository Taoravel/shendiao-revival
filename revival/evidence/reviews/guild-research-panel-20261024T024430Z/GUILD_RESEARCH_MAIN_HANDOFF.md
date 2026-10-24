# 帮派研究成长接入

读取条件：整合guild_research、启用研究曲线或消费正常维护研究奖励前。当前准确固定候选查guild-research-current-review.json；这份交单只交成长结算核心，仍未启用生产研究、NPC或完整组织玩法。

## 可直接复用的Interface

- OrganizationStore(path, organizations_policy, research_policy=explicit_recipe)：显式recipe含revision、origin及14技能各自完整升级阈值；索引0是0升1，序列长度为该技能当前cap。配置复制为冻结tuple并按内容/版本/来源计算digest，不依赖调用方可变dict。
- 新建帮派事务在显式配置下同时初始化14项0级/0经验；默认None不建状态，旧帮派读取/启动不回填。不把隔离验证10/20/30阈值作为生产值；不默认采纳来源报告里的设计候选。
- guild_research.award(db, ResearchAward, now, rules)：正常维护生产者在同一个帮派所有者、同一个已打开事务中证明/记录源事件后调用，可把研究与维护资金/时钟/凭据共同提交。此函数不验证维护资格或计算研究力，不能直接暴露给线包、NPC或运营任意加经验输入。
- OrganizationStore.award_guild_research / OrganizationRuntime.award_guild_research：用于已有可信源的消费，运行调用与该帮派管理共享既有organization键。单独存储事务不自动具备另一个源的原子性；跨Owner/跨库需先实现源outbox、消费inbox与恢复，不用稳定字符串代替源证明。
- guild_research_snapshot返回冻结14项等级、cap、经验、下一需求和当前选择；native_skills投影为GuildSkill(id,(level,cap,xp,need))，只生成已知研究列表，不填完整GuildDetails其余未知字段。

同事件键重放保留原选择/原结果；新事件可作用于新的研究选择。多级消费、余数保留、满级0经验/丢弃超额、0选择/0增量/已满级不增加revision为本模块明确designed结算语义。旧recipe改变不覆盖存档；既有凭据仍按历史读取。真实家族最后解散导致guild pending后，新研究奖励拒绝，旧凭据可重读。无角色资产、钱包或其他Owner写入。

## 正式启用还必须完成

主策划根据GUILD_RESEARCH_GROWTH_SOURCES.md制定生产阈值、初始研究等级/上限及练功房研究力关系。155仅为本模块有界曲线预算，原官网140/包内学习知识155不能推成统一研究cap。没有修改共用recovery-baseline或任何生产数值政策。

正常帮派维护Module须真实实现资金不足48倍仅基本维护、不增加研究经验，以及练功房对研究力的影响。原客户端证明了机制/关联，具体量和比较先后仍须明确裁定。由该唯一写者提交稳定维护事件和已计算增量，使用同事务award；当前尚无这个生产者。未知旧帮派的明确迁移也单独交单，不能只给构造传recipe就自动补历史。

研究刷新另已查到原SRefreshFactionSkillData 0xc563a，selected i32 + list<FactionSkill>，原0x149a410同步写manager+324和+318。当前下一批checkpoint见guild-research-refresh-checkpoint.json，完整原handler在关闭GUI实例的隔离环境执行；尚未加入本批固定源/审查，也未提供服务器查询/NPC路由。它能单独刷新研究列表，后续无需为了研究界面而伪造完整GuildDetails的未知字段。

实际组织成员/副帮主授权、完整地图地址/代次、NPC新证明与共享注册仍由main统一接线；原始game_runtime/runtime_storage/accounts/serve/gateway本批未编辑。用户此前不打开游戏的指令继续执行，无部署、真实角色数据或服务操作。完整目标保持active。

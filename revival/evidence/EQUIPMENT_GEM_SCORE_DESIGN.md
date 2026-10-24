# 普通宝石评分：独立设计候选与明确基准

接宝石score/color写入、导入镶嵌前评分或变更评分政策前读本文。2026-10-24。此候选补上上一foundation的明确评分策略与基准来源，**没有接生产写入、收费、人物投影或共享入口**；全量目标仍包括这些完整闭包。本批不修改此前固定七生产文件。

## 为什么是设计值

`GEM_SOCKET_SOURCE_MAPPING_RESEARCH.md`实际证明：原详情保留有序gem list并聚合独立effects，不会因列表改变自动重算score；原cequipscoreconfig七处直接消费者属于强化下一阶段预览。因此普通宝石原服评分仍unknown，不能把400或420当作已证系数。

唯一参数`design/equipment-gem-score-v1.json`，source_status明确designed local candidate。采用所有14族同等级等分：1..15级依次50/55/60/65/70/75/80/85/90/95/100/105/110/115/120。首级50、每级+5均是本地平衡选择；统一等级评分让未闭合单位的五行吸收/治疗量原数值不直接混入外攻/HP权重。不修改任何原gem effect或其战斗语义，不将原吸收3等数值删除、转单位或当评分来源。

颜色仍使用原cequipeffect.scorecolor阈值与cequipprefixconfig.bestcolortype。公式为：**当前score=已知镶嵌前plain_score+当前有序列表各宝石的设计分数之和**。每次重算，不按旧总分反推基准，不累计加差导致漂移。后续原公式若找到，需新policy和明确历史基准迁移；不能静默用新公式解释旧记录。

## 纯Interface与持久来源

启动`GemScoreRules.load()`一次，严格冻结.1的15档参数。`GemScoreBasis(role_id,item_key,policy,plain_score,source_ref)`是调用方可信完整基准，分数非负signed32，来源非空；一个客户端key或已有总分不授权该来源。

`project(score_rules,gem_rules,current_item,old_gem_state,next_gem_state,basis)`要求同角色实例、当前score等于显式基准+旧gem分、当前color与独立score/prefix一致、宝石状态恰好下一版本。返回`GemScoreChange`的当前/下一ItemState、基准、旧/新贡献；只改detail.score及必要的condition.color_tier，变色时condition.version+1，保留当前/最大耐久、prefix、identified、基础属性和全部物品字段。它不检验/授予镶嵌材料、现金、孔位或战斗权限；先由实际embed/remove计划校验资格。

分数溢出或输入基准/当前分/颜色/角色/版本不一致时明确拒绝。空列表贡献0；摘光回到可信plain_score。等阶不同类型替换保持相同分，颜色不变则condition版本不变；库存/gem版本仍由真实列表CAS另管。不得把GemScoreChange当成已保存或已扣费的凭据。

`equipment_gem_score_storage.prepare(db)`只启动建表，基准表归角色Owner唯一写入。`initialize(...,basis,'explicit_known_pre_gem_score')`要求已知完整socket profile和当前租约，并用纯no-change投影检查显式给定的基准解释当前score/color；它不保存所构造的下一gem状态。来源唯一且不可重置，同一基准重入只读返回。缺基准读None，不尝试以总分减估计贡献补档。

基准导入只保存不可变元数据，不改当前显示score、gem列表、库存revision或人物属性；之前没有基准的动作不能已受理，完整动作应固定此基准及所有现有来源。删除或模板/归属变更清理本Module基准，避免旧来源被另一资产复用。普通slot移动和耐久变化保留基准。未来强化/精练/随机附加结果改变非宝石评分时，须由完整新评分来源迁移；.1不提供覆盖baseline的通用写口。

## 可重复验证与未完成工作

`verify_equipment_gem_score.py`使用明确plain250、40100原第一阈值292：加一级石的设计50→总300/green2，原完整详情parser实际读到300/color2/独立81=12；当前耐久42/80保留。移除→250/white1、色版本继续推进；同阶替换不变色/不改耐久版本。另测贡献225/170、错基准/旧版本/错颜色/外物/溢出拒绝。

`verify_equipment_gem_score_storage.py`使用真实临时SQLite：缺档None、完整明确基准落盘、真实INSERT失败与外层失败回滚、错来源/重置拒绝、SQL禁止DML下已知基准重入/读取、重登与旧epoch围栏。没有读取或修改真实角色。

仍未完成：score/color公开同事务资产writer、实际cash/material/tool/receipt controller、完整有序附加triples与强化评分、root完整gem角色投影和HP/MP过渡、登录/重连/共享投递/发布/真实GUI。现有equipment_condition.reconcile_color仅为实验v1迁移，不能借用为本候选变色；新策略也不自动激活role-equipment v1/v2遗漏gem的旧路径。

方法：TDD在纯计划/原native和角色调用方持久化接缝完成缺模块red→green；codebase-design把可替换评分与不可变基准来源集中，复用完整socket快照和公共纯投影，未复制现金或资源权威；research决定本参数必须标designed；writing-for-agents共置准入、拒绝、迁移和完成条件；固定新增片按code-review双轴审查，报告与实际检查以本批记录为准。

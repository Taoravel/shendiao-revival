# AI8027 下一配方：Spec 独立静态审查

Missing/partial：0；Extra：0；Wrong：0。仅设计，不是当前AI8001发布门。

来源审计:13–24、30–47的十条原边、AI8027、NPC10908/1501、255XP/600SMoney、Animation0，与policy:18–38、81–82一致；101004未因同AI扩入。enemy29105原身份与设计双敌/站位/60HP等在:8–16、41–47明确分开，未把DisplayNPC三项当敌数或MonsterNum0当自动赢。

来源:89–145只证100008身份、两目标文案、等级相关MP及原消息能力，未给公式。policy:55–71明确采用设计：入场level1..155，成本2+L（3..157）、伤害20+5L（25..795），忽略物防、防御向下减半且至少1、逐目标裁剪剩余HP；主目标保留再选最低另一活敌，最多2且去重；主目标/角色先失活取消无耗蓝，不足MP拒绝且可另选，单次执行只扣一次MP。上下界及失败规则可判定，无内部矛盾。

first-skill政策:27–37要求完整已学账本和独立战斗授权；新policy:38、73不重授、不清map。RECOVERY_DECISION:7–13要求原件/epoch不改与原子consumer；新policy:78–84要求完整CAS、独立复活permit、迟错回滚，按原admission选择恢复配方、保留8001旧recipe，未知留pending；原CG只下一active，不伪造完成。

方法：沿用完整code-review/codebase-design，需求逐项对照来源，以Interface前提检查目标选择、数值范围、终态和配方升级恢复。非Git，冻结新文件与candidate.patch比较；未读另一轴。

审前后2source+9inputs+3external全部SHA匹配。manifest=95d195c9c4bb7c9755ef9f4ab695e9bc9a7825fbf9e624f4b7724905d3211569；patch=ca4daf0efa21ad8a2ad086332fc91ba562bc599010bdfb240b09ae3da3efc910。policy=7bbef4665a11366718fee6c2d465902286fa0b7f7adec1e138fac84f2e65ba59；decision=de7dc6b84d7a112faf08d3abde39e98d032d9c59596c9b4ac54112f35d947fa4。

未验：仅读取冻结来源记录，未重新提取PFS或执行native、测试、DB、socket、服务、战斗、GUI；未验证本配方实现/真人状态/发布，未改变当前AI8001门槛。

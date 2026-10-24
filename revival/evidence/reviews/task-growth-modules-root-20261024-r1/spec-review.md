# 限定 Task Module 组合：Spec 独立审查

Missing/partial：0；Extra：0；Wrong：0。以 repair023920 为实际BASE，固定选定五文件；非Git，无提交列表。

- task-pve政策:20–26要求真实当前私有地址/原任务/NPC/版本。task_first_battle:55–95冻结原43路线与十节点、原10908/placement10；:98–165核章节/门派/前驱、唯一active、确切持久checkpoint/实例目录、当前NPC证明和票据世代后调用generic admission。新task_battle:267–316仍核Participant版本、当前租约、能力、请求与同ID指纹，接口组合相容。
- first-skill政策:22、27–36要求真实前驱、完整已知账本、同事务及当前重试。task_first_skill:136–168使用新task_battle:236–264只读历史胜利证明；其局部registry默认关闭不阻止读取既有证明。:245–258已付只读当前技能/XP/profile，无grant或state1；:259–281首次CAS授予/120XP/唯一原后继。role_skills:118–202拒绝未知/部分/错误来源、保留全部合法key及高值并发完整map。新designed旧角色基线未混入。
- RECOVERY_DECISION:7–13要求保留原终态/epoch，当前独占租约受限恢复、漂移pending、已付只读。task_battle:372–398保留普通旧epoch拒绝；:476–516独立恢复验证原admission/terminal与当前witness，未改原event；:431–473已付当前查询不重新奖励或续链。恢复后的原Task receipt仍可供首技前驱查询。

方法：重读code-review/codebase-design及ARCHITECTURE/DESIGN；按Interface、所有权、事务和前后状态逐项追踪。沿用已审政策结论，重新读五文件组合；未读另一轴。读取根方5+8+6组绿证据，未自行运行。

五文件SHA256审前后匹配：

- task_first_battle b5557bd04227018b7d706849091373a0915c446b62cdb3e45ade7835036b51ad
- role_skills 7985e132239bffcda1c19fce63b3af724d3b48e1e92395f590a530b7e6038daf
- task_first_skill 40a15f95b47bf25088a2abff63aa84b246c612d5b91e76fdb50043bb71f0fcdb
- task_domain 11f93e8efbaf6059e6b51779691c310912bda5143fe630a0e625c5cadedf6c0b
- task_battle 8a78b9da2ce1cd144035c0b176c5485ef561d75afaa0ddf1bb033bdb6740d3f8

未验：人工terminal、numericParticipant及Witness/hash仅契约输入，不能证明实际producer、完整source CAS、资源/revive/outbox同事务接通；后者由调用方负责。无测试/DB/socket/服务/GUI操作，无真人资格、shared或发布验收，不宣称完整成长已通。

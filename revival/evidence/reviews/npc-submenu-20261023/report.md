# NPC子菜单增量审查

固定点为用户刚部署的npc-20261023T102110Z/source，当前四文件与其逐字节/difflib比较。项目无Git元数据，固定发布哈希替代Git ref/commit；manifest.json保留基线及最终当前值，initial/及initial-manifest.json保留首次审查状态。需求来源为NPC_SUBMENU_INTEGRATION.md；规范来源为AGENTS、ARCHITECTURE、DESIGN_AUTHORITY及code-review的Fowler基线。两个独立后台审查分别检查Standards与Spec，没有将两轴混合评级。

## Standards

硬标准违背0项，Fowler味道问题0项。菜单展开与授权校验集中在启动阶段NpcServices；显示根没有加入实际服务bindings，未引入shared改写、热路径配置读取、额外状态写入或跨所有者可变引用。NPC→295设计关联与客户端证据范围分别记录。Spec修复后再次只读复核，仍0项。

## Spec

初次发现1项P2：已绑定中间父项未拒绝。树1→2→3、绑定2/3、展示根1时，启动成功且父2仍可执行，与“父菜单不作为服务器命令”冲突。当前295直接三叶结构不受影响，但通用展示树的校验不完整。

新增公开构造用例后，旧实现对中间父2和返回10001明确失败；修复将所有已遍历本地节点（含根、中间父、返回）同NPC动作绑定统一拒绝，原六项单测转绿。Spec代理独立重跑六项并复核，剩余0项。测试随后扩展到两个原训练师，实际Owner各自通过相同既有断言。

Standards最终0项；Spec初1项已修复、最终0项。两轴审查均为静态/公开接口范围，不冒称GUI、部署或全NPC玩法验收。

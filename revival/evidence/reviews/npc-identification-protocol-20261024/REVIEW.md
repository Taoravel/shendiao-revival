# NPC鉴定纯协议固定审查

固定范围为manifest.json及changes.diff两个真实新增文件，base为空；四个原始字节SHA在两轴分别核实。需求依据是冻结原生研究、原JSON及模型交单；协议保真不等于服务权限或资产配方。

## Standards

硬规则违背0项，Fowler判断性问题0项。完整独立报告见[standards.md](standards.md)。优先导入冻结current的六组原生协议检查通过；有界解析、冻结命令、无文件I/O及无新增执行器符合当前仓库约束。

## Spec

需求缺失0项，额外范围0项，错误实现0项。完整独立报告见[spec.md](spec.md)。四个SHA一致，独立六组含原codec oracle通过。向量保留顺序和重复，NPCkey保留64位，signed32边界及回复key>0与原codec一致，辅助字段语义未擅自命名。

两轴分别0项，各轴均无最严重问题。仅确认纯协议实现；495领域查询、NPC绑定、当前租约与物品版本复验、费用/鉴定结果、共享路由、发布和GUI仍分别待验。方法为code-review分轴后聚合、tdd三个公开缺入口实际红→绿、research以原codec为独立oracle及codebase-design隔开wire数据与业务权限。没有改资产或现场进程。

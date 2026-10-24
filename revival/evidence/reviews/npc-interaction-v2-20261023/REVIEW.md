# NPC离散格交互固定审查

固定范围与原始字节SHA以manifest.json为准：四个已有文件对比已审v1冻结快照；verify_npc_cell_interaction.py新增；audit_npc_service_integration.py在36632固定发布中不存在，按完整新增文件审查。共六文件、十二个base/current SHA，不以工作区实时内容代替固定审查对象。政策依据为本目录冻结v2政策、主策划决定及兼容性研究。

## Standards

硬规则违背0项；Fowler判断性问题0项。独立审查完整结果见[standards.md](standards.md)。审查者核对十二个SHA并优先导入冻结current，v2八组、显式v1八组及既有Scene/Lifecycle回归通过。共用allows承载离散判据，启动冻结与热命令分开，现有地图/角色当前性检查保留。

## Spec

需求缺失0项；额外范围0项；错误实现0项。独立审查完整结果见[spec.md](spec.md)。同样核对十二个SHA并独立执行上述检查。严格16/13/169、三段位置、无摆放例外、非208像素圆、v2拒绝radius_for及原三点访问包证据均已覆盖。

两轴分别0项；各轴均无最严重问题。以上仅为固定领域与验证代码结论，未证明共享自然链、固定候选发布、GUI、原完整自动接近或商业容量。普通NPC碰撞/区域底层原生研究仍含明确Adapter。

方法与产物：code-review两轴独立后聚合；codebase-design审核共用公开Interface；tdd保留实际红例并复查公开Seam的转绿与拒绝行为。生产最小输入、共享接线和未激活Lifecycle分别见../../npc-interaction-v2-ready.json。未操作真人库或服务进程。

# Spec 审查：真实地图成员绑定设计 v1

固定范围 `reviews/world-role-binding-design-v1`，manifest SHA256 `b72d986e242c35bd73665a4a538a3f653af7d91507eea8de86c178662e590a19`。核对3份final、25份reference哈希全部匹配；3份是真新增，无Git/提交，以changes.diff和SPEC七项为基线。沿用本会话已完整读取的code-review、codebase-design及AGENTS/ARCHITECTURE/DESIGN_AUTHORITY。

## 发现

**[P2] fence必须捕获预期成员身份，不能仅捕获Location。**

`final/evidence/WORLD_ROLE_BINDING_INTERFACE_DESIGN.md:39–46` 设计 `fence_role_binding(expected: Location, view: RoleScene)`，只要求domain/view精确位置匹配，然后推进当前成员revision。SPEC第4/5项要求陈旧清理不能影响新状态，设计第81行也要求陈旧expected拒绝，但此参数不足以区别同epoch同Location的重新加入。

以哈希与reference相同的现有纯Module，执行公开join_with_view→leave_with_view→以相同Location再次join_with_view：Location（含地址/epoch/version/坐标）完全相同、view对象相同，真实membership_revision由1变3。旧排队fence携带的两项参数仍全部匹配，却会撤销新成员；此为设计参数缺口，不声称尚未实现的fence已执行或当前发布发生了该故障。

建议fence接收并验证完整expected RolePresence，或captured RoleViewBinding加精确Location；在地图执行者比较owner_generation、membership_revision与当前presence，不能到处理时取新snapshot为旧请求补身份。随后才推进revision。补对应同Location新成员反例到设计验收。

## 其余范围与限制

未发现其他明确Spec偏差：七观察明确只证既有契约；metadata工厂/收费/完整AOI均声明未实现；freeze旧view与domain权威分开；r4四项独立检查、main全302只读核验及35568→12512的OS证据没有混用，GUI保持未验。

本次只读静态审查及上述单项纯内存反例；未重跑长302、修改final/生产、操作服务/GUI或访问真实库。**Spec开放1项P2。**

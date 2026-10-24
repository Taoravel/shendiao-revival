# Spec 复审：真实地图成员绑定设计 v2

固定 `reviews/world-role-binding-design-v2`，manifest SHA256 `309c9c93856ddef356bfc5aa5a0fdbbf79a5b535f7d08d6384fb2a2ceaffcf19`。3份final、27份reference哈希全部匹配。以v1新增文件基线及v2差异审查，保留v1初审，不虚构Git提交；沿用code-review/codebase-design与项目约束。

**原P2关闭，新增0项可行动Spec问题。**

两个提案Interface均改为接收投递前已捕获的完整RolePresence，执行时精确比较当前view.snapshot身份与domain expected.location，不再按roleID或相同Location替旧请求补身份。该比较含owner generation、membership revision及完整位置，足以区分v1提出的同epoch、同Location重新加入反例；fence只在验证后推进真实revision。

冻结witness报告已扩至9项，全部true且输入稳定；报告绑定最终脚本及5份依赖源码哈希，与final/reference逐一一致。新增两项实际观察证明Location-only会别名、新captured presence可区分；没有声称执行尚未实现的role_binding/fence方法。

metadata-only/None外观、普通移动稳定、冻结权威复核、取消恢复、新连接及send前身份/流程围栏仍为明确设计与实施验收要求，未误称已实现、已收费或已启AOI。r4独立/只读全302/启动与OS证据的范围未改变；GUI与全量目标继续未完成。

本次只读静态diff、manifest和报告绑定核对，未重跑长测、修改final/生产或操作服务／GUI。Spec当前开放0项。

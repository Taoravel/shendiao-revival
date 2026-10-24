# NPC共享成员绑定接缝提案

后续正式裁定已到：以MEMBER_BINDING_DECISION.md及reviews/member-binding-decision-root-20261024-r2/acceptance-root.json为准（root接受设计，不是上线许可）。本提案下文仅保留此前分析；实际采用Domain固定metadata projection、物理generation一致性、普通移动许可稳定而显式fence推进许可、freeze前fence及resume沿新许可、连接CAS与真实撤销屏障。此前“source freeze/resume保留同一身份”的提案不能解释成恢复fence前旧许可。继续保持已封9b05类型/数据，等World冻结和main准确共享候选；本文不签发任何许可。

2026-10-24，NPC窗口；状态`proposal_only`，待root/World/main确认实际Interface。本文不授权发布、不改任何生产/政策或已封鉴定ready。接线顺序保持普通repair独立片后，再成员绑定，再鉴定。

## 现有来源与需要隐藏的复杂度

`npc_equipment_identification.query/confirm`已经按正式政策接受完整RoleViewBinding；确认要求与成功查询的binding一致。它只消费可信快照，不查询实际地图或自行维护成员。当前game_runtime.MapOwner仍用NpcScene/positions，尚未安装RoleScene或RoleViewBinding；公开SceneFence的公共地图generation为None，scene_token是字符串，不能直接冒充成员revision。

`world_owner.MapOwner`已经独占`_roles`和真实`_generation`，公开inspect_lifecycle可读世代；join/leave之外，activate建立loading成员，ready转active，freeze/resume更新同一成员位置，retire_transfer/finalize执行按精确回执清理。仅在普通join里加计数会漏目标activate。根约束是由这个现有Module补实际成员快照，而不是再建第二套世界位置/成员权威或全服排队器。

## 建议的Interface语义

在所属WorldDomain单次邮箱执行中，按当前role/opaque epoch校验真实成员，返回冻结的完整address、owner_generation、role_id、login_epoch、membership_revision；角色所有者再结合真实当前ConnectionOwner.generation构造既有RoleViewBinding。具体函数名由World单写方确定。NPC证明及成员快照最好在同一次MapOwner命令取得，Location/当前实体/距离仍用既有真实interact。

member revision是同一MapOwner generation内单调分配的成员身份；只保留当前成员及一个有界整数分配器，不保留无界历史。重复相同join返回原身份，真实离开后重入获新身份；新owner换generation后可以重置本地计数。移动不更换成员身份；target activate的loading成员分配新身份，ready沿用。source freeze/resume保留同一身份但期间不可取得active NPC许可。过期disconnect/finalize/resume/retire只能清理它们原本绑定的成员，不能影响新租约或重入的成员。

计数耗尽/容量/错误回执必须在状态变更前拒绝；失败不消耗已接受身份。以实际Location.version、connection generation、UUID转整数或常量1填membership_revision都不符合这个语义。保持各地图/实例/分区独立推进，不为它添加全服计数锁。

RoleViewBinding在本批只是既有冻结数据合同，不要构造假RolePresence/RoleBasic或启动一个丢弃输出的RoleScene来获得它。WorldDomain generation与RoleScene自己的projection generation目前各有来源；root需确认NPC使用真实物理地图成员语义，并明确未来玩家投影如何保持兼容，不能混用两份generation。若root选择其它正式类型，需另版审查NPC领域变化，不能修改已封9b05 ready冒称原审覆盖。

## 发送与撤权

实际join/transfer/ready/disconnect的提交结果通过可信角色/连接事件安装或撤销当前绑定。ConnectionOwner在真正编码/发送前复核完整address、地图世代、成员身份、opaque epoch和connection generation，复用现有scene_token门控。不能只在入队时检查，也不能让客户端包或待投递消息自行安装绑定。

移动、别的菜单、战斗、transfer/loading、断线和连接替换按已批准鉴定合同清除未付ticket；就算成员身份不变，原Location或对话状态变化仍撤销未付许可。已受理资产结算按稳定request_id及当前租约合同处理；付费重放只读当前，不由后续NPC删除回滚已付资产。地图邮箱外有界编排存储和目标投递，不持地图/数据库事务等待其他Owner。

## 完成判据

| 情景 | 必须观察到的实际行为 |
| --- | --- |
| 同成员移动 | revision稳定，Location.version推进；旧未付对话撤销 |
| 同epoch真实leave再join | 新revision；旧ticket和延迟消息都拒绝 |
| 新opaque epoch/连接替换 | 旧回调不能移除或投递到新成员 |
| 跨完整MapAddress传送 | 目标loading身份与ready一致；旧源及旧场景投递拒绝 |
| source取消恢复 | 仍为原source成员，过期resume不覆盖后续新成员 |
| 旧finalize/retire重放 | 已接受旧清理可幂等，新成员/新MapOwner保留 |
| owner卸载重建 | 新generation使旧绑定失效，即使本地revision相等 |
| 发送延迟/积压 | 阻塞真正发送边界后改变成员/连接，释放时旧消息被挡；另一Owner仍推进 |

在准确冻结候选公开WorldDomain/实际MapOwner和加密Peer Seam上完成这些反馈，再接原495/C04cc/C4276，而不是用补一个字段或pure dataclass通过代替共享接入。GUI、商业容量和跨进程部署仍另验。

方法：codebase-design把成员权威留在现有深WorldDomain Module，Interface提供冻结身份并隐藏全部创建/清理路径；tdd沿既定真实Owner/投递Seam逐个纵切，不提前编造共享实现或批量mock；writing-for-agents把提案状态、来源差异、全部生命周期分支与可判定完成标准放在同页。本文只有静态源检查，未宣称实现或执行这些未来检查。

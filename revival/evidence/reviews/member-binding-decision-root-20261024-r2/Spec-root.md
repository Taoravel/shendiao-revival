# Spec 独立复审 r2

缺失/部分0、额外行为0、错误0。r1 P2已闭合，原报告保留；本结论不批准runtime或部署。

冻结 `ARCHITECTURE.md:33`要求“预留目标→冻结源移动→切换带版本的归属→确认后清源”。r2裁定L17把绕过配套命令的禁令限定为已列六种操作，并明确“freeze仍使用原Domain命令：先精确fence旧许可，再冻结源位置”，原freeze不再被误禁。冻结时投影只保留最后active快照，Domain frozen拒签，故快照不冒充active授权；取消由resume_with_view更新位置并保留fence后的新许可世代，成功由finalize_with_view精确清源，无需另造freeze_with_view。

与准确已批准BASE交叉亦可实施：`world_owner.py:645–666`保留原freeze/receipt；其L722–725及L788–791本就要求投影维持offer.source的active快照，分别在finalize/恢复时清理或移动。修正文义既保留该协议，又配合裁定L19/L21的active+captured presence校验阻止冻结前许可复活；没有授予旧snapshot或历史callback新权限。

除L3状态标注r2和L17冻结例外外无新变更；其余术语、实际Domain generation/唯一metadata投影、MOVE许可稳定、连接CAS及入队/编码前校验、真实屏障与无全服锁要求沿用r1完整审阅。AOI、鉴定收费、资产扩展仍未获本批授权，L39继续明确纯模块成功不代表shared接入。

方法：沿用已完整读取的code-review/codebase-design/domain-modeling，以“先fence→freeze→cancel/resume或finalize”具体场景区分物理成员、投影快照与许可世代，再核原公开协议。非Git，以固定r1为BASE；四source SHA及实际diff SHA均匹配scope，前后重复核对稳定。scope SHA `49863a6320bc2ba03c5e3e79c6acabc98301f2ec10c57a6adbeea6ee854553f9`，新裁定SHA `482be66d276a7ae6b647dc83726dc225538940dec0918ed11e5ec053cf455d29`。

仅静态读取；未运行模块/共享测试、DB、socket、服务、GUI或战斗，未读另一轴。成员实现、连接投递及运行验收仍待独立冻结候选。

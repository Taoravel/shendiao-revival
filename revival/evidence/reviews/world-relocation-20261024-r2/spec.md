# Spec review: relocation membership and retired-request fences

2026-10-24。按 `code-review` 的 Spec 轴，以真实保存的 r2 before `b38aacb…`→after `a454134…` 执行 `git diff --no-index`，并核对更新后的 `after/WORLD_RELOCATION_DOMAIN_HANDOFF.md`。旧 r1 封存、P2报告和四例失败反例均保留，本报告另置。

## Findings

**原 P2 已关闭；新增 open findings: 0。**

成员普通退出、跨图清源、旧交接恢复清理及重定位提交替换源成员时，将该角色/租约的旧终态记录标为 detached。记录继续占用原预算，仍可用原终态 receipt 精确退休，commit/cancel 执行路径却不再将其当成功幂等回执，因此同值成员重入不会复活旧证明。pending不因该清理或退休消失，既有唯一冻结源及loading/ready边界保持。

另一个已退休请求重建问题由每次实际新freeze的 `preparation_id` 解决：pending重试保留原prepared，真正新接受的同请求/源位置生成新身份。旧proof与新pending的精确匹配失败；终态显式退休也不能误删同transfer_id下的新决定。此身份是操作证明，未被用来创建假地图实例或扩充住宅目标政策。

## Independent verification

执行前后核验工作区与冻结 after 的 owner SHA均为 `a454134ec3d274e5c6203b66adea9364f10a42563bf7fbdc2c83ed1865a693ac`；验证脚本均为 `eedf6c8c1c4ba600104bf425c9992b4786d856991ba2ce2bf349410919536f3e`，其全部声明依赖前后稳定。

独立重放原 commit/cancel × bare/paired 四种同值 leave→join 反例：旧proof全部拒绝，当前权威不变，detached原receipt仍可退休。再独立执行最终验证脚本的全部10组函数，包括 `retired_request_aba_case`、pending精确重试、预算/闲置、AOI容量失败及热路径检查，全部通过。结构化结果为 `spec-independent-r2-observations.json`；没有覆盖或改写主验证报告。

本轴未独立执行最终5项旧回归，待父任务按该准确最终源验收。SQL事务、故障/新租约恢复、真实发送屏障、共享接线、入口政策、native完整流程及GUI依然未完成；结论只覆盖所属领域能力与本次证明围栏，不构成运行时发布验收。仅新增本轴报告/观察证据，未改源、冻结文件或服务。

Spec findings: **0 open**。

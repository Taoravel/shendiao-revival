# 普通NPC绑银候选审查

固定点、五文件diff及原始字节SHA256见manifest.json与changes.diff。三新增文件基线为空；NpcGamePlay基线为本次菜单ready冻结，旧商店verifier基线为wild固定source。

## Standards

硬违规0项，Fowler判断问题0项。固定两个新verifier共13条结果和字节哈希通过，见standards.md。

## Spec

缺失0项、额外范围0项、错误实现0项。独立通过两新verifier与旧商店回归，包括真实历史mode0 receipt兼容和source/资产晚期回滚，见spec.md。

两轴最终各0项。仅staged候选；合入、固定发布与GUI另验，不能从审查结论推定已开放运行服绑银购买。

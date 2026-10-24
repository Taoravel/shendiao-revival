# Spec review

结论：0 个发现（P0/P1/P2/P3 均为 0）。仅针对本目录固定候选，无 Git 提交；比较 `since-approved-scope.diff` 与 `since-36632.diff`。规范来源为 `revival/evidence/PRIVATE_SCENE_SCOPE_DECISION.md`，重点为“延迟投递与连接队列”。

已核对候选四文件、规范与记录的 SHA-256 一致；`results/import-closure.json` 所列导入文件当前哈希也一致，未导入未审工作区代码。

规范要求“新增可选仅关键字字段，默认None，保持原四位置参数及GuildWake/FamilyWake/GroupDelivery等继承构造兼容”。`Delivery` 使用冻结 dataclass 的 keyword-only 字段；严格拒绝 bool、可变容器、错误长度/类型、非正 map/instance、负 partition 及 signed63 越界，显式公共 tuple 归一为 int。原四参数及五类继承构造保持兼容。

规范要求“带key先与当前snapshot.scene_key比对……经原收件人关系检查，再调用共享异步Interface”。实现先拒绝旧范围，再保留群组/组织授权和角色关系过滤，随后仅 await `offer_scene_channel`。范围不符、hook 缺失及显式拒绝均计数且不回落 `target.offer`；None 保持原路径。转换投递保留原 scene_key，不会因转换丢失范围。

现有固定结果覆盖迟到旧实例拒绝、相同 key 交 hook、公共归一、缺失/拒绝 hook、持久化黑名单、epoch、None 世界/门派及继承构造（8 组）；原 scope 6 组与六份基线回归结果齐全。本次审查阅读并核对这些现有结果，未重新运行测试。

范围无夹带：候选排除 `guild.initial` 和组织激活，未修改 shared。规范明确“共享另以受控慢drain……验证”；实际 fanout 填 key、ticket/pin、连接队列/drain 围栏、私有入场及 GUI 仍未验证，属于主集成后续验收，不由此候选声称完成。

方法：code-review 的独立 Spec 轴逐项比对；codebase-design 以冻结快照与投递 Interface 为检查 Seam；writing-for-agents 将固定输入、结论和未验证范围共置。

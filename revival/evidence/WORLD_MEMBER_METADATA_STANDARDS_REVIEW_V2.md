# Standards复审：成员metadata v2

固定范围：`reviews/world-member-metadata-implementation-v2`，manifest SHA256 `b60c9a36e8e3c7f6e76cc9a44aaf10154ace36af810210d228d1b29c239e3819`。2份base、6份final、56份reference及SPEC哈希全部匹配；v1与初审记录保持不变。

方法沿用code-review Standards轴：冻结AGENTS、ARCHITECTURE、DESIGN_AUTHORITY、GLOSSARY、ADR0001、成员许可裁定及完整Fowler基线，仓库规范优先于判断性异味。

硬规范违规0项；判断性代码异味0项。

相对v1生产变化仅为`WorldDomain.process_one`在取队列前检查配套成员模式。出队准入与实际位置变更各自保留验证，承担不同阶段的状态保护，未判为可行动Duplicated Code。未配置metadata的旧路径继续原语义；RoleScene源未变化，未增加锁、全服队列或额外位置权威。

新增公开submit/inspect/dequeue回归实证：错误消费者拒绝后已接纳命令仍在队列，正确配套消费者随后执行同一命令。报告明确保留旧红和修后绿；最终14组metadata、10份旧回归与原生字段验证的范围分别记录，未升格为共享接线或GUI验收。当前repair BASE的独立join红例仍清楚标为未修共享缺口。

本次仅静态diff、哈希及报告核对；未重跑测试、修改生产或操作服务、GUI、正式数据库。

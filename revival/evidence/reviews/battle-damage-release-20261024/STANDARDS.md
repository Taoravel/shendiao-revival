# Standards

BASE：npc-role-healing-20261023T125539Z；候选：battle-damage-20261023T180731Z。核对固定diff、manifest及两源SHA。

硬违例0；判断性smell 0。依据AGENTS、ARCHITECTURE及Fowler基线；无GLOSSARY/独立规范。TargetResult区分结果映射与DemoAttr，未改变所有权、执行或持久化路径。

部署脚本身份、输入哈希、停服后备份门槛未见错误。限制：Established仅是瞬时空服守卫，不保证检查后新连接不被断开；非阻断。

方法：code-review Standards；diagnosing-bugs用于证据隔离。静态审查，两候选及工作区源SHA前后不变；沿用冻结绿检。未启动客户端/监听、未触真人DB，未动态验证部署。元数据复制已置于检查前。
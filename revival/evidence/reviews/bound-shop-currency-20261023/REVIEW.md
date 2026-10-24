# 绑银普通购买：钱包用途增量评审

固定点：manifest.json记录的修改前currency.1；新增三文件的base为空。非Git工程，无提交列表。4文件141行diff.patch，root核当前工作文件及固定current哈希均一致。

## Standards

0项。独立报告STANDARDS.md；依据项目AGENTS/ARCHITECTURE与技能规范，含Fowler启发式。

## Spec

0项。独立报告SPEC.md；依据固定支付政策与客户端优先来源要求。

两轴均为静态检查。root另外实际验证：合法绑银300原用途拒绝的红反馈→仅增purpose后公开临时钱包绿，旧verify_currency必要回归绿。没有更改currency.py、旧钱包数据、NPC领域实现、共享路由或运行服；绑定产物/原子发物/GUI另验。

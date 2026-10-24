# 普通NPC绑银购买最小发布复核

固定点为实际44084的npc-close-master-commit-20261023T113819Z，candidate为npc-bound-shop-20261023T115742Z。非Git无提交列表，manifest锁4生产输入194行增量。root独立BASE1425/candidate1427全哈希匹配，恰好4变化且无删除，共享Module原字节保持。

## Standards

0项；独立STANDARDS.md。

## Spec

0项；独立SPEC.md。

root准确candidate source/config独立执行verify_npc_bound_shop_runtime/sources两项13组结果全绿：真实连续加密Owner、binding隔离、当前余额/重试/不足、source CAS与晚错/满包回滚、失败键再成功、实际旧mode0receipt兼容、mode1policy冲突。五实际生产Module.__file__精确落在candidate；harness哈希与candidate清单一致；每次后1427manifest未变。仅输出重定向工作evidence/root-candidate-bound-shop，无dispatcher/业务替换。

其余10条总检查与旧BASE真实红由主集成记录。未GUI、真人库、实际battle、启停或商业容量验收；此候选核对不等于已部署。

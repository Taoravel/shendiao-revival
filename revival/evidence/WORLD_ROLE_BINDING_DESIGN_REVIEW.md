# 真实成员绑定方案双轴复审

固定范围 `reviews/world-role-binding-design-v2`，manifest SHA309c9c93856ddef356bfc5aa5a0fdbbf79a5b535f7d08d6384fb2a2ceaffcf19；3份真正新增final、27份reference，/dev/null真实新文件基线，无Git或虚构commit。范围为Interface方案、现有公开契约witness、R4准确验收说明；没有生产/shared实现。

## Standards

硬规范违规0项，判断性代码异味0项。核3份final、27份reference及9项观察绑定6份源码；捕获RolePresence的契约保持单写位置权威与陈旧回调围栏。仅静态复审，未运行服务/GUI。独立记录WORLD_ROLE_BINDING_DESIGN_STANDARDS_REVIEW_V2，初审保留。

## Spec

原P2关闭，新增0项。v1只用Location作为expected，公开leave/rejoin可生成新member revision但相同epoch/version/位置，故旧fence可能撤销新成员。当前提案两命令都要求投递前捕获完整RolePresence，执行时精确比当前view及domain Location，不现场补新身份。公开witness新增两观察，现9项/6源码前后稳定；并未执行不存在的新方法。独立记录WORLD_ROLE_BINDING_DESIGN_SPEC_REVIEW_V2，初审P2保留。

两轴结果：Standards开放0，Spec开放0。可交main/root审阅具体接线方案；**尚未实现metadata-only工厂或两条地图命令，不可据此接入收费/发送或宣称多人AOI已恢复**。后续World所属实现与main共享接线仍各自需要准确代码、回归和新候选验收。

## 方法、证据与边界

codebase-design用于将真实成员来源及单一位置权威留在地图Module，并把连接入队/编码前的完整身份核验留在目标执行者；diagnosing-bugs的实际公开反例排除Location等同成员、pair_capacity0等同纯metadata的假设；code-review双轴独立核验设计与证据。

R4的旧finalize红→绿、earlyACK/wall/重连/清理与普通特殊子集为World独立执行。全部302/46项为独立核main准确报告；1442 source/445启动及OS实际发布归属已核。真实GUI、整个新手流程/怪物/战斗/玩家AOI与商业容量仍未验，目标active。

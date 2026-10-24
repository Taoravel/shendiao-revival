# 普通门户准确运行时联合验收

2026-10-24。不可变来源 `runtime/deployments/npc-repair-20261024T023920Z/source`，manifest SHA `b4ad84e07328110ecedaf753be126c4c19d3f58eadac2f0a700f1dea699eb367`。本批完成 **212个普通有向跨图组合的联合覆盖**；全量地图、场景、怪物和新手GUI目标仍未完成。

主记录：[world-portal-runtime-combined-acceptance.json](world-portal-runtime-combined-acceptance.json)。逐对绑定报告、原见证、脚本版本、manifest、原包及catalog SHA。不能称单次全绿。

## 两批实际结果

首批 `world-portal-runtime-repair-all212.json` 执行全部212组：199组完整通过；13组因原包没有对应 `npc.xml`，在目标NPC期望读取处抛KeyError，未执行完后续链。原报告保持 `all_passed=false`。脚本 SHA `c902399b21ddf36ce36987d41e56b097850b54e1d226b55f5136679755eac399`，固定于 `reviews/world-portal-runtime-20261024-r1` 及r2的before副本。

修正版按无歧义casefold查原NPC表，缺失时仍严格要求全部实际解码NPC记录为空，不跳过比较；有表记录原entry/SHA。对同13组分别新建临时DB重跑完整链，全部通过，见 `world-portal-runtime-repair-npc-resource-r2-remainder.json`。修正版 SHA `f3a0cb22a90a2a44d8dabd1195544b71c5c5da1386f14d96265552e2712d3dcd` 固定于 `reviews/world-portal-runtime-20261024-r2`，工作区入口现为相同字节。联合记录按pair及source_cell/approach/portal/target/target_step排重匹配，199+13=212。工作区后来更新脚本不改变先前真实执行的源，读取旧证据应按其冻结SHA。

独立原包门槛 [world-portal-source-binding-repair.json](world-portal-source-binding-repair.json) 核准确候选304张地图属性、142张goto表、6275原行逐项相等；保持行数只改目的坐标的反例实际被拒绝。旧研究140表漏了1412/1413目录大小写不同的各25行，已保存历史并修正，原227个有向组合不变。原行一致本身不证明原服目的坐标单位。

两批全部1442生产文件、manifest及原map/config整包前后稳定，联合验收又逐项重算相符。本批只改验证/研究，未改生产或运行服；账号、位置和显式实例采用全部限于临时DB。

## 每对完整链与夹具

1. 原portal附近可走起点建立明确离线检查点，以实际加密认证/登录进入源图；起点是fixture，不表示真人已沿完整路径抵达。
2. 从实际源Owner当前位置，在临时角色事务显式采用完整地图地址。实际MOVE/STOP触发交接及目标发送完成屏障，原生decoder核目标scene坐标和全部原NPC布置。
3. 目标同格合法一步，核公开落盘位置/版本与同事务完整实例地址；同runtime断线重登，再关闭runtime冷建重登，核地址、位置、版本和四字节心跳。发送完成不是客户端加载ACK。

每对独立DB，不覆盖上一对已采用实例。另有legacy两组诊断 `world-portal-runtime-repair-pilot-legacy-r3.json` 保持实例None，不冒称完整地址持久化。早期重登诊断还纠正了脚本发六字节心跳的错误，实际协议要求四字节；这是检查脚本修正，不是产品修复。

复验入口：`verify_world_portal_runtime.py --runtime-source <准确source> --runtime-harness <同候选harness> --report <新报告>`。不传 `--pairs` 时执行全部212；新结果另存，保留本次联合原报告。

## 特殊出口与剩余范围

15组特殊pair保持独立：9组原目标阻挡、4组住宅返回越界、2组同图入口。本批未混入212通过数。

纵向回放另核1301→1100、1305→1104：保持阻挡落点，原MOVE/CHECK/STOP逐字节进入准确加密运行时。首MOVE拒绝，后CHECK/STOP仍能走出并落盘，不能由首拒绝就判卡死，也不能称九组都已恢复。七组原输入夹具无移动报文，未补造回放。全部适配边界见 [WORLD_PORTAL_EXIT_SOURCE_RESEARCH.md](WORLD_PORTAL_EXIT_SOURCE_RESEARCH.md)。

[官方资料核对](WORLD_BLOCKED_EXIT_GUIDE_RESEARCH.md) 支持帮派空间独立及门派车夫流程，未给七组权威返回坐标。[位置字段研究](WORLD_MAP_POSITION_FIELDS_RESEARCH.md) 将playerPosX/Y追到Worldmap UI矩形，xjPos/yjPos最终导航消费者尚未闭合；均未建立出生/出口落点authority。仍按主策划明确来源与实例政策补全。

尚未验证全部6275格、自然寻路/完整轨迹、1302/1307缺图、NPC全部模型/方向/隐藏、正式怪物AI、玩家AOI、共享成员接线、商业容量及真正客户端黑幕/移动/新手全程。已有共享join撤销移动上下文红例仍见 `WORLD_RUNTIME_JOIN_CONTEXT_BLOCKER.md`，本批未改共享入口或借其他绿灯关闭它。

## 方法、审查与采用条件

diagnosing-bugs定位两类脚本错误并保留红结果，只完整重跑受影响13组；research绑定原PFS/原指令；code-review按Standards/Spec独立审查，r1原源绑定P2由142表全行门槛关闭，r2及两例纵向回放当前两轴均0；writing-for-agents将执行、来源及未验项共置。具体报告在上述r1/r2及 `reviews/world-portal-exit-source-20261024`。

共享集成可采用联合记录作为这212个普通代表的准确BASE证据。变更生产、原包或见证后，在新准确来源上验证受影响链，不能转签本结果。真实客户端和全部特殊实例合同仍是独立完成条件。

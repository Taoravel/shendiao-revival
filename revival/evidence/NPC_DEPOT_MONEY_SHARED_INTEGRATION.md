# 仓库存取款共享Owner接线

2026-10-23。原始集成窗口；依据CURRENCY_DECISION追加裁定及NPC_DEPOT_MONEY_INTEGRATION已交Interface。该源码未进入PID8724验收发布。

RoleOwner的NPC_DEPOT_TYPES统一转入既有depot_request。只有OPEN_DEPOT建立访问票据；钱请求须有未过期票据、16字节原NPCkey与当前票据一致，经地图重新核对真实实体/距离/地址和位置版本后，才调用npc_gameplay.depot_operation。该函数已有现金钱包、仓库现金、账本/审计与共用凭据同事务；共享入口只负责访问与命令身份，没有再写一份货币逻辑。

原verify_npc_depot_money_runtime在完整当前prepare、实际连续RC4/原MPPC→Owner路径上，开仓后存款返回{}而红；两处共享路由/绑定修正后原样全绿，主策划独立复跑。覆盖4294967303存入/4294967301取出两signed64余额、未开仓/错NPC拒绝、同受理命令仅一次、重新登录后必须重开且双余额保持。线包无request ID，新受理操作仍各自分配内部身份，不按同金额永久去重。

额外临时公开Interface审计在evidence/npc-depot-money-access-verification.json：过期票据拒绝，截断/尾随/零负金额不改双方100/100余额也不延长票据；实际STOP清访问；过期位置版本清票据并拒绝；loading/battle守卫哨兵拒绝且无交易。过期/版本/守卫使用明确受控夹具，STOP与钱请求经真实加密Owner；未执行战斗或真实换图，不将哨兵检查称作完整场景穿越。

方法：diagnosing-bugs以实际调用缺失返回的确定红→绿回路定位；codebase-design复用现有仓库授权/调用方事务Seam，原生解码及余额规则仍归NPC/货币Module；writing-for-agents共置打开、读取、提交与失效条件。产物为GameRuntime局部路由/原key核对、两份验证记录及本页。无全服锁、无新资产写者；config/schema依旧启动准备。

未验证：原客户端存取款弹窗/余额GUI与当前发布运行；完整仓库服务、跨角色交易、商业数据库/容量与异常关服恢复。没有部署、重启、操作GUI、改现场余额或角色。原NPC领域/原codec证据按其交接保留，不能据共享路由通过推定全NPC实机通过。

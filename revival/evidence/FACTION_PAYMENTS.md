# 组织费用：现金扣款、撤销与恢复

接家族创建、帮派创建的角色现金支付，或处理其失败/重登恢复时读本文。家族/帮派宗旨改走独立组织资金，旧现金意图恢复见ORGANIZATION_FUNDS.md。当前产物为faction_payments.py、OrganizationStore.revoke_funding及实际钱包事务验证；原生创建入口尚未接通，当前手动现场未部署/重启。完整目标继续active。

## 集成顺序及完成条件

1. **启动**：既有SQLiteSocialStore.initialize已准备组织表、organization_payments及只读organization_policy；主入口的runtime_storage.prepare准备currency规则/表。构造OrganizationPayments(policy, currency_rules)，运行期间复用。完成条件：启动一次完成DDL和配置加载，热路径仅执行事务。初始化钱包仍由明确的新角色/迁移流程负责；旧角色缺profile保持WalletNotInitialized。
2. **意图**：角色入口先验证原生NPC上下文、实际队伍/共同同意和原始枚举，再构造不可变OrganizationCommand。稳定request_id标识同一业务意图；deadline和当前epoch可更新，名称/宗旨/共同创始人等args改变即为新意图。完成条件：角色/团队授权可追溯，客户端提供的ID不直接变成创始人确认。
3. **扣款**：角色所有者经有界I/O，在当前租约的已BEGIN事务中调用payments.fund(db, account_id, role_id, epoch, command, now_ms)，异常由外层整体回滚。它同时写cash扣款凭据、不可变资金授予和角色恢复意图。完成条件：PaymentReceipt.status=funded且事务已提交；返回当前绝对余额，供角色经连接所有者编码刷新。无直接网络发送，也不初始化钱包。
4. **组织执行**：调用social_runtime.organizations.command(command, now_ms)，已按OrganizationStore.owner_key(command)路由独立有界邮箱及I/O，再执行store.execute，返回冻结OrganizationOutcome。它在组织事务中消费grant、写组织结果和幂等receipt。完成条件：组织receipt持久化；执行与角色扣款是两个事务，不能描述为一个原子建帮交易。
5. **成功/丢失回包**：角色当前租约事务调用payments.resolve(..., request_id, now_ms)。完成条件：它读到匹配的组织成功receipt与consumed=1，将角色意图改为committed；重复处理只返回当前钱包，不重扣、不退款。超时或异常本身不会授权退款。
6. **失败取消**：调用social_runtime.organizations.command(command, now_ms, revoke=True)，组织所有者在同一个owner_key下调用revoke_funding。已成功则返回committed；仍未成功则将该grant永久标为revoked(consumed=-1)。之后角色调用resolve读取持久决定，给cash退款一次，和refunded状态/退款凭据共用角色事务。完成条件：已退款grant不能被迟到的创建命令消费；再次处理无重复退款。角色不直接改组织的consumed状态。
7. **重登恢复**：当前角色租约调用payments.pending(..., limit)，得到冻结的旧意图。对已提交组织先resolve；需取消的命令保留原args/request_id，以当前actor epoch和新deadline交组织撤销，再resolve。共同创始人确认已失效时走取消，重新确认后的新args使用新意图。完成条件：每条旧funded意图变为committed、refunded或明确待核；旧epoch回调无法改钱包。

角色正在等待组织执行时，组织只返回不可变结果，不反向同步call该角色邮箱。已经处于RoleOwner→SocialRuntime调用中的处理，也不能从社交Module反向call同一角色邮箱取钱；角色入口需先完成自己拥有的支付阶段。IO工作线程只接ID、冻结命令与存储Adapter，不接Session/writer。

## 判定与规则

| 持久状态 | resolve结果 |
|---|---|
| 原钱包扣款凭据 + grant可用、无组织成功receipt | funded，等待决定 |
| 原扣款凭据 + 匹配组织成功receipt + grant已消费 | committed，保留扣款 |
| 原扣款凭据 + grant已撤销、无成功receipt | 退款一次并refunded |
| 原扣款凭据丢失，或grant/receipt互相矛盾 | 明确待核错误，余额保持；不能自动补钱 |

创建费用来自baseline.organizations，币种/用途来自currency-v1.json：family_create、guild_create使用cash，绑定银和元宝不替代。family_aim_update白名单保留历史兼容含义，当前fund拒绝创建新的宗旨现金意图；已有记录可resolve/取消退款，不能重复扣款。挂起上限payment_pending_limit为本地设计；已结算财务凭据不在此模块清理。所有余额均读当前账本，避免历史扣款回执覆盖新余额。

这是同一SQLite数据库的持久补偿实现。跨数据库/商业分片需要事务outbox/inbox及相应grant Adapter，当前没有该部署证明。余额不足、缺钱包、策略迁移、退款溢出或凭据矛盾均保留错误/待核，不把失败报为成功。

## 验证及未接通部分

verify_faction_payments.py通过13组公开Interface验证：实际现金扣款/授予/意图共同提交、同键幂等、绑定银拒绝替付、缺钱包不初始化、外层全部回滚、消费后组织INSERT失败的退款、取消后迟到合法创建拒绝、重登恢复/旧epoch拒绝、丢成功回包保持扣款、丢原扣款凭据拒绝退款、挂起容量、8次实际创建提交/撤销竞争、有界角色I/O独立推进及实际组织所有者顺序。结果faction-payment-verification.json。钱包基线与角色级别仅是临时夹具，家族3级仍为成长测试夹具；实际扣款/退款走currency Module，没有直接填测试付款凭据绕过。宗旨不再作为新现金测试操作，旧现金兼容与正确组织支出由verify_faction_family_funds覆盖。

其中“丢原扣款凭据”按tdd单切片：先用公开fund→组织撤销→resolve复现本应拒绝却退款的失败，再补原账本receipt存在检查，同一命令转绿。故障注入仅删临时凭据；断言通过resolve/read_wallet观察。没有将整个批次声称为测试先行。

组织邮箱调度已由faction_runtime.py接入social_runtime；最新运行路径和11组频道/并发验证见FACTION_RUNTIME.md。verify_faction_payments现通过13组，新增真实现金支付后经OrganizationRuntime验证取消等待、顺序提交/撤销与一次退款。角色原生付费入口、重登自动支付恢复和提交后原生余额刷新尚待共享集成入口接通，目前验证不是原客户端已能建帮。多人同意、完整面板/成员名单、建设维护和生产仍待恢复。

## 本批方法

codebase-design决定角色现金/恢复意图与组织消费/撤销各有单一写入者，fund/resolve/pending和revoke_funding隐藏多表事务，跨所有者返回冻结值。tdd实际约束一条凭据缺失的red→green；writing-for-agents将扣款、成功、取消、重登分支及各完成条件放在主步骤，依据与限制后置。没有运行Standards/Spec双轴审查或实机验收。

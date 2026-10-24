# NPC回购query4：真实当前实例的只读候选

2026-10-24。所属候选，未修改工作区npc_shop_sales.py、shared或服务。原16链已证回购tab发column4+完整NPCkey，普通购买由本地NpcSellItem模板驱动；c0434是原ItemBag+价格map的可用载体，原服具体选择及费用政策仍未知。查询采用c0434、以现有普通shop.open/service2绑定作为只读准入均是本片提案，尚待root采用，不能写成原服事实或已上线。

## 接入步骤与门槛

1. 先读NPC_SHOP_CATALOG_NATIVE_RESEARCH.md、NPC_BUYBACK_QUOTE_NATIVE_RESEARCH.md及本片新固定review。精确生产BASE为023920发布的5bfbc444，候选在staging/npc-buyback-query-candidate-v2/npc_shop_sales.py。当前PVE冻结发布不夹入此片，主复原单写shared。
2. main识别CGetBagInfo精确12字节的column4/完整NPCkey分支，按当前完整地图实例、成员许可、NPC实体/世代、位置/版本生成新证明，再调`plan_query(resources, body, proof, current, request_id/now_ms/deadline_ms)`。它只认可当前显式service2/shop.open；既有Stock不推售卖权限，也不增加214绑定。target0/本人role、其它column、尾随、假NPC或过期证明拒绝。NPC10003实际同时有商店资格，不能仅凭“仓库NPC”文字拒绝其既有service2。
3. 角色所有者经有界I/O调用`query(accounts, inventory, intent)`；它使用该角色leased连接、本次BEGIN读快照及SQLite连接级query_only。已有调用方事务可调`query_listing(db, inventory, intent, rules=冻结SaleRules, currency_rules=冻结CurrencyRules)`。两者校验owner/epoch、deadline和已知钱包；不建表、不扣费、不改资产、凭据、回购行或时间戳。
4. 只SELECT本角色+本NPC尚在现有TTL内的真实已售实例，按sold_at/key有界排序，最多读取capacity+1用于拒绝越界而不静默截断。新普通商店无该缓存时回空c0434清旧回购UI。未知钱包不补0；JSON/实例key/owner/template/数量/绑定/native价格错误拒绝。记录中的condition/detail继续保留，不声称普通Bag已经验证全部tooltip或装备语义。
5. main在接收结果后再核当前deadline、成员许可、NPC/地址及位置版本，由目标连接所有者投递，不把过期回调送入新世代。实际Peer原query、登录/重连及原GUI另验。
6. **费用政策门槛独立保留。** 新查询目前按现有cash_price编码，三笔原显示/现扣差异275/250、7700/7000、300/150未被此片修复。root采用与UI一致的新费用口径后，统一修改同一纯`_encode_listing`投影与真正buyback扣款，处理旧paid/current-only；合审、自然链及数据备份后才发布。不会用query绿灯宣称费用一致，不造stock4实例/qty99。

## 实现与验证规格

TDD沿既有NPC plan/Inventory/钱包公开Seam扩展只读查询。先对准确发布原件实际运行，缺plan_query为exit1；完整13组正向使用真实公有AssetChange及NPC sale产生三行缓存，未SQL造价/造付款凭据。原native c0434 codec完整往返。空10004商店、10011真实缓存的key/数量/余额、重复只读、换NPC、214不扩权、字段/完整地址/位置许可、不同角色、未知钱包、deadline、TTL、真实repurchase后的当前状态和旧lease全部验证。

SQLite authorizer在实际query_listing调用期间拒绝DML/DDL。缓存畸形source负例先在临时未提交事务中从真实已售行故障注入，再启DML拒绝、要求ValueError并回滚该测试故障；它们不是合法缓存来源证据。真实异常原型4fc6504f曾把非object JSON抛成TypeError，已保留并改成明确拒绝。完整数量上限来自冻结citemattr.maxNum，价格受原signed32编码范围约束，不新增数值公式。TTL1秒为测试显式冻结规则，等待后只过滤，原3600秒查询仍能读取原行，证明查询不清理过期数据。

初次空查询验证曾错误地对FencedConnection调用set_authorizer；改为AccountStore公开原SQLite连接建立调用方事务，再由公开Inventory和钱包函数校验租约。实际生产query仍用leased连接。另一个失败源于把10003误当仅仓库，已改为从真实服务绑定选无service2的NPC。这些失败日志保留；没有为让测试通过移除生产权限检查。

第一轮13组全绿后，codebase-design将原交易刷新与新查询的纯c0434编码集中到`_encode_listing`，为后续价格政策保留一个真实投影位置。原_cache清理、sale/buyback结算、费用、policy revision与fingerprint逻辑保持，原实际Peer sale12组回归须再次通过。没有嵌套连接或全服锁。

按code-review固定真实BASE/新增文件空BASE、Standards/Spec独立审查；writing-for-agents将NPC证明、读快照、投递后检查和费用发布门槛放在步骤旁。当前只证明所属只读Module，root准入/费用政策、main原query加密路径、原GUI、发布和完整NPC恢复仍待，不关闭总目标。

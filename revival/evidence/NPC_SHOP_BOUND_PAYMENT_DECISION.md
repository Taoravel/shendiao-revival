# 普通NPC绑银购买裁定

2026-10-23，主策划。单一参数来源design/npc-shop-payments-v1.json；涉及购买mode1、绑银扣款或绑定产物时读取。按ARCHITECTURE继续由角色Owner及既有调用方事务受理，NPC窗口实现领域分支，共享接线交原始集成窗口；本裁定不操作运行服。

原包证据见NPC_SHOP_MODES_NATIVE_RESEARCH：普通商店按钮原构造明确mode0银两、mode1绑银，20字节购买包保留完整64位NPC key。原库存10157/物品32000正价150可作普通样本；mode2..11包含其它原用途。库存行不等于原服务2权限，零/缺价不当免费，新增支付方式也不扩大NPC菜单授权。

端游资料补查：[2012官方站媒体稿](https://sdxl.wanmei.com/news/media/20120719/132976.shtml)支持两种货币的区别；[2025官方公告](https://sdxl.wanmei.com/news/gamebroad/20250813/257899.shtml)有特定礼包分别用银两/绑银且绑定结果不同的例子。后者属于后期特定商品，不能证明本包所有普通物品的价格和绑定配方。完整1.6.1服务器配方仍未知，以下按用户授权标designed，不移植后期礼包、价格或功能。

mode1沿当前已授权普通商店、原货架及正整数原价，单价与mode0相同，数量1..99，总价只扣bound_silver，产物binding1。mode0继续cash/binding0和既有receipt规则。两币不能混付、替代或自动兑换；未知钱包拒绝，元宝和其它mode保持未恢复。bound_silver独立用途npc_shop_bound只服务本配方，通用npc_shop、玩家交易和修理等不能消费它。

领域实现先在实际公开购买Interface复现mode1失败，再接真实钱包与库存。付款、绑定实例/兼容堆叠、资源source同步和领域/共用命令凭据在同一个外层租约事务；背包满、晚期编码/回调异常整体回滚，同失败键可重试。mode1新意图纳入mode/currency/binding/payment policy；mode0旧指纹字节配方保留，不改总npc版本或已付记录。凭据只确认已支付，重发读取当前余额/背包；新受理的同线包有新身份。绑定产物继续通过资产窗口已有出售限制，不因本功能新增换现金或解绑出口。

本批codebase-design决定复用currency公开事务Seam，由NPC Module隐藏付款和产物规则；钱包只增用途配置，不增加执行器、连接或全服锁。tdd已在临时AccountStore通过公开apply_currency/read_wallet保存真实红反馈：合法两份150绑银订单因用途未开放被拒。实现仅增currency.1的独立用途。verify_currency_bound_shop覆盖现金1000保持、绑银500→200、同键一次、冲突/混付/替代/交易/不足拒绝、晚期异常回滚后同键150成功为50、历史回执与当前余额分离、新旧租约。最终结果见currency-bound-shop-verification.json；NPC实例发放/共享路由/发布及GUI不在钱包检查范围。

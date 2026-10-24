# Standards

0项可行动发现。按manifest实际核对4文件共8个base/current SHA-256全部匹配，含两份新增文件空base；非Git，无提交列表。仅审本轮194行，不外推继承代码；整包哈希由根另验。

沿用完整code-review／codebase-design，依据AGENTS、ARCHITECTURE、DESIGN_AUTHORITY检查。npc_shop_payments.py启动读取后冻结两种真实配方，热路径仅查规则；npc_gameplay.py:170–173保留mode0原指纹，mode1独立纳入支付语义。:174–199在同角色租约事务内扣款、绑定实例、领域收据、source hook与最终编码，paid读当前钱包／库存。中央currency.1仅增专用用途，不改余额或旧凭据，原事实与设计配方分开标注。

12项Fowler smell逐项作heuristic判断，未见有实际后果的问题；无新全服队列、热配置读取或第二资产账。

仅静态核对固定diff／源码，未运行候选验证、DB、服务、GUI或战斗；staged绿色不作本轴执行证据。实际发布、绑定购买画面与商业并发仍另验。

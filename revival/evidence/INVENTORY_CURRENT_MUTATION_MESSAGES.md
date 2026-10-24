# 已付通用命令的当前只读回复

2026-10-23。主集成接role_inventory_commands已付分支时读本文；fresh接线仍见INVENTORY_RESOURCE_HOOK_INTEGRATION。本批只补资产模块Interface，未修改shared/root或部署。

公开签名：

```python
inventory.current_mutation_messages_transaction(db, kind, body, epoch, now_ms=None)
```

db必须是调用方已开始的当前角色fenced事务。kind/body是已经由领域共同凭据验证过的原始请求；当前支持集合公开为INVENTORY_CURRENT_MUTATION_TYPES，包含MOVE_ITEM、ARRANGE_BAG、RENAME_PET、FIGHT_PET、REST_PET、FREE_PET、USE_ITEM的pet kind1、ADD_PET_POINT。返回tuple逻辑消息，没有发送/提交/新连接/配置解析，也不读旧absolute ACK、不调用任何mutation。可选now_ms来自可信服务器，为当前宠物回复前置c0007；现有任一宠物有非空到期map而缺时间会明确拒绝。

已付流程在同db依次：根核对(role_id,request_id)共同凭据的kind/body fingerprint → 根synchronize_inventory_resource_source(...,replayed=True)严格检查当前profile/source → 本方法构造当前消息 → 提交只读事务后由目标连接发。共同凭据存在并不授权重新执行receive；本方法不代替共同凭据查验或给pending来源补写。其他异常也不能伪装成未迁移/免费重试。

MOVE/ARRANGE返回当前携带栏和真实cash，原实例已经移动/合并/删除仍能按当前整个背包刷新，不要求旧source_slot继续成立。宠物分支返回当前完整拥有列表、原目标仍在时的当前PetData、当前XP及当前选择；原目标已经放生则加当前不在栏内的Remove消息，不重建旧宠。当前另选宠物时发送实际现选key；目前无选择时明确发Rest。pet USE_ITEM同时返回当前携带栏，不要求历史物品实例仍存在，也不再次治疗/扣物。旧rename/point请求只用于身份和线包形状校验，当前名字/潜能来自现在的实例。

LEARN_SKILL_BOOK不在通用只读集合；它的独立学习领域已有稳定凭据和可信draw/time Adapter，后续由主集成明确分支。此Interface不创建随机数、不改变既有概率，也不临时将无上下文receive当作秘籍入口。

tdd沿既定同事务快照/当前原生消息Seam：缺方法实际红→只读实现绿。verify_inventory_current_mutation_messages通过真实先移动到7后移到2，回复与独立原item serializer的slot2全字节一致；实际用药/两次加点/后改名/后换参战后，旧请求只回HP6、剩余潜能3、后来名字、当前另一宠key。原宠放生和名单全空分别回复当前名单/Remove/Rest。SQL authorizer在方法全程禁止INSERT/UPDATE/DELETE/建表/删表，仍成功构造原生回复，调用方事务保持开启。原完整宠物栏converter、PetData及技能原消费者执行；当前opaque租约通过、旧租约/无事务/错误目标/短包拒绝。

结构化证据inventory-current-mutation-messages-verification.json。codebase-design将已付消息从原mutation中分离，根持有请求与资源权威；writing-for-agents明确当前回复含义、接线顺序和未完成范围。无服务、GUI、真实角色或实际战斗；shared共同凭据及现场验收由主集成继续。

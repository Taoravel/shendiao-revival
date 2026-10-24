# Spec

0项可确证缺陷、遗漏或越权。

沿用code-review独立Spec轴、codebase-design的完整地图身份Seam；只审固定current，manifest四哈希全匹配，非Git，无提交列表。

current/verify_runtime_private_map_factory.py:55要求不得“registered under a flattened or wrong address”，:76要求public独立；verify_runtime_map_address_identity.py:25、34要求旧integer仅别名public、畸形身份拒绝。current/game_runtime.py:88–97严格校验完整MapAddress及非bool整数范围；:101–119用map_id读取原碰撞/NPC资源和wire key，以完整address建立WorldDomain/mailbox；:1074–1082完整地址作为注册键，同地址复用，跨模板/instance/partition分离，精确lookup不创建。未将private instance移位成原生NPC key。

静态核对两verifier中的自然origin与受控join/移动边界，未执行检查、DB、服务、GUI或战斗。角色全地址路由、scene频道、持久恢复、实例预算/卸载均属声明后续范围，本片不证明natural handoff或完整private运行链。

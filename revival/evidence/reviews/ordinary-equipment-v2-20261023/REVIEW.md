# 普通六槽v2固定增量审查

基准为本批开工冻结源码，新文件以空文件比对；scope.json固定5文件、527行差异。项目非Git，无Git提交列表。root于汇总时重新校验全部当前源码SHA256，与冻结after完全一致。

# Standards

0项发现。仅审scope.json固定5文件／527行diff，无Git或提交列表。

沿用完整code-review与codebase-design，按根AGENTS、ARCHITECTURE、DESIGN_AUTHORITY及冻结交单／政策检查单一权威与Interface。role_equipment.py:40、84、93以None兼容旧1240；:251–255拒绝v1/v2基线混用；:276–294核对六槽负索引、资格及clean实例，套装未静默丢弃。:106–118仍严格同source／数值caps组合唯一资源，无读取治疗或第二本HP。新loader仅启动读取并冻结规则，默认v1未替换；协议仅已知1240追加第21项及entry15。

12项Fowler smell逐项作heuristic判断，未见有实际后果的问题；未把保留兼容分支误报为重复抽象。

仅静态核对冻结diff／源码／政策，未运行测试、数据库、服务或GUI。共享激活、v1旧basis升级及真实客户端／商业并发未验证，未计作本批缺陷。

# Spec

0项可确证缺陷、需求遗漏或越权。

沿用code-review独立Spec轴、codebase-design的Interface/Seam；按scope.json审固定5文件，非Git，无提交列表。

依据SPEC_SOURCE.md:7、9、11、17–23，已核对current/role_equipment.py:121–216保留默认v1、显式v2加载973及212元数据；:228拒绝旧混合v2；:251–307要求已知1240，按九属性及1230/1240重算，校验六槽负slot/数量、原角色OR/性别/needLevel、clean详情，拒绝套装、空/百分比及高级实例，耐久0不贡献。current/role_attribute_protocol.py:83–109、:133–135使用同一最终profile发送21map与entry15；资源组合仍严格匹配source/caps。

可信同事务Inventory及详情origin为Interface前提，不误报可造DTO为客户端漏洞。仅静态核对，未运行代码、数据库、服务、GUI或战斗；未验证共享激活、旧basis升级和套装，未将这些后续范围计为缺陷。

Standards 0项、无最高问题；Spec 0项、无最高问题。两轴仅静态审查；root实际运行验证与未验证范围分别见ORDINARY_EQUIPMENT_V2_INTEGRATION、RESOURCE_SHARED_RUNTIME_INTEGRATION及ARCHITECTURE_ACCEPTANCE。未部署或操作真实角色、GUI、战斗。

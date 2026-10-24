# 同库装备政策选择固定增量审查

本批开工精确base→冻结current，3文件161行，项目非Git，无提交列表。scope.json固定每文件前后SHA256，root汇总时确认全部工作源码与冻结after匹配。

# Standards

0项发现。仅审scope固定3文件增量，原文件以本批开工快照为base，新验证以空为base；无Git／提交列表。

沿用完整code-review与codebase-design，依据AGENTS、ARCHITECTURE、DESIGN_AUTHORITY及装备／资源交单核查。role_equipment.py:219–223启动加载两个真实policy并冻结registry，不切换角色。role_equipment_storage.py:71–87核registry与共用形象映射，沿当前事务／租约读取持久basis，精确选择规则对象；缺basis单独异常、不可用policy拒绝，1240的None／已知合同不得混用。只执行读取，不补0、不建连接、不读配置或写迁移。

12项Fowler smell逐项作heuristic判断，未见有实际后果的问题；该Seam支持两种实际policy，不是虚构抽象。最终资产／资源一致性仍交既有profile Interface，未扩大选择器责任。

静态核对冻结diff及脚本，未运行验证、DB、GUI、战斗或服务；不把脚本通过声明当本轴执行证据。共享切换、basis升级及自动激活未验收。

# Spec

0项可确证缺陷、遗漏或越权。

沿用code-review独立Spec轴、codebase-design的实际持久basis选择Seam；按scope.json审固定3文件，非Git，无提交列表。

SPEC_SOURCE.md:7要求“v1十件规则和v2原973条规则”，current/role_equipment.py:219–222复用两个既有严格loader并冻结registry。Spec:9要求“缺basis精确抛EquipmentBasisNotInitialized”“不能回退到任意默认”“不将旧档None改成0”，current/role_equipment_storage.py:64–87核冻结类型、共用形象、当前角色/lease及持久basis，精确选同policy对象并拒绝角色/1240合同不符；只有SELECT，无隐式基线或资源写入。Spec:11把完整profile核验交现Interface，选择器未越权承担迁移或授权。

默认.1、自动profile开关及已有basis未被本批改变。仅静态审查，未执行代码、数据库、服务、GUI或战斗；shared统一注入、basis升级、全消费者v2激活不在本批交付范围。

Standards 0项、无最高问题；Spec 0项、无最高问题。两轴仅静态。root已另实际运行verify_equipment_policy_selection，隔离库/公开事务/SQL禁写/实际20和21map通过；未改shared全局规则或启用自动迁移、部署、GUI、战斗。

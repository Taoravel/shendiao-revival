# Spec review

结论：0 个当前可行动发现，P0/P1/P2/P3均0，无审查阻塞。范围是第十九批未激活家族历程增量；全量社交、家族帮派及修炼目标仍未完成，不将其作为本批遗漏。

按code-review独立Spec轴，以第十八批固定source及since-family-donation-selection.diff代替不存在的Git/commit历史，审9个增量文件。沿用完整已读code-review、codebase-design、tdd、writing-for-agents，读取固定AGENTS、ARCHITECTURE、DESIGN_AUTHORITY与FAMILY_HISTORY_RUNTIME；公开Store/Inventory/projection为验证Seam。

检查missing/partial、scope creep、wrong behavior，未发现当前增量偏差：

- 规格“记录…及最终领域凭据共同成功或回滚”：faction_domain.py的创建、直接传位及自退位分支在同事务调用family_history，姓名从实际新org.leader读取；family_donation.py:286–288仅等级实际增长时记最终等级；family_maintenance.py:340–342仅记录非零降级。角色付款不写家族历程，失败保留paid恢复，外层幂等凭据/维护凭据优先返回，重放不重复记录。
- 规格“稳定source_id”“旧库…不追造”：family_history.py:21–36以(family,source_id)唯一约束和内容/时间冲突检查拒绝异意重用；command含actor/request、donation child、maintenance due使用不同命名空间。初始化只建表，不backfill；family_projection沿既有租约/成员代次校验后读取。
- 规格“最近100…更旧行仍在持久archive”“原表/原marshal…client_verified”：family_history.py:39–44索引限读并恢复写入顺序，不删archive；faction_protocol保持旧构造及空vector，新增kw-only冻结history、7模板形状与有界UTF16参数。原CourseInfo及完整FamilyData离线marshal证据支持编码；日期、预算和多级仅记最终等级明确为designed。5/6/7仅可编码，无跨Owner生产者；未改数值recipe或共享入口，未冒称原GUI完成。

验证：9候选、626依赖、637资源、规格/diff/原disasm哈希匹配，执行policy与基准相同。独立临时库公开Interface验证五个真实20箱栈的100箱后台恢复仅记一次最终3级（余30），重复sweep不新增；传位后改名仍保留事件当时实际新族长姓名。单key100的首次小夹具因原堆叠20上限被拒，修正夹具后通过，未作功能红灯。核阅历程与native检查产物；20脚本完整回归仍运行，最终结果/import-closure由汇总方核验。

未验：真实GUI、商业容量、跨库交付、加入/离帮及活动生产者、准确共享/NPC组织激活闭包。未改source或历史快照，未开游戏、真人库、部署或正式端口。
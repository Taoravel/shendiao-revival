# Spec

未发现本次增量的遗漏、扩域或实现错误（0项）。固定比较 r2/source→r3/source；无 Git commits。独立于 Standards，不合并排序。

依据集成规格“只管原SSendOtherSkills写入的manager+0x40完整已知map”及原生研究N1的五个身份，`role_skills.py:18,58–65` 将准入收窄为100007/100008/100009/310202/700004；保留先行特判310202，没有误禁全部class4。依据“旧r2……指纹不会静默沿用”，新指纹包含容器和身份，既有 `_read` 精确比较指纹并拒绝旧来源，不过滤旧key或补空。

依据“必要负例在原本UNKNOWN的账本上独立检查”，验证器100–110在成功adopt之前逐个测试350001/600018/700001/600005，且每次确认仍未知；接纳先过 `_entries` 再读旧基线，因此若漏命名空间校验会成功插入并使`refuse`失败，不会被已adopt冲突掩盖。grant负例使用当前revision并核无DML；310202/700004正例贯穿fresh、later/paid完整map及原consumer断言。

“中央授100008/value1、费用0、时间1000/300000和原120XP等参数未改”符合本批范围：中央JSON及task_first_skill/task_domain/原consumer三文件原字节不变；继承r1/r2已审结论。

方法/验证：code-review Spec静态核116行patch、5文件两端SHA、28冻结inputs及报告22输入对应SHA，全部一致；未重跑八组、DB、native或GUI。真实AI、shared建角/登录、发布、网络故障与GUI仍未验。

# 宠物成长与血脉颜色显示

2026-10-23，端游1.6.1/网络版本601。已接入已知Profile.growth_raw和PetCare.grade的原生字段，完整宠物查询/刷新共用pet_record；存档成长整数、成长点公式和已有血脉档位均不改写。规则出处为design/pet-presentation-v1.json。

## 当前接线及完成条件

- 已知成长：pet_record将精确原整数经pet_protocol.growth_wire_float投影后写入Pet bean+ac；未知旧成长继续保留未知，不在查询时创建Profile。
- 已知颜色：PetCare.grade1..6写入Pet bean+3c；初始grade1仍沿用pet-care-v1的designed基线，不根据中档成长推血脉档位。进化1440和其他短/字节字段保持独立。
- 喂养、用药、加点等完整宠物刷新保留两字段；加点现将完整回复编码放在扣点、版本及领域回执的同一事务内。编码失败回滚后，公开当前快照须与操作前相同。
- 完成条件分层：原Pet/SRefreshPetData完整codec、原刷新存储指令、原显示算术/原配置lookup已验证；真实窗口颜色、文字排版及技能图标/技能玩法仍待实机和后续恢复。

## 原生证据

成长：原SRefreshPetData消费者1135303将message+b4（内层Pet bean+ac）作为float32加载，113530d写内部pet+30。原UI1130d35加载pet+30，1130d38乘映像2473fa8处的binary64常量1000.0，再调用19191e0。SSE与x87两条原转换路径均执行验证。属性定义表600为“宠物成长率”；此wire显示尺度与服务器成长点公式是两个问题，不能把/1000重新套到派生属性。

颜色：原11354fb读取message+44（bean+3c），1135503写内部pet+2c，GUI观察者为空时沿原分支继续。原宠物面板140df60..140df92以该值调用89e3b0返回的CPetXueMaiConfig查找，读取原record+28决定技能格数；原“skillnumber”字符串225cdcc及配置解析886d20..886d49把该字段写入同一+28。配置初始化d436fc将实现vtable225ce24放入root+c1c，89e3b0同样返回+c1c，表身份一致。六档原格数4/4/6/8/10/12已执行核对；这不是已学技能数量，也不授予技能。

research_pet_presentation.py使用已保存原映像，执行上述原指令与原float转换，配置查找由宿主提供原目录记录；它不启动客户端/GUI。结构化证据为pet-presentation-native.json。原Pet字段坐标另沿用pet-native-field-layout.json，新的语义以本批消费者证据为准。

## 浮点投影与设计范围

直接用最近float32编码raw/1000会使部分原值减少1。例如996的最近float32为0.9959999918937683，原UI乘1000后截断为995。此前完整记录还未编码该字段，已知1006实际走到原消费者时为0，已建立失败回归。

当前选择不小于raw/1000的最小float32，并验证原UI反投影的整数仍等于raw；无法无损表示就拒绝。选择具体浮点bit pattern为designed确定性投影，原客户端float存储、1000常量、截断和字段语义为client_verified，不宣称已知原服务器的浮点尾数。不会修改存档、重掷成长、改变pet-growth-v1的累计growth_raw/100点数计算或乘派生属性。

111个原成长整数（范围900..1325），以及500..5000共4501个连续输入，在原SSE和x87转换下均回到原整数。996专例、原刷新字段、六档颜色lookup、实际喂养/加点刷新、重开存档已验证。受控旧Profile导致真实signed-short编码拒绝时，加点/版本/回执整体回滚；测试通过公开receive及immutable_snapshot观察，没有替换pet_record内部实现。

## 方法、产物、验证与未验证

codebase-design把数值投影集中于pet_protocol、pet_record共享所有完整刷新路径；权威整数与显示表示分开。diagnosing-bugs以实际宠物记录→原解码→原消费建立“已知1006/grade1变成0/0”的红例，并定位最近浮点996变995；随后原算术差分变绿。tdd沿既有公开事务Seam对超出63位整数租约先观察OverflowError，再收窄身份校验，保持无效上下文在访问存储前被拒绝。writing-for-agents把来源、当前接线与未验证范围集中于本文，集成摘要仅保留触发指针。

产物：pet_protocol.py、pet-presentation-v1.json、原生研究脚本/证据、verify_pet_presentation.py，以及Inventory两字段/加点提交顺序的局部修改。宠物成长和养护的原序列化fixture补入已确认字段，继续逐字节比较，不放宽原比较。

通过：pet_presentation、pet_growth、pet_care、pet_native_commands、pet_consumables、pet_capped_awards、inventory、task_pet_experience。任务XP仍使用实际固定宠物、原奖励量与当前快照，不因显示修正改变接受者或经验。原生加点请求没有客户端重试ID，仍按原角色受理命令处理，未把两次相同请求合并成同一命令。

未验证/未实现：真实宠物窗口文字和颜色；技能学习/遗忘/格子/被动效果和战斗技能；血脉升级、进化、资质洗炼、寿命补充；战斗死亡养护回写及全部高级字段。未部署共享服务，未修改真实角色或运行战斗。

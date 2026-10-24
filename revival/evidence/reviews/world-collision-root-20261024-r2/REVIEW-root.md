# collision 202425 主策划阶段审查

## Standards

独立静态硬0/判断0，见 Standards-root.md。

## Spec

独立静态 missing0/extra0/wrong0，原paid duplicate P1已修复，见 Spec-root.md。

## 新运行反例及决定

root已对准确r2实际执行7项：lifecycle、strict earlyACK、terminals5组、scene_delivery_terminals6组、自然private断线、自然两角色bloodmark/聊天/冷重连、资源图1006/1404/1501诊断子集，均exit0；每项1442/418/1204+runner全SHA前后稳定。

但随后冻结新intro-race补充探针dd64e539532eb8d571acf23b420d3aac22492b1eb50e49308bdb36f398d5d22a，fresh角先真实early ACK开始当前CG，再放开旧Scene drain，对同r2实际exit1：await pending→Peer.take queue.join Timeout，尚未到closed断言。因此不把timeout写成已执行closed断言。源码旧回执通用ValueError使发送泵终止，合法新CG队列无法继续。此实际反例使发布条件不成立，静态0不能代替完整运行验收。

r2不发布，不签通过；旧source、静态报告、7绿和新RED全部保留。main已另冻r3 202823，只按严格身份分类post-drain失效回执，拒安装并继续当前合法队列，必须同例转绿和新两轴后再验收。未启动GUI/服务、正式DB或正式剧情战斗；容量未验证。

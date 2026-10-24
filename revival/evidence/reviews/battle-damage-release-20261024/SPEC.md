# Spec

0项代码缺陷；真人画面待验收。

方法：code-review规格轴对照固定BASE；diagnosing-bugs复跑实际出包→原解码→原HP消费者。

规格《BATTLE_DAMAGE_PRESENTATION_FIX.md》7、13行要求结果map、仅两文件：battle_protocol.py:94–113写map，training_battle.py:259写key1。1429项仅两项变化，后者仅一行；未见缺项、越界或实现错误。

冻结harness 8/8通过，含太湖猫两回合；旧包读0，新普攻读−16。两生产SHA前后匹配指定值，1429生产/8验证输入保持。

按规格29行，完整Process、资源写入、受击、飘字、血条及GPU尚未验收；未知不计代码缺陷。本次未启动客户端、监听或访问真人DB。

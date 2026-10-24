"""Inventory original social classes and explicit full-restoration acceptance gaps.

RTTI candidates are discovery evidence, never proof a protocol or feature works.
"""
import hashlib
import json
import re
from inspect_client import OUT,write_json


SYSTEMS={
 'friends':('好友与玩家群组',('好友查找/列表/设置','申请同意拒绝','黑名单/分组/亲密度','私聊/离线消息/历史','建群/加群/群主管理/群聊')),
 'msg':('公共聊天',('当前/门派/世界频道','队伍/家族/帮派频道','等级/消耗/频控','表情/物品链接/富文本')),
 'faction':('家族与帮派',('创建及真实扣费退款','申请/邀请/审核','名单/职位/权限/公告','成员退出驱逐/传位','家族成长/维护/生产',
    '帮派建筑/资金/帮费/捐赠','研究选择/小时经验/等级与上限','成员辅助技能学习/支付/声望',
    '人物战斗修炼/属性修炼/经验与结算','组织地图/召集/任务/Boss/帮战与奖励')),
 'master':('师徒',('登记/搜索/拜师收徒','双方确认与人数等级约束','师徒列表/在线通知','出师/评价/奖励','解除/历史关系')),
 'sworn':('结拜',('申请/成员共同确认','仪式/任务/称谓','成员增减/缺席处理','解除关系')),
 'marry':('婚姻与婚礼',('求婚/双方确认','任务/婚礼预约/入场','请柬/红包/婚礼互动','夫妻关系/技能','协议离婚/强制离婚/解除')),
 'team':('组队协作依赖',('建队/申请/邀请/接受拒绝','队长/暂离/归队/跟随','成员同步/队伍聊天','副本及战斗资格交接')),
 'teamcontract':('团队契约依赖',('建立契约/确认','成员与任务状态','解除及结算')),
 'trade':('交易资产依赖',('双方确认/预留资产','断线取消/恢复','幂等交易提交/补偿')),
}


def main():
    image=(OUT/'evidence/native-image.bin').read_bytes()
    names=sorted(set(x.decode('ascii') for x in re.findall(rb'\.\?AV[^\x00]{1,180}',image)
                     if b'@gsp@knight@@' in x and b'?$' not in x))
    systems=[]
    for ns,(title,features) in SYSTEMS.items():
        candidates=[n for n in names if f'@{ns}@gsp@knight@@' in n]
        systems.append({'namespace':ns,'title':title,'native_class_candidates':candidates,
                        'candidate_count':len(candidates),'required_features':list(features),
                        'complete':False,'native_client_acceptance':'pending'})
    runtime_paths=[OUT/name for name in ('game_runtime.py','social_runtime.py','social_owner.py','group_runtime.py','group_store.py','group_protocol.py',
                                      'faction_domain.py','faction_protocol.py','faction_payments.py','faction_runtime.py',
                                      'faction_types.py','family_projection.py','family_runtime.py','guild_offices.py','guild_training.py',
                                      'guild_protocol.py','guild_projection.py','guild_runtime.py','guild_practice.py',
                                      'role_practice.py','practice_protocol.py','practice_npc.py',
                                      'family_products.py','family_products_protocol.py','family_maintenance.py','family_maintenance_runtime.py')]
    runtime_sources={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in runtime_paths if path.exists()}
    result={'scope':'full_social_restoration','goal_status':'active',
            'runtime_sources_sha256':runtime_sources,
            'native_image_sha256':hashlib.sha256(image).hexdigest(),
            'meaning':'Class candidates identify research scope, not validated protocol IDs or working features.',
            'completion_requires':['original requests and UI flows connected','permissions and persistence verified',
             'entity ownership and bounded delivery integrated','restart/retry/failure recovery verified',
             'real original-client acceptance','remaining unknown rules explicitly designed and sourced'],
            'systems':systems,
            'current_critical_gaps':['social/group runtime source wiring tested; current live process has not been restarted by this window',
              'original-client GUI acceptance of social runtime remains pending',
              'family/guild chat integrated via per-organization owners and real temporary TCP; native GUI still pending',
              'family five native management routes and guild three query/appointment/resignation routes, basic data/current roster/presence integrated; full guild detail/NPC creation contexts/history/extensions/GUI pending',
              'organization local cash debit/revoke/refund Adapter verified; native role-owner pay/recovery entry not wired; cross-database saga pending',
              'organization notice changes use separate family/guild fund ledgers; old cash intents recover; original guild initial balance, full income/construction and remaining native management routes pending',
              'family production settings, close charge, original buttons/formats and hourly normal/simple maintenance with explicit designed population/stock rules implemented; periodic source and pending permission fences tested; NPC/purchases/construction/full dissolution consumers/GUI pending',
              'guild offices/authority and basic roster wired; family join uses durable guild-owned cursor; seven-skill cash/pill transactions, trusted NPC Adapter and login known-skill/pending recovery implemented; live NPC registration/shared purchase dispatch/managed-resource source consumers/full panels/property/life/inscription/research progression/battle effects/GUI pending',
              'group main/management/history flows integrated; lifecycle, system notifications, rich content and live GUI remain pending',
              'master/sworn/marry require implementation and end-to-end acceptance']}
    write_json(OUT/'evidence/social-full-recovery-inventory.json',result)
    print(json.dumps({'scope':result['scope'],'systems':[{k:s[k] for k in ('namespace','candidate_count','complete')} for s in systems]}))


if __name__=='__main__':main()

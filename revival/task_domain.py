"""Pure, role-owned task transitions. No file, database, Session or network I/O.

Rules for offer/accept and successor candidates are local restoration policy.
Gameplay evidence is emitted by the authoritative map/battle/scenario owner;
client commit/dialog-end packets are requests and cannot create such evidence.
"""
from dataclasses import dataclass, replace


PLAIN_DIALOGUE_BLOCKERS = ('ScenarioInfoAnimationID', 'ScenarioInfoBranchNpcID', 'ProcessBarTime',
    'RewardMapJumpType', 'ActiveInfoTargetID', 'ActiveInfoTargetNum', 'ActiveInfoTimeLimit',
    'ActiveInfoGiveBackMoney', 'ActiveInfoGiveBackPetID', 'ActiveInfoUseItemID',
    'ActiveInfoOtherType', 'AIInfoAIID', 'TransformID', 'ActiveInfoMaxStep',
    'ActiveInfoMiniStep', 'QuestionInfoNpcID')


def supports_plain_dialogue(task):
    """Capability query shared by NPC interactions and task-chain activation."""
    return (task['type'] == 10 and task['target']['npc_id'] > 0 and task['target']['map_id'] > 0
            and not any(int(task['attributes'].get(k, 0)) for k in PLAIN_DIALOGUE_BLOCKERS))


PROLOGUE_TOUCH_SOURCE_IDS=frozenset((100106,100206,100306,100406,100506,100606,
    100706,100806,100906,101002,103206))
PROLOGUE_TOUCH_IDS=PROLOGUE_TOUCH_SOURCE_IDS-{101002}  # Legacy edge outside current43 creation routes.

PROLOGUE_FIRST_SKILL_IDS=frozenset((100179,100279,100379,100479,100579,100679,
    100779,100879,100979,103279))


def supports_prologue_first_skill(task):
    """Original ten teaching nodes; never a generic progress-bar completion."""
    a=task['attributes']
    return (task['id'] in PROLOGUE_FIRST_SKILL_IDS and task['type']==10
        and (task['target']['map_id'],task['target']['npc_id'])==(1501,10908)
        and int(a.get('ProcessBarTime',0))==1 and a.get('ProcessBarText')=='掌握技能'
        and not any(int(a.get(k,0)) for k in PLAIN_DIALOGUE_BLOCKERS if k!='ProcessBarTime')
        and not any(int(a.get(k,0)) for k in ('TransMinLevel','TransMaxLevel','ActiveInfoIsRestartTimer','ActiveInfoStepProbability'))
        and not task['dialogue']['start'] and not task['dialogue']['finish'] and not task['text']['note']
        and task['level']=={'min':0,'max':0} and not a.get('ScenarioInfoBranchNote')
        and set(task['lists'])=={'PostMissionList','DisPlayNPCID'}
        and tuple(map(int,task['lists']['DisPlayNPCID']))==(10910,10911,10912)
        and not task['request_mission_ids'] and not task['role_config_ids'] and not task['display_items']
        and len(task['incoming_ids'])==len(task['next_ids'])==1
        and task['display_rewards']=={'ExpReward':120,'MoneyReward':0,'PetExpReward':0,'ShengWang':0,'SMoney':0})

PROLOGUE_PUZZLE_IDS=frozenset((100120,100219,100319,100419,100519,100619,
    100719,100819,100919,103220))


PROLOGUE_FIRST_DREAM_RETURN_IDS=frozenset((100111,100210,100310,100410,100510,100610,
    100710,100810,100910,103211))
PROLOGUE_DREAM_RETURN_IDS=PROLOGUE_FIRST_DREAM_RETURN_IDS|frozenset((100121,100220,100320,100420,100520,100620,
    100720,100820,100920,103221))


def supports_prologue_dream_return(task):
    """Original20 return nodes; completion still requires a policy/world permit."""
    a=task['attributes'];first=task['id'] in PROLOGUE_FIRST_DREAM_RETURN_IDS
    return (task['id'] in PROLOGUE_DREAM_RETURN_IDS and task['type']==10
        and (task['target']['map_id'],task['target']['npc_id'])==(1501,10085 if first else 10140)
        and tuple(int(a.get(k,0)) for k in ('RewardMapJumpType','RewardMapID','RewardMapXPos','RewardMapYPos'))
            ==((3,1006,170,70) if first else (3,1006,335,144))
        and not any(int(a.get(k,0)) for k in PLAIN_DIALOGUE_BLOCKERS if k!='RewardMapJumpType')
        and len(task['dialogue']['start'])==(4 if first else 5) and not task['dialogue']['finish']
        and not task['text']['note'] and not a.get('ScenarioInfoBranchNote')
        and not task['lists'].get('ScenarioInfoBranchOptionList') and not task['request_mission_ids']
        and not task['role_config_ids'] and not task['display_items']
        and len(task['incoming_ids'])==len(task['next_ids'])==1
        and task['display_rewards']=={'ExpReward':125 if first else 450,'MoneyReward':0,
            'PetExpReward':0 if first else 450,'ShengWang':0,'SMoney':0})


def supports_prologue_puzzle(task):
    """Exact original portrait tasks; this does not authorize client claims."""
    a=task['attributes']
    return (task['id'] in PROLOGUE_PUZZLE_IDS and task['type']==59
        and (task['target']['map_id'],task['target']['npc_id'])==(1501,0)
        and not any(int(a.get(k,0)) for k in PLAIN_DIALOGUE_BLOCKERS+(
            'TransMinLevel','TransMaxLevel','ActiveInfoIsRestartTimer','ActiveInfoStepProbability'))
        and tuple(map(int,task['lists'].get('DisPlayNPCID',())))==(11106,)
        and len(task['dialogue']['start'])==len(task['dialogue']['finish'])==1
        and all(line['speaker']==10139 for kind in ('start','finish') for line in task['dialogue'][kind])
        and not task['request_mission_ids'] and not task['role_config_ids']
        and task['level']=={'min':0,'max':0} and not task['text']['note']
        and not a.get('ScenarioInfoBranchNote') and not task['lists'].get('ScenarioInfoBranchOptionList')
        and len(task['incoming_ids'])==len(task['next_ids'])==1 and not task['display_items']
        and task['display_rewards']=={'ExpReward':360,'MoneyReward':0,
            'PetExpReward':350 if task['id']==100719 else 360,'ShengWang':0,'SMoney':0})


def supports_prologue_touch(task):
    """Original blood-handprint objectives, requiring timed world settlement."""
    a=task['attributes']
    return (task['id'] in PROLOGUE_TOUCH_IDS and task['type']==10
        and (task['target']['map_id'],task['target']['npc_id'])==(1006,10498)
        and tuple(int(a.get(k,0)) for k in ('ProcessBarTime','RewardMapJumpType',
            'RewardMapID','RewardMapXPos','RewardMapYPos'))==(3,3,1501,63,79)
        and not any(int(a.get(k,0)) for k in PLAIN_DIALOGUE_BLOCKERS
                    if k not in ('ProcessBarTime','RewardMapJumpType'))
        and not task['dialogue']['start'] and not task['dialogue']['finish']
        and len(task['incoming_ids'])==len(task['next_ids'])==1
        and not task['request_mission_ids']
        and not task['role_config_ids'] and task['level']=={'min':0,'max':0}
        and not task['display_items'] and not any(task['display_rewards'].values()))


NATIVE_EFFECT_DIALOGUE_IDS=frozenset((100105,100204,100304,100404,100504,100604,100704,100804,100904,103205))


def supports_native_effect_dialogue(task):
    """Verified60001 local title effect after ordinary NPC commit, not a CG.

    Keep plain-dialogue capability narrow. These exact original10 quests have
    no gameplay animation acknowledgement or extra server continuation.
    """
    return (task['id'] in NATIVE_EFFECT_DIALOGUE_IDS and task['type']==10
            and task['target']['map_id']==1006 and task['target']['npc_id'] in (10212,10492)
            and int(task['attributes'].get('ScenarioInfoAnimationID',0))==60001
            and not any(int(task['attributes'].get(k,0)) for k in PLAIN_DIALOGUE_BLOCKERS if k!='ScenarioInfoAnimationID')
            and len(task['dialogue']['start'])==3 and not task['dialogue']['finish']
            and not task['attributes'].get('ScenarioInfoBranchNote') and not task['text']['note'])


def supports_item_submission(task):
    """Static item objectives; extra animation/timer/transfer work stays explicit."""
    blockers = tuple(k for k in PLAIN_DIALOGUE_BLOCKERS if k not in ('ActiveInfoTargetID','ActiveInfoTargetNum'))
    return (task['type']==12 and task['target']['npc_id']>0 and task['target']['map_id']>0
            and task['target']['id']>0 and task['target']['count']>0
            and not any(int(task['attributes'].get(k,0)) for k in blockers))


def supports_money_submission(task):
    """Static type11 amount, with its dedicated native money confirmation."""
    a=task['attributes']
    blockers=tuple(k for k in PLAIN_DIALOGUE_BLOCKERS if k!='ActiveInfoGiveBackMoney')+(
        'TransMinLevel','TransMaxLevel','ActiveInfoIsRestartTimer','ActiveInfoStepProbability')
    return (task['type']==11 and task['target']['map_id']>0
            and task['target']['npc_id']>0 and task['target']['npc_id']!=999999
            and 0<int(a.get('ActiveInfoGiveBackMoney',0))<=0x7fffffff
            and '$round$' not in task['name']
            and not any(int(a.get(k,0)) for k in blockers) and not task['text']['note']
            and not a.get('ScenarioInfoBranchNote') and not task['lists'].get('ScenarioInfoBranchOptionList')
            and all(line['speaker'] is not None for kind in ('start','finish') for line in task['dialogue'][kind]))


def supports_static_region(task):
    """Original type56 rectangles without another objective/animation/transfer.

    This grants no movement mode or activation. A trusted world position is
    required even for lightgong quests whose rectangle has ordinary clear cells.
    """
    blockers=PLAIN_DIALOGUE_BLOCKERS+('ActiveInfoNpcID','TransMinLevel','TransMaxLevel',
                                    'ActiveInfoIsRestartTimer','ActiveInfoStepProbability')
    a=task['attributes']
    rect=tuple(int(a.get(k,0)) for k in (
        'ActiveInfoLeftPos','ActiveInfoTopPos','ActiveInfoRightPos','ActiveInfoBottomPos'))
    return (task['type']==56 and task['target']['map_id']>0
            and 0<=rect[0]<rect[2]<=0x7fffffff//16
            and 0<=rect[1]<rect[3]<=0x7fffffff//16
            and not any(int(a.get(k,0)) for k in blockers)
            and not a.get('ScenarioInfoBranchNote')
            and not task['lists'].get('ScenarioInfoBranchOptionList'))


def _supports_npc_scenario_dialogue(task):
    """Shared static type50 NPC contract; cyclic instances remain unsupported.

    Source999999 is an unbound placeholder. NPC-less, transfer/movie/branch and
    other scenario types retain their own activation/authoritative event rules.
    """
    a=task['attributes']
    blockers=PLAIN_DIALOGUE_BLOCKERS+('TransMinLevel','TransMaxLevel',
                                    'ActiveInfoIsRestartTimer','ActiveInfoStepProbability')
    return (task['type']==50 and task['target']['map_id']>0
            and task['target']['npc_id']>0 and task['target']['npc_id']!=999999
            and '$round$' not in task['name']
            and not any(int(a.get(k,0)) for k in blockers)
            and not a.get('ScenarioInfoBranchNote') and not task['text']['note']
            and not task['lists'].get('ScenarioInfoBranchOptionList'))


def supports_npc_finish_dialogue(task):
    """Type50 NPC commit then native state1 finish dialogue, no extra mechanic."""
    return (_supports_npc_scenario_dialogue(task) and not task['dialogue']['start']
            and bool(task['dialogue']['finish'])
            and all(line['speaker'] is not None for line in task['dialogue']['finish']))


def supports_npc_start_dialogue(task):
    """Type50 local start dialogue then ordinary NPC commit, without a movie."""
    return (_supports_npc_scenario_dialogue(task) and bool(task['dialogue']['start'])
            and not task['dialogue']['finish']
            and all(line['speaker'] is not None for line in task['dialogue']['start']))


def supports_npc_empty_scenario(task):
    """Static type50 NPC handoff with no local conversation or other mechanic."""
    return (_supports_npc_scenario_dialogue(task) and not task['dialogue']['start']
            and not task['dialogue']['finish'])


def supports_fixed_npc_quiz(task):
    """Original type17 fixed local question; dynamic/round questions stay out."""
    a=task['attributes'];wrong=task['lists'].get('QuestionInfoWrongAnswerList',())
    blockers=tuple(k for k in PLAIN_DIALOGUE_BLOCKERS if k!='QuestionInfoNpcID')+(
        'TransMinLevel','TransMaxLevel','ActiveInfoIsRestartTimer','ActiveInfoStepProbability')
    return (task['type']==17 and task['target']['map_id']>0 and task['target']['npc_id']>0
            and task['target']['npc_id']!=999999 and '$round$' not in task['name']
            and int(a.get('QuestionInfoNpcID',0))==task['target']['npc_id']
            and bool(a.get('QuestionInfoCorrectAnswer')) and bool(a.get('QuestionInfoConversion'))
            and 1<=len(wrong)<=5 and all(type(x) is str and bool(x) for x in wrong)
            and all(line['speaker'] is not None for k in ('start','finish') for line in task['dialogue'][k])
            and not any(int(a.get(k,0)) for k in blockers) and not task['text']['note']
            and not a.get('ScenarioInfoBranchNote') and not task['lists'].get('ScenarioInfoBranchOptionList'))


FIGHTING_PET_TASK_IDS=frozenset((100189,100289,100389,100489,100589,100689,
    100789,100889,100989,103289,101014))


def supports_fighting_pet_task(task):
    """Only the original11 selected-pet objectives, not arbitrary type59."""
    a=task['attributes']
    return (task['id'] in FIGHTING_PET_TASK_IDS and task['type']==59
            and task['target']['npc_id']==0 and task['target']['map_id']==1006
            and not any(int(a.get(k,0)) for k in PLAIN_DIALOGUE_BLOCKERS+(
                'TransMinLevel','TransMaxLevel','ActiveInfoIsRestartTimer','ActiveInfoStepProbability'))
            and not task['dialogue']['start'] and not task['dialogue']['finish']
            and not task['text']['note'] and not a.get('ScenarioInfoBranchNote')
            and not task['lists'].get('ScenarioInfoBranchOptionList'))


def supports_level_gate(task):
    """Verified resource family with ordinary level goals; special58 stays out.

    Completion timing is a designed server policy, not a recovered server loop.
    209302 is phone binding; 224302 lacks a confirmed level objective.
    """
    return (task['type']==58 and task['id'] not in (209302,224302)
            and 15<=task['level']['min']<=155 and task['level']['max'] in (0,155)
            and task['target']['npc_id']==0 and not task['role_config_ids']
            and not any(int(task['attributes'].get(k,0)) for k in PLAIN_DIALOGUE_BLOCKERS)
            and not any(int(task['attributes'].get(k,0)) for k in ('TransMinLevel','TransMaxLevel')))


def valid_task_epoch(epoch):
    # Epochs are opaque identities: AccountStore currently returns positive ints
    # while persisted TEXT/other compatible Adapters may supply strings.
    return (type(epoch) is str and 1 <= len(epoch) <= 128) or (type(epoch) is int and epoch > 0)


@dataclass(frozen=True)
class TaskActor:
    account_id: int
    role_id: int
    login_epoch: int | str
    level: int
    shape: int


@dataclass(frozen=True)
class TaskSnapshot:
    role_id: int
    revision: int = 0
    offered: frozenset = frozenset()
    active: frozenset = frozenset()
    completed: frozenset = frozenset()
    tracked: frozenset = frozenset()

    def __post_init__(self):
        if (any(type(v) is not frozenset for v in (self.offered, self.active, self.completed, self.tracked))
                or self.active & self.completed or not self.tracked <= self.active
                or self.revision < 0):
            raise ValueError('Invalid task snapshot')


@dataclass(frozen=True)
class TaskEvidence:
    task_id: int
    role_id: int
    login_epoch: int | str
    kind: str
    source_id: str
    map_id: int = 0
    npc_id: int = 0
    reference_id: int = 0  # AIInfoAIID or ScenarioInfoAnimationID
    item_debits: tuple = ()  # trusted item validation; never copied straight from client
    region_position: tuple = ()  # trusted logical-pixel (x,y), not wire input
    region_version: int = 0


@dataclass(frozen=True)
class TaskPlan:
    role_id: int
    login_epoch: int | str
    before: TaskSnapshot
    after: TaskSnapshot
    action: str
    task_id: int
    # Source literals survive until a settlement handler maps every channel.
    reward_scalars: tuple = ()
    reward_items: tuple = ()
    next_ids: tuple = ()
    source_event: str = ''
    continuation_fields: tuple = ()
    objective_debits: tuple = ()
    reward_item_selectors: tuple = ()
    reward_role_config_id: int | None = None
    completion_effect_id: int = 0
    completion_finish_dialogue: bool = False


class TaskDomain:
    def __init__(self, resources):
        self.resources = resources

    def _eligible(self, actor, task):
        minimum = max(task['level']['min'], int((task.get('offer') or {}).get('attributes', {}).get('minilevel', 0)))
        maximum = task['level']['max']
        choices = task['role_config_ids']
        return (actor.level >= minimum and (not maximum or actor.level <= maximum)
                and (not choices or self.resources.shape_to_role_config.get(actor.shape) in choices))

    def available(self, actor, snapshot):
        self._scope(actor, snapshot)
        return tuple(sorted(q for q in snapshot.offered - snapshot.active - snapshot.completed
                            if q in self.resources.definitions
                            and self._eligible(actor, self.resources.definitions[q])))

    @staticmethod
    def _scope(actor, snapshot):
        if actor.role_id != snapshot.role_id or not valid_task_epoch(actor.login_epoch):
            raise ValueError('Task owner mismatch')

    def plan(self, actor, snapshot, action, task_id, *, tracked=0, evidence=None):
        self._scope(actor, snapshot)
        task = self.resources.definitions.get(task_id)
        if task is None:
            raise ValueError('Task definition missing')
        after = snapshot
        rewards, items, next_ids, source, continuations = (), (), (), '', ()
        if action == 'offer':
            # Trusted activation policy calls offer; client IDs cannot register offers.
            if not self._eligible(actor, task):
                raise ValueError('Task character or level requirement')
            if task_id not in snapshot.active | snapshot.completed:
                after = replace(snapshot, offered=snapshot.offered | {task_id})
        elif action == 'accept':
            if task_id not in self.available(actor, snapshot):
                raise ValueError('Task is not offered')
            after = replace(snapshot, offered=snapshot.offered - {task_id}, active=snapshot.active | {task_id})
        elif action == 'wait_level':
            # Server-only chapter progression. MinLevel is this objective's goal,
            # not permission to skip waiting by relaxing every quest's minimum.
            if not supports_level_gate(task) or not 1<=actor.level<=155:
                raise ValueError('Unsupported ordinary level gate')
            if task_id in snapshot.completed:
                raise ValueError('Level gate is already completed')
            after=replace(snapshot,offered=snapshot.offered-{task_id},active=snapshot.active|{task_id})
        elif action == 'track':
            if tracked not in (0, 1) or tracked and task_id not in snapshot.active:
                raise ValueError('Task is not active or invalid tracking flag')
            after = replace(snapshot, tracked=(snapshot.tracked | {task_id}) if tracked else (snapshot.tracked - {task_id}))
        elif action == 'complete':
            if task_id not in snapshot.active:
                raise ValueError('Task is not active')
            self._completion(actor, task, evidence)
            source = evidence.source_id
            rewards = tuple(sorted(task['display_rewards'].items()))
            items = tuple((r['id'], r['count'], r['bind']) for r in task['display_items'])
            # Keep missing/character-specific edges too. The activation policy
            # resolves these literals; completion never silently drops an edge.
            next_ids = tuple(task['next_ids'])
            # Preserve unresolved presentation/transfer instructions as literals;
            # a victory must not silently discard the original finish dialogue.
            continuations = tuple((k, task['attributes'][k]) for k in (
                'RewardMapJumpType', 'RewardMapID', 'RewardMapXPos', 'RewardMapYPos',
                'ScenarioInfoAnimationID') if k in task['attributes']) + tuple(
                (k, tuple(task['lists'][k])) for k in (
                    'DisPlayNPCID', 'ScenarioInfoFinishConversationList', 'ScenarioInfoFinishNpcID')
                if k in task['lists'])
            after = replace(snapshot, active=snapshot.active - {task_id},
                            completed=snapshot.completed | {task_id}, tracked=snapshot.tracked - {task_id})
        else:
            raise ValueError('Unsupported task transition')
        if after != snapshot:
            after = replace(after, revision=snapshot.revision + 1)
        return TaskPlan(actor.role_id, actor.login_epoch, snapshot, after, action, task_id,
                        rewards, items, next_ids, source, continuations,
                        evidence.item_debits if action=='complete' and evidence.kind=='npc_items_submitted' else (),
                        tuple(int(x) for x in task['lists'].get('RewardItemShapeIDList',())) if action=='complete' else (),
                        self.resources.shape_to_role_config.get(actor.shape) if action=='complete'
                            and task['lists'].get('RewardItemShapeIDList') else None,
                        60001 if action=='complete' and evidence.kind=='npc_native_effect_dialogue_completed' else 0,
                        action=='complete' and (evidence.kind=='npc_finish_dialogue_completed'
                            or evidence.kind in ('npc_quiz_correct_answer','npc_money_submitted') and bool(task['dialogue']['finish'])))

    def _completion(self, actor, task, evidence):
        if (not isinstance(evidence, TaskEvidence) or evidence.role_id != actor.role_id
                or evidence.login_epoch != actor.login_epoch or evidence.task_id != task['id']
                or type(evidence.source_id) is not str or not 1 <= len(evidence.source_id) <= 160):
            raise ValueError('Missing or stale authoritative task event')
        a, target = task['attributes'], task['target']
        if evidence.kind == 'npc_dialogue_completed':
            if (not supports_plain_dialogue(task) or evidence.npc_id != target['npc_id']
                    or evidence.map_id != target['map_id']):
                raise ValueError('Task requires another gameplay event')
        elif evidence.kind == 'npc_native_effect_dialogue_completed':
            if (not supports_native_effect_dialogue(task) or evidence.reference_id!=60001
                    or evidence.npc_id!=target['npc_id'] or evidence.map_id!=target['map_id']):
                raise ValueError('Unsupported native effect dialogue completion')
        elif evidence.kind == 'npc_finish_dialogue_completed':
            if (not supports_npc_finish_dialogue(task) or evidence.npc_id!=target['npc_id']
                    or evidence.map_id!=target['map_id']):
                raise ValueError('Scenario finish dialogue requires its current authoritative NPC commit')
        elif evidence.kind == 'npc_start_dialogue_completed':
            if (not supports_npc_start_dialogue(task) or evidence.npc_id!=target['npc_id']
                    or evidence.map_id!=target['map_id']):
                raise ValueError('Scenario start dialogue requires its current authoritative NPC commit')
        elif evidence.kind == 'npc_empty_scenario_committed':
            if (not supports_npc_empty_scenario(task) or evidence.npc_id!=target['npc_id']
                    or evidence.map_id!=target['map_id']):
                raise ValueError('Empty scenario requires its current authoritative NPC commit')
        elif evidence.kind == 'npc_quiz_correct_answer':
            if (not supports_fixed_npc_quiz(task) or type(evidence.reference_id) is not int
                    or evidence.reference_id!=0 or evidence.npc_id!=target['npc_id']
                    or evidence.map_id!=target['map_id']):
                raise ValueError('Fixed quiz requires the original correct answer code and current NPC')
        elif evidence.kind == 'npc_money_submitted':
            if (not supports_money_submission(task) or type(evidence.reference_id) is not int
                    or evidence.reference_id!=int(a['ActiveInfoGiveBackMoney'])
                    or evidence.npc_id!=target['npc_id'] or evidence.map_id!=target['map_id']):
                raise ValueError('Task money requires the exact original amount and current NPC')
        elif evidence.kind == 'pet_set_fighting':
            if (not supports_fighting_pet_task(task) or type(evidence.reference_id) is not int
                    or not 0<evidence.reference_id<=0x7fffffff or evidence.map_id!=target['map_id']
                    or evidence.npc_id!=0):
                raise ValueError('Selected-pet objective requires a current owned fighting pet')
        elif evidence.kind == 'battle_won':
            if (task['type'] != 40 or not int(a.get('AIInfoAIID', 0))
                    or evidence.reference_id != int(a['AIInfoAIID'])
                    or int(a.get('AIInfoBattleResult', 0)) != 1):
                raise ValueError('Task battle result does not match')
        elif evidence.kind == 'scenario_finished':
            if (task['type'] != 50 or not int(a.get('ScenarioInfoAnimationID', 0))
                    or evidence.reference_id != int(a['ScenarioInfoAnimationID'])):
                raise ValueError('Task scenario does not match')
        elif evidence.kind == 'role_level_reached':
            if (not supports_level_gate(task) or not task['level']['min']<=actor.level<=155
                    or evidence.reference_id!=actor.level):
                raise ValueError('Task level goal has not been reached by the current role')
        elif evidence.kind == 'region_reached':
            position=evidence.region_position
            if (not supports_static_region(task) or evidence.map_id!=target['map_id']
                    or type(position) is not tuple or len(position)!=2
                    or any(type(v) is not int for v in position)
                    or type(evidence.region_version) is not int or evidence.region_version<=0):
                raise ValueError('Unsupported or unversioned region objective')
            left,top,right,bottom=(int(a[k])*16 for k in (
                'ActiveInfoLeftPos','ActiveInfoTopPos','ActiveInfoRightPos','ActiveInfoBottomPos'))
            if not left<=position[0]<right or not top<=position[1]<bottom:
                raise ValueError('Authoritative position is outside the original region')
        elif evidence.kind == 'master_card_chosen':
            # Only the dedicated durable chapter/card workflow emits this fact.
            # Generic NPC dialogue support deliberately remains unchanged.
            if (task['type']!=10 or not 20000<int(a.get('ScenarioInfoAnimationID',0))<20100
                    or evidence.reference_id!=int(a['ScenarioInfoAnimationID'])
                    or evidence.npc_id!=target['npc_id'] or evidence.map_id!=target['map_id']):
                raise ValueError('Master card selection does not match original task')
        elif evidence.kind == 'starter_weapon_equipped':
            if (task['type']!=59 or task['id'] not in (
                    100188,100288,100388,100488,100588,100688,100788,100888,100988,103288)
                    or type(evidence.reference_id) is not int or evidence.reference_id<=0):
                raise ValueError('Unsupported starter equipment objective')
        elif evidence.kind == 'newbie_cart_transfer_committed':
            # Only the dedicated task/world caller-transaction workflow emits
            # this after checking the approved policy and durable world receipt.
            if (task['type']!=10 or task['id'] not in (
                    100104,100203,100303,100403,100503,100603,100703,100803,100903,103204)
                    or evidence.npc_id!=target['npc_id'] or evidence.map_id!=target['map_id']
                    or int(a.get('RewardMapJumpType',0))!=1 or int(a.get('RewardMapID',0))!=1006
                    or evidence.reference_id!=1006 or int(a.get('ScenarioInfoAnimationID',0))!=0):
                raise ValueError('Unsupported first-cart durable transfer objective')
        elif evidence.kind == 'prologue_touch_transfer_committed':
            if (not supports_prologue_touch(task) or evidence.map_id!=target['map_id']
                    or evidence.npc_id!=target['npc_id'] or evidence.reference_id!=1501):
                raise ValueError('Blood handprint requires its timed durable world transfer')
        elif evidence.kind == 'prologue_puzzle_claim_accepted':
            if (not supports_prologue_puzzle(task) or evidence.map_id!=1501
                    or evidence.npc_id!=11106 or evidence.reference_id!=553):
                raise ValueError('Portrait puzzle requires its dedicated authorized client-claim workflow')
        elif evidence.kind == 'prologue_dream_return_committed':
            if (not supports_prologue_dream_return(task) or evidence.map_id!=1501
                    or evidence.npc_id!=target['npc_id'] or evidence.reference_id!=1006):
                raise ValueError('Dream return requires its approved durable world settlement')
        elif evidence.kind == 'prologue_first_skill_granted':
            if (not supports_prologue_first_skill(task) or evidence.map_id!=1501
                    or evidence.npc_id!=10908 or evidence.reference_id!=100008):
                raise ValueError('First skill requires its accepted teaching and owned ledger transaction')
        elif evidence.kind == 'npc_items_submitted':
            units=evidence.item_debits
            if (not supports_item_submission(task) or evidence.npc_id!=target['npc_id']
                    or evidence.map_id!=target['map_id'] or evidence.reference_id!=target['id']
                    or type(units) is not tuple or not units or len(units)>256
                    or any(type(x) is not tuple or len(x)!=2 or any(type(v) is not int or v<=0 for v in x) for x in units)
                    or len({key for key,_ in units})!=len(units)
                    or sum(amount for _,amount in units)!=target['count']):
                raise ValueError('Task item submission does not match original objective')
        else:
            raise ValueError('Unsupported authoritative task event')

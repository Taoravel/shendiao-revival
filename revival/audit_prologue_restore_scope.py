"""Read-only original prologue graph and current task capability inventory.

Predicate matches describe independent task support, never playable runtime or
GUI coverage. Traversal follows stored edges and explicit creation branches;
missing definitions remain missing instead of becoming invented terminals.
"""
from collections import Counter
import hashlib
import json
from inspect_client import OUT,write_json
import task_domain
from world_newbie import load_newbie_routes


PREDICATES=(
    'plain_dialogue','native_effect_dialogue','item_submission','money_submission',
    'static_region','npc_finish_dialogue','npc_start_dialogue','npc_empty_scenario',
    'fixed_npc_quiz','fighting_pet_task','level_gate','prologue_touch','prologue_puzzle',
)


def dream_return_inventory(tasks,routes):
    """Original facts only; inferred coordinates grant no runtime transfer."""
    families={10085:{},10140:{}}
    for route in routes:
        found=[]
        for index,q in enumerate(route['path']):
            task=tasks[q];npc=task['target']['npc_id']
            if task['type']!=10 or task['target']['map_id']!=1501 or npc not in families:
                continue
            if not index or len(task['next_ids'])!=1:
                raise ValueError('Dream return lacks an unambiguous original predecessor/successor')
            before=tasks[route['path'][index-1]];after=tasks[task['next_ids'][0]]
            jump=tuple(int(task['attributes'][k]) for k in
                ('RewardMapJumpType','RewardMapID','RewardMapXPos','RewardMapYPos'))
            expected=((3,1006,170,70),40,125,0) if npc==10085 else ((3,1006,335,144),59,450,450)
            if (jump!=expected[0] or before['type']!=expected[1]
                    or (task['display_rewards']['ExpReward'],task['display_rewards']['PetExpReward'])!=expected[2:]
                    or tuple(before['next_ids'])!=(q,) or after['type']!=10
                    or after['target']['map_id']!=1006):
                raise ValueError('Original dream-return research no longer matches source graph')
            families[npc][q]=dict(task_id=q,predecessor_id=before['id'],
                predecessor_type=before['type'],source=task['target'],original_jump=jump,
                original_rewards=task['display_rewards'],successor_id=after['id'],
                successor_target=after['target'],successor_rewards=after['display_rewards'],
                successor_reward_lists={k:v for k,v in after['lists'].items() if k.startswith('Reward')},
                inferred_logical_candidate=(jump[1],jump[2]*16,jump[3]*16),
                coordinate_status='raw-unit interpretation inferred; adopted conversion is designed in '
                    'design/newbie-dream-return-v1.json; this source inventory grants no authority')
            found.append((npc,q))
        if [npc for npc,q in found]!=[10085,10140]:
            raise ValueError('Each original route must contain both dream returns in order')
        route['original_dream_returns']=[q for npc,q in found]
    if any(len(rows)!=10 for rows in families.values()):
        raise ValueError('Original dream-return families must each contain exactly ten nodes')
    return [dict(source_npc_id=npc,nodes=[rows[q] for q in sorted(rows)])
        for npc,rows in families.items()]


def story_phase_inventory(tasks,routes,returns):
    """Retain every original node between CG1 and the second return, no skips."""
    return_ids={row['task_id'] for family in returns for row in family['nodes']}
    groups={};movies={10001:{},10002:{}}
    for route in routes:
        path=route['path'];marks=[]
        for index,q in enumerate(path):
            effect=int(tasks[q]['attributes'].get('ScenarioInfoAnimationID',0))
            if effect in movies:
                task=tasks[q];a=task['attributes']
                marks.append((index,'movie'+str(effect),q))
                movies[effect][q]=dict(task_id=q,predecessor_id=path[index-1],next_ids=task['next_ids'],
                    target=task['target'],original_rewards=task['display_rewards'],
                    original_jump=tuple(int(a.get(k,0)) for k in
                        ('RewardMapJumpType','RewardMapID','RewardMapXPos','RewardMapYPos')),
                    original_progress=int(a.get('ProcessBarTime',0)),
                    start_speakers=[line['speaker'] for line in task['dialogue']['start']],
                    finish_count=len(task['dialogue']['finish']),
                    display_npc_list_present='DisPlayNPCID' in task['lists'],
                    original_display_npc_ids=task['lists'].get('DisPlayNPCID'),
                    process_bar_color_present='ProcessBarColor' in a,
                    original_process_bar_color=a.get('ProcessBarColor'))
            elif q in return_ids:
                marks.append((index,'return'+str(tasks[q]['target']['npc_id']),q))
        if [kind for index,kind,q in marks]!=['movie10001','return10085','movie10002','return10140']:
            raise ValueError('Original CG/dream-return order is incomplete or changed')
        segment=tuple(path[marks[0][0]:marks[-1][0]+1])
        if segment not in groups:
            groups[segment]=dict(route_keys=[],path=segment,
                milestones=[dict(kind=kind,task_id=q) for index,kind,q in marks],
                formal_battle_gates=[dict(task_id=q,ai_id=int(tasks[q]['attributes']['AIInfoAIID']))
                    for q in segment if tasks[q]['type']==40])
        groups[segment]['route_keys'].append((route['character_id'],route['school_id']))
    if any(len(rows)!=10 for rows in movies.values()):
        raise ValueError('Expected exactly ten original nodes for each movie family')
    return dict(segments=list(groups.values()),
        original_movie_families=[dict(movie_id=effect,nodes=[rows[q] for q in sorted(rows)])
            for effect,rows in movies.items()],
        interpretation='Original configured effects/edges only; no playback ACK, transfer conversion or battle success inferred')


def main():
    catalog_path=OUT/'catalogs/tasks.json'
    tasks={t['id']:t for t in json.loads(catalog_path.read_text(encoding='utf-8'))['missions']}
    masters=json.loads((OUT/'catalogs/newbie-master-cards.json').read_text(encoding='utf-8'))['routes']
    master_by_route={(m['character_id'],m['school_id']):m for m in masters}
    routes=load_newbie_routes()
    rows=[];nodes={}
    for key,route in sorted(routes.items()):
        master=master_by_route[key]
        if master['master_task_id']!=route.successor_task_id:
            raise ValueError('Original creation/master route snapshots disagree')
        current=route.intro_task_id;path=[];seen=set();stop=None
        while current in tasks and current not in seen:
            seen.add(current);path.append(current);task=tasks[current]
            if current not in nodes:
                a=task['attributes']
                matches=[name for name in PREDICATES
                    if getattr(task_domain,'supports_'+name)(task)]
                nodes[current]=dict(task_id=current,type=task['type'],target=task['target'],
                    next_ids=task['next_ids'],independent_predicate_matches=matches,
                    original_effect=int(a.get('ScenarioInfoAnimationID',0)),
                    original_progress=int(a.get('ProcessBarTime',0)),
                    original_jump=tuple(int(a.get(k,0)) for k in
                        ('RewardMapJumpType','RewardMapID','RewardMapXPos','RewardMapYPos')),
                    original_battle_ai=int(a.get('AIInfoAIID',0)),
                    original_rewards=task['display_rewards'],original_reward_items=task['display_items'],
                    original_reward_lists={k:v for k,v in task['lists'].items() if k.startswith('Reward')})
            edges=tuple(task['next_ids'])
            if current==route.intro_task_id:
                if route.successor_task_id not in edges:
                    raise ValueError('Selected original master is not an intro edge')
                current=route.successor_task_id
            elif len(edges)==1:
                current=edges[0]
            else:
                stop='no_successor' if not edges else 'branch_requires_policy'
                break
        if stop is None:
            stop='definition_missing' if current not in tasks else 'cycle'
        rows.append(dict(character_id=key[0],school_id=key[1],path=path,
            stop=dict(task_id=current,reason=stop)))
    dream_returns=dream_return_inventory(tasks,rows)
    story_phases=story_phase_inventory(tasks,rows,dream_returns)
    effects=Counter(n['original_effect'] for n in nodes.values() if n['original_effect'])
    report=dict(route_count=len(rows),unique_original_nodes=len(nodes),
        original_types=dict(sorted(Counter(n['type'] for n in nodes.values()).items())),
        original_effects=dict(sorted(effects.items())),
        missing_definitions=sorted({r['stop']['task_id'] for r in rows if r['stop']['reason']=='definition_missing'}),
        nodes=[nodes[q] for q in sorted(nodes)],routes=rows,
        original_dream_return_families=dream_returns,
        original_story_phase_inventory=story_phases,
        gated_candidate_modules=[dict(module='task_prologue_return',
            task_ids=sorted(q for q,t in tasks.items() if task_domain.supports_prologue_dream_return(t)),
            delivery='evidence/task-dream-return-settlement-delivery.json',
            status='both isolated task contracts and actual World paid/recovery verified; actual AI, shared runtime and GUI unverified',
            shared_wiring_approved=False),dict(module='task_first_skill',
            task_ids=sorted(q for q,t in tasks.items() if task_domain.supports_prologue_first_skill(t)),
            delivery='evidence/task-first-skill-delivery.json',
            status='isolated teaching/complete class6 ledger/native consumer and paid current result verified; actual AI, shared runtime and GUI unverified',
            shared_wiring_approved=False)],
        source_catalog_sha256=hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        interpretation='Original graph plus independent predicate inventory; no runtime or GUI success inferred',
        known_special_modules=['task_newbie_chapter','task_master_card','task_cart_dialogue',
            'task_prologue_touch','task_prologue_puzzle'],
        methods={'codebase-design':'Inventory the actual task Interface rather than infer support from MissionType',
            'research':'Follow stored original Post edges and explicit creation-selected master; preserve missing records'},
        live_server_changed=False,client_launched=False,battle_executed=False,
        limits=['Reuses audited catalogs, does not re-extract PFS in this run',
            'Predicate matches do not prove activation, shared hooks, rewards, visibility or native GUI',
            'Full prologue completion remains unproven; missing terminal records remain unresolved'])
    write_json(OUT/'evidence/prologue-restore-scope.json',report)
    print({k:report[k] for k in ('route_count','unique_original_nodes','original_types','original_effects','missing_definitions')})


if __name__=='__main__':main()

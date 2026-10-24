"""Original Post stops and Request references, never runtime continuation.

The existing43 route walks stop at missing definitions. This audit preserves
those stops and inventories additional original records which REFER to them.
It does not infer OR/AND, create terminal quests, stamp markers or activate any
task. Direct original PFS records must match the saved catalog.
"""
from collections import Counter
import hashlib
import json
from inspect_client import OUT,ROOT,catalog_rows,write_json
from pfs import PfsArchive
from bxml import decode
from world_newbie import load_newbie_routes


def _sha(data):return hashlib.sha256(data).hexdigest()


def main():
    catalog_bytes=(OUT/'catalogs/tasks.json').read_bytes()
    tasks={t['id']:t for t in json.loads(catalog_bytes)['missions']}
    scope_bytes=(OUT/'evidence/prologue-restore-scope.json').read_bytes()
    scope=json.loads(scope_bytes)
    if scope['source_catalog_sha256']!=_sha(catalog_bytes) or len(scope['routes'])!=43:
        raise ValueError('Current original43 Post inventory must match task catalog')
    archive=PfsArchive(ROOT/'artres/config.pfs')
    member='autoconfig/knight.gsp.task.cmainmissioninfo.xml'
    raw=archive.read(member)
    original={int(t['attributes']['id']):t for t in catalog_rows(decode(raw))}
    if set(original)!=set(tasks):raise ValueError('Original task IDs differ from catalog')
    for q,t in tasks.items():
        if original[q]['attributes']!=t['attributes'] or original[q]['lists']!=t['lists']:
            raise ValueError('Original task fields/lists differ from saved catalog')
    def facts(q):
        t=tasks[q]
        return dict(task_id=q,name=t['name'],type=t['type'],target=t['target'],
            original_request_ids=t['request_mission_ids'],original_post_ids=t['next_ids'],
            original_rewards=t['display_rewards'],original_reward_items=t['display_items'],
            original_jump={k:t['attributes'].get(k) for k in
                ('RewardMapJumpType','RewardMapID','RewardMapXPos','RewardMapYPos')},
            original_animation=t['attributes'].get('ScenarioInfoAnimationID'),
            original_ai=t['attributes'].get('AIInfoAIID'))
    request_index={}
    for q,t in tasks.items():
        for value in t['request_mission_ids']:request_index.setdefault(value,[]).append(q)
    missing=sorted({p for t in tasks.values() for p in t['next_ids'] if p not in tasks})
    markers=scope['missing_definitions'];groups=[];additional=set();routes=load_newbie_routes()
    for marker in markers:
        if marker in tasks:raise ValueError('A previously missing stop now has an original definition')
        all_refs=sorted(request_index.get(marker,()))
        single_refs=[q for q in all_refs if tasks[q]['request_mission_ids']==[marker]]
        chains=[]
        for start in single_refs:
            path=[];q=start;reason=None
            while q in tasks and q not in path:
                path.append(q);edges=tasks[q]['next_ids']
                if len(edges)!=1:
                    reason='no_post' if not edges else 'multiple_posts';break
                q=edges[0]
            if reason is None:reason='definition_missing' if q not in tasks else 'cycle'
            additional.update(path)
            chains.append(dict(referencing_task_id=start,path=path,
                stop=dict(task_id=q,reason=reason),
                later_request_references=[facts(n) for n in sorted(request_index.get(q,()))]))
        matched=[]
        for row in scope['routes']:
            if row['stop']!={'task_id':marker,'reason':'definition_missing'}:continue
            key=(row['character_id'],row['school_id']);route=routes[key]
            matched.append(dict(character_id=key[0],school_id=key[1],
                original_last_defined_task=row['path'][-1],home_map_id=route.home_map_id))
        groups.append(dict(missing_post_id=marker,
            actual_defined_incoming_tasks=[facts(q) for q,t in tasks.items() if marker in t['next_ids']],
            request_reference_tasks=[facts(q) for q in all_refs],
            single_requirement_reference_chains=chains,original_creation_routes=matched))
    original_nodes={n['task_id'] for n in scope['nodes']}
    extra=additional-original_nodes
    if len(groups)!=10 or len(extra)!=88 or sum(len(g['original_creation_routes']) for g in groups)!=43:
        raise ValueError('Original prologue reference inventory changed; inspect literal edges')
    report=dict(source_status='client_verified original fields and literal graph references only',
        original_member=dict(path=member,length=len(raw),crc32=f'{archive.entries[member].crc:08x}',
            sha256=_sha(raw),length_crc_verified=True),
        source_catalog_sha256=_sha(catalog_bytes),prior_post_scope_sha256=_sha(scope_bytes),
        prior_post_only_unique_nodes=len(original_nodes),additional_reference_chain_nodes=len(extra),
        union_original_catalog_nodes=len(original_nodes|additional),groups=groups,
        additional_original_nodes=[facts(q) for q in sorted(extra)],
        additional_types=dict(sorted(Counter(tasks[q]['type'] for q in extra).items())),
        global_missing_post_ids=missing,
        global_missing_post_suffix99_count=sum(q%100==99 for q in missing),
        global_missing_post_other_ids=[q for q in missing if q%100!=99],
        interpretation='Post graph and Request reference relations are different facts. Missing IDs remain undefined; candidate reference chains do not grant automatic transition.',
        request_list_or_and_semantics='unconfirmed',server_marker_write_rule='unconfirmed',
        terminal_definition_created=False,marker_written=False,task_activated=False,
        shared_runtime_wired=False,live_server_changed=False,native_gui_verified=False,battle_executed=False,
        methods={'research':'Direct PFS CRC/length plus complete field/list match, exact source Post/Request join; independent native boundary research separate',
            'codebase-design':'Inventory missing source boundaries separately from possible server continuation/activation policy'})
    write_json(OUT/'evidence/prologue-stage-reference-inventory.json',report)
    print({k:report[k] for k in ('prior_post_only_unique_nodes','additional_reference_chain_nodes',
        'union_original_catalog_nodes','additional_types','global_missing_post_suffix99_count','global_missing_post_other_ids')})


if __name__=='__main__':main()

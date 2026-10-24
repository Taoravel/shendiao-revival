"""Audit all task NPC references against current public domain predicates.

Static reference and predicate coverage are distinct from authoritative task
activation, shared routing, dynamic visibility, deployment and GUI evidence.
Only a disposable task store is opened; no runtime/service is started.
"""
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import tempfile

from accounts import AccountStore
from inspect_client import OUT,write_json
import task_domain
from tasks import prepare_task_store
from world_npcs import load_placements,load_npc_definitions


PREDICATES=('supports_plain_dialogue','supports_item_submission','supports_static_region',
    'supports_native_effect_dialogue','supports_npc_finish_dialogue','supports_npc_start_dialogue',
    'supports_npc_empty_scenario','supports_fixed_npc_quiz','supports_money_submission',
    'supports_fighting_pet_task','supports_level_gate','supports_prologue_touch',
    'supports_prologue_puzzle','supports_prologue_dream_return','supports_prologue_first_skill')
ATTRIBUTE_REFERENCES=('ScenarioInfoFinishNpcID','ScenarioInfoBranchNpcID',
    'QuestionInfoNpcID','ActiveInfoNpcID')
LIST_REFERENCES=('DisPlayNPCID','ScenarioInfoNpcID','ScenarioInfoFinishNpcID')
INPUTS=('audit_npc_task_coverage.py','accounts.py','tasks.py','task_domain.py',
    'task_conversation.py','task_chains.py','world_npcs.py','catalogs/tasks.json',
    'catalogs/world.json','catalogs/knight.gsp.npc.cnpcconfig.json',
    'catalogs/knight.gsp.role.createroleconfig.json')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    hashes={name:sha(OUT/name) for name in INPUTS}
    original=json.loads((OUT/'catalogs/tasks.json').read_text(encoding='utf8'))['missions']
    if len({row['id'] for row in original})!=len(original):
        raise ValueError('Duplicate source task IDs would be lost by startup loading')
    places=load_placements();definitions=load_npc_definitions()
    by_npc=defaultdict(list)
    for entries in places.values():
        for placement in entries:
            by_npc[placement.npc_id].append(dict(map_id=placement.map_id,
                placement_id=placement.placement_id,x=placement.x,y=placement.y))
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'npc-task-reference-audit.sqlite3')
        tasks=prepare_task_store(store).definitions
    assert set(tasks)=={row['id'] for row in original}
    references=defaultdict(lambda:defaultdict(set))
    rows=[];capabilities=Counter();types=Counter();target_gaps=[]
    for ident,task in sorted(tasks.items()):
        matches=[name for name in PREDICATES if getattr(task_domain,name)(task)]
        capabilities.update(matches);types[task['type']]+=1
        target_npc=task['target']['npc_id'];target_map=task['target']['map_id']
        if target_npc>0:references[target_npc]['target'].add(ident)
        display_ids=tuple(map(int,task['lists'].get('DisPlayNPCID',())))
        for name in LIST_REFERENCES:
            for npc in map(int,task['lists'].get(name,())):
                if npc>0:references[npc][name].add(ident)
        for name in ATTRIBUTE_REFERENCES:
            npc=int(task['attributes'].get(name,0))
            if npc>0:references[npc][name].add(ident)
        target_places=by_npc.get(target_npc,())
        matching=tuple(p['placement_id'] for p in target_places if p['map_id']==target_map)
        gap=(target_npc>0 and target_map>0 and not matching)
        row=dict(task_id=ident,type=task['type'],target_npc_id=target_npc,target_map_id=target_map,
            target_definition_present=target_npc in definitions,display_npc_ids=display_ids,
            target_static_placement_ids_in_target_map=matching,
            target_static_placements_anywhere=list(target_places),
            public_domain_predicate_matches=matches,
            not_classified_by_these_predicates=not matches,
            shared_runtime_and_deployment_status='not_proven_by_this_audit')
        rows.append(row)
        if gap:target_gaps.append(row)
    npc_rows=[]
    for npc,roles in sorted(references.items()):
        npc_rows.append(dict(npc_id=npc,definition_present=npc in definitions,
            name=definitions.get(npc,{}).get('name'),static_placements=by_npc.get(npc,()),
            task_reference_roles={name:sorted(ids) for name,ids in sorted(roles.items())},
            distinct_referencing_tasks=len(set().union(*roles.values()))))
    # Complete partition checks guard accidental omission while preserving
    # overlapping domain predicates and multiple roles per NPC/task.
    assert len(rows)==len(tasks) and len({r['task_id'] for r in rows})==len(tasks)
    assert sum(types.values())==len(tasks)
    assert all(set(ids)<=set(tasks) for roles in references.values() for ids in roles.values())
    for name,digest in hashes.items():
        if sha(OUT/name)!=digest:raise RuntimeError('Source changed during NPC task audit: '+name)
    summary=dict(tasks=len(rows),task_types=dict(sorted(types.items())),
        tasks_with_positive_target_npc=sum(row['target_npc_id']>0 for row in rows),
        tasks_matched_by_at_least_one_public_predicate=sum(bool(row['public_domain_predicate_matches']) for row in rows),
        tasks_not_classified_by_these_predicates=sum(row['not_classified_by_these_predicates'] for row in rows),
        public_predicate_counts=dict(sorted(capabilities.items())),
        distinct_positive_source_reference_values=len(npc_rows),
        source_reference_values_without_npc_definition=sum(not row['definition_present'] for row in npc_rows),
        source_reference_values_without_static_placement=sum(not row['static_placements'] for row in npc_rows),
        tasks_with_positive_target_npc_and_map_without_matching_static_placement=len(target_gaps),
        static_gap_tasks_matched_by_a_public_predicate=sum(bool(row['public_domain_predicate_matches']) for row in target_gaps),
        static_gap_tasks_with_target_placed_on_another_map=sum(bool(row['target_static_placements_anywhere']) for row in target_gaps),
        static_gap_tasks_with_target_without_any_static_placement=sum(not row['target_static_placements_anywhere'] for row in target_gaps))
    report=dict(scope='current workspace task resources, all references and public capability predicates; not runtime completion',
        source_sha256=hashes,predicates=list(PREDICATES),summary=summary,npc_references=npc_rows,
        tasks=rows,target_static_gaps=target_gaps,
        caveats=['A predicate match is not an accepted task or shared route/deployment proof.',
            'Predicates overlap; unmatched tasks may belong to other dedicated Modules.',
            'A missing static placement may require dynamic or private content; never fabricate one.',
            'Attribute/list references preserve source roles; they do not automatically grant interaction.',
            'Unresolved source reference values may be placeholders or flags rather than NPC identities.',
            'Dialogue speaker1 is a local player symbol, not a missing NPC spawn.',
            'Targets/map0 and placeholder IDs remain original values, not inferred spawns.'],
        live_database_accessed=False,runtime_started=False,deployed=False,native_gui_verified=False)
    write_json(OUT/'evidence/npc-task-coverage-audit.json',report)
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()

"""Compile the actual NPC registry in disposable storage; audit all original IDs.

Registry coverage is not a runtime/GUI completion claim. NPCs without generic
bindings may still own task dialogs; client scenery is a separate lifecycle.
"""
from collections import Counter,defaultdict
from contextlib import closing
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile

from accounts import AccountStore
from inspect_client import OUT,write_json
import runtime_storage


def main():
    watched=('audit_npc_service_integration.py','npc_services.py','npc_gameplay.py','npc_recovery.py','npc_repairs.py','runtime_storage.py','inventory.py',
             'npc_shop_sales.py','npc_depot.py','npc_shop_payments.py','npc_role_healing.py',
             'role_resource_plan.py','currency.py','npc_interaction.py','world_npcs.py','npc_lifecycle.py',
             'design/npc-services-v1.json','design/npc-interaction-v1.json','design/npc-interaction-v2.json',
             'design/npc-shop-payments-v1.json','design/npc-role-healing-v1.json',
             'design/npc-pet-loyalty-v2.json',
             'design/role-resources-v1.json','design/currency-v1.json',
             'catalogs/knight.gsp.npc.cnpcserverconfig.json','catalogs/knight.gsp.npc.cnpcconfig.json',
             'catalogs/knight.gsp.item.npcsellitem.json','catalogs/knight.gsp.item.citemattr.json','catalogs/world.json')
    hashes={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in watched}
    with tempfile.TemporaryDirectory() as temp:
        store=AccountStore(Path(temp)/'npc-audit.sqlite3');prepared=runtime_storage.prepare(store)
        resources=store.npc_gameplay;services=resources.services
        by_npc=defaultdict(list);by_service=defaultdict(list);roots=defaultdict(list)
        for binding in services.bindings.values():
            by_npc[binding.npc_id].append(asdict(binding));by_service[binding.service_id].append(binding.npc_id)
        for npc_id,menu in services.menus.items():
            for service_id in menu:
                if (npc_id,service_id) not in services.bindings:roots[service_id].append(npc_id)
        placements=defaultdict(list);filtered=[];interaction_rules=getattr(store,'npc_interaction_rules',None)
        for places in store.npc_resources[0].values():
            for p in places:
                scene=prepared[3].get(p.map_id)
                eligible=(scene is not None and 0<=p.x<min(scene['width'],32768)
                          and 0<=p.y<min(scene['height'],32768) and p.npc_id in store.npc_resources[1])
                placements[p.npc_id].append({**asdict(p),'startup_coordinate_eligible':eligible,
                    'configured_interaction_distance_mode':None if interaction_rules is None else interaction_rules.distance_mode,
                    'configured_interaction_radius':None if interaction_rules is None or interaction_rules.default_radius is None
                        else interaction_rules.radius_for(p.map_id,p.placement_id,p.npc_id)})
                if not eligible:filtered.append(asdict(p))
        definitions=[]
        for npc_id,definition in sorted(store.npc_resources[1].items()):
            definitions.append({'npc_id':npc_id,'name':definition.get('name',''),
                'original_hide_mode':int(definition['hide']),
                'static_placements':placements.get(npc_id,[]),
                'generic_action_bindings':sorted(by_npc.get(npc_id,[]),key=lambda r:r['service_id']),
                'display_menu_ids':services.menus.get(npc_id,()),'task_dialog_coverage':'not_audited_here'})
        service_rows=[];missing=[]
        for service_id,label in sorted(services.labels.items()):
            children=services.children.get(service_id,())
            for child in children:
                if child not in services.labels:missing.append({'parent':service_id,'child':child})
            if service_id in by_service:classification='registered_action'
            elif service_id in roots:classification='registered_local_display_root'
            elif service_id in (10001,10002,10003,10004):classification='original_local_navigation'
            elif children:classification='original_local_parent_not_registered'
            else:classification='original_leaf_without_explicit_generic_binding'
            service_rows.append({'service_id':service_id,'label':label,'childservice':children,
                'classification':classification,'action_npc_ids':sorted(by_service.get(service_id,())),
                'display_root_npc_ids':sorted(roots.get(service_id,()))})
        unsupported_shop=[]
        for npc_id,items in resources.stock.items():
            unknown=tuple(item for item in items if item not in resources.prices)
            if unknown:unsupported_shop.append({'npc_id':npc_id,'not_currently_purchasable_template_ids':unknown})
        counts=Counter(row['classification'] for row in service_rows)
        unplaced=tuple(row['npc_id'] for row in definitions if row['generic_action_bindings']
                       and not any(p['startup_coordinate_eligible'] for p in row['static_placements']))
        with closing(store.connect()) as db:
            assert db.execute('PRAGMA quick_check').fetchone()==('ok',)
        report={'scope':'current workspace startup registry in disposable DB; not deployed/GUI coverage',
            'source_status':'client_verified catalogs plus explicit designed/guided bindings',
            'npc_policy_revision':resources.revision,'source_sha256':hashes,
            'interaction_distance_policy':None if interaction_rules is None else asdict(interaction_rules),
            'summary':{'original_npc_definitions':len(definitions),'original_services':len(service_rows),
                'map_records':len(store.npc_resources[0]),
                'maps_with_static_npcs':sum(bool(ps) for ps in store.npc_resources[0].values()),
                'empty_map_records':sum(not ps for ps in store.npc_resources[0].values()),
                'static_placements':sum(map(len,placements.values())),
                'generic_action_bindings':len(services.bindings),'npcs_with_generic_actions':len(by_npc),
                'distinct_registered_action_ids':len(by_service),'local_display_roots':dict(roots),
                'original_definition_hide_mode_counts':dict(sorted(Counter(row['original_hide_mode'] for row in definitions).items())),
                'original_static_placement_hide_mode_counts':dict(sorted(Counter(
                    row['original_hide_mode'] for row in definitions for placement in row['static_placements']).items())),
                'generic_bound_npc_hide_mode_counts':dict(sorted(Counter(
                    row['original_hide_mode'] for row in definitions if row['generic_action_bindings']).items())),
                'action_binding_counts':{sid:len(ids) for sid,ids in sorted(by_service.items())},
                'configured_npcs_without_static_placements':len(unplaced),
                'service_classifications':dict(counts),'missing_child_references':missing,
                'filtered_static_placements':len(filtered),'shops_with_unaccepted_price_rows':len(unsupported_shop)},
            'npcs':definitions,'services':service_rows,'filtered_static_placements':filtered,
            'configured_npc_ids_without_static_placements':unplaced,
            'shops_with_unaccepted_prices':unsupported_shop,'live_database_modified':False,
            'task_coverage_included':False,'native_gui_verified':False,
            'dynamic_npc_runtime_coverage_inferred':False}
    if any(hashlib.sha256((OUT/name).read_bytes()).hexdigest()!=digest for name,digest in hashes.items()):
        raise RuntimeError('NPC source/config changed during audit; rerun against one coherent registry')
    write_json(OUT/'evidence/npc-service-integration-audit.json',report)
    print(json.dumps(report['summary'],ensure_ascii=False))


if __name__=='__main__':main()

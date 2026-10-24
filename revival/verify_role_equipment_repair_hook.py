"""Exercise the actual shared precommit projection with the NPC fault fixture.

Reuses its real inventory/lease/repair setup and adversarial assertions. The
additional oracle is the shared runtime_storage hook, not another calculator.
No production source is replaced; scoped patches select the test dependency.
"""
from unittest.mock import patch

from inspect_client import OUT,write_json
from role_equipment import load_equipment_attribute_rules
import npc_repairs
import runtime_storage
import verify_npc_repair_projection as fixture


def main():
    original=npc_repairs.repair
    rules=load_equipment_attribute_rules()
    entered=[]

    def repair_with_shared_projection(accounts,inventory,intent,precommit=None,*,draw_source):
        # The reused fixture prepares only relevant domain dependencies. Supply
        # the same immutable startup dependency that real prepare injects.
        accounts.equipment_attribute_rules=rules

        def project(db,current_inventory,snapshot):
            assert db.in_transaction
            entered.append(snapshot.inventory_revision)
            actual=runtime_storage.equipment_projection_messages(db,accounts,current_inventory,snapshot)
            expected=precommit(db,current_inventory,snapshot)
            assert actual==expected, 'Shared projection differs from the independent fixture oracle'
            return actual

        return original(accounts,inventory,intent,project,draw_source=draw_source)

    with patch.object(npc_repairs,'repair',repair_with_shared_projection):
        fixture.main()
    assert len(entered)==4, 'Shared hook did not cover late failure, success, replay and float refusal'
    report=dict(passed=[
        'actual runtime_storage.equipment_projection_messages reads the repair caller transaction',
        'broken0 to repaired equipped weapon restores45/35/19 and preservesHP70/MP40',
        'real shared full-map encoding precedes the late injected failure; cash/condition/receipts roll back',
        'successful same-key retry and later committed replay use current projection without redrawing',
        'shared float32 refusal at seal16777217 rolls back repair and cash'],
        shared_projection_hook_verified=True,owner_wire_route_verified=False,
        dependency_scope='NPC domain fixture plus actual shared projection hook; full startup and first-master Owner verified separately',
        database='disposable',native_gui_verified=False,live_server_changed=False,battle_executed=False)
    write_json(OUT/'evidence/role-equipment-repair-hook-verification.json',report)
    print(report)


if __name__=='__main__':
    main()

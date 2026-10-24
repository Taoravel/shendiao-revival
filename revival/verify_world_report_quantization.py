"""The native legal rounded CHECK must not become an integer-DDA rejection."""
import json
import struct
from inspect_client import OUT,write_json
from world_collision import maze_segment_result
from world_grids import SceneGrid
from world_movement import CHECK_MOVE,ROLE_STOP,decode_movement
from world_owner import MapAddress,MapOwner,Location,MoveCommand


def main():
    original=json.loads((OUT/'evidence/movement-reports-native.json').read_text(encoding='utf-8'))
    case=next(c for c in original['cases'] if c['case']=='original_clear_leg_quantized_check_false_rejection')
    body=bytes.fromhex(case['sent']['body_hex'])
    assert body.hex()=='003c004a01001800581122334455667788'
    assert decode_movement(CHECK_MOVE,body)[:2]==((60,74),((24,88),(60,74)))
    values=bytearray(36);values[4*6+2]=1
    maze=SceneGrid(6,6,bytes(values),12)
    assert maze_segment_result(maze,(25,88),(73,70),mask=1)==0
    assert maze_segment_result(maze,(25,88),(60,74),mask=1)==1
    assert maze_segment_result(maze,(24,88),(60,74),mask=1)==1
    catalog={7:dict(available=True,width=96,height=96,portals={})}
    address=MapAddress(7,1,0)
    owner=MapOwner(address,catalog,capacity=1,transfer_capacity=1,mailbox_capacity=1,maze=maze)
    location=owner.join(Location(1,'native-rounding',address,1,25,88))
    result=owner.move(MoveCommand(location,'native-check',100,CHECK_MOVE,body,movement_state=0),1)
    assert not result.rejection and result.location.position==(7,60,74)
    # This does not disable verified node collision: a point inside the actual
    # wall must still fail without changing the accepted position/version.
    blocked=b'\0'+struct.pack('>hhQ',40,72,0)
    denied=owner.move(MoveCommand(result.location,'wall-node',100,ROLE_STOP,blocked,movement_state=0),2)
    assert denied.rejection=='Movement enters blocked maze cell' and owner.location(1)==result.location
    report=dict(original_native_case=case['case'],native_original_leg_clear=True,
        native_rounded_subsegment_blocked=True,actual_CHECK=body.hex(),
        legal_report_not_rejected_by_integer_reconstruction=True,blocked_node_still_refused=True,
        continuous_collision_complete=False,
        missing='quantization-aware authoritative movement reconciliation, special modes, speed',
        gui_verified=False,client_launched=False,live_server_changed=False)
    write_json(OUT/'evidence/world-report-quantization-verification.json',report)
    print(report)


if __name__=='__main__':
    main()

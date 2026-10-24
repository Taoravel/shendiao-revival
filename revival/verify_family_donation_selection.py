"""Selected original item keys stay selected across the two donation owners."""
from contextlib import closing
import tempfile
import family_donation as donation
from verify_family_donation import setup,encode
from inventory import AssetChange
import faction_protocol as family_wire
import json,struct
from dataclasses import replace,FrozenInstanceError
from inspect_client import OUT,write_json
import family_donation_protocol as protocol
from task_item_protocol import NpcItemSubmission,encode_npc_item_submission


def check_selected(directory):
    f,family,inv=setup(directory)
    f.tx(1,lambda db:inv.apply_settlement(db,AssetChange('fixture-select-boxes',grants=((36076,2,0),(36201,1,1)))))
    items=inv.immutable_snapshot().items
    chosen=next(i for i in items if i.template_id==36076)
    window=protocol.DonationWindow(731,2**40+10055,0,0)
    incoming=encode_npc_item_submission(NpcItemSubmission(731,window.npc_key,0,((chosen.id,1),)))
    selected=protocol.decode_submission(incoming,window,maximum_count=f.org.donation_rules.batch_limit)
    units=selected.units
    command=f.cmd(1,family,'reserve_family_donation',(sum(q for _,q in units),units))
    f.org.execute(command,f.now())
    paid=f.tx(1,lambda db:donation.pay(db,1111,1,f.epochs[1],family,command.request_id,f.now(),
        f.org.donation_rules,inv,precommit=encode))
    assert paid.items==((chosen.id,36076,0,1),)
    assert sorted((i.template_id,i.quantity) for i in inv.immutable_snapshot().items)==[(36076,1),(36201,1)]
    f.org.execute(f.cmd(1,family,'resolve_family_donation',(command.request_id,)),f.now())
    result=f.org.family_donation_receipt(family,1,command.request_id)
    assert (result.funds_after,result.construction_after,result.prestige_after)==(3100000,1,(5,5))


def check_scene_identity():
    original=family_wire.FamilyView(123,'测试家族','同心协力','创始人',1,3000000)
    view=family_wire.family_scene_view(original,2**40+1401)
    assert view.family_scene_identity==2**40+1401 and original.unbound_identity==0
    assert family_wire.family_update(view)[-9:-1]==(2**40+1401).to_bytes(8,'big')
    for value in (True,-1,2**63,None):
        try:family_wire.family_scene_view(original,value)
        except ValueError:pass
        else:raise AssertionError('Invalid scene identity accepted')


def check_window():
    window=protocol.DonationWindow(731,2**40+10055,0,0)
    request=NpcItemSubmission(731,2**40+10055,0,((12345,3),(67890,2)))
    wire=encode_npc_item_submission(request)
    assert protocol.decode_submission(wire,window,maximum_count=100)==request
    assert protocol.prompt(window)[0]==0xc233f
    assert protocol.prompt(window)[1]==struct.pack('>iQi',731,2**40+10055,0)+b'\x02'+struct.pack('>iii',36076,36201,0)
    try:window.context_id=732
    except FrozenInstanceError:pass
    else:raise AssertionError('Server window was mutable')
    for other in (replace(request,task_id=732),replace(request,npc_key=request.npc_key+1),replace(request,submit_type=1)):
        try:protocol.decode_submission(encode_npc_item_submission(other),window,maximum_count=100)
        except ValueError:pass
        else:raise AssertionError('Different window was accepted')
    for units in ((),((1,1),(1,1)),tuple((i,1) for i in range(1,7)),((1,101),)):
        try:protocol.decode_submission(encode_npc_item_submission(replace(request,units=units)),window,maximum_count=100)
        except ValueError:pass
        else:raise AssertionError('Invalid selected units accepted')
    for body in (wire[:-1],wire+b'\0',bytearray(wire)):
        try:protocol.decode_submission(body,window,maximum_count=100)
        except ValueError:pass
        else:raise AssertionError('Malformed/mutable body accepted')


def check_no_substitution(directory):
    f,family,inv=setup(directory)
    f.tx(1,lambda db:inv.apply_settlement(db,AssetChange('fixture-choice-stock',grants=((36076,2,0),(36201,2,1),(36747,1,0)))))
    original=inv.immutable_snapshot();box=next(i for i in original.items if i.template_id==36076)
    other=next(i for i in original.items if i.template_id==36747)
    for units in (((box.id,3),),((other.id,1),),((0x7fffffff,1),)):
        command=f.cmd(1,family,'reserve_family_donation',(sum(q for _,q in units),units))
        f.org.execute(command,f.now())
        f.reject(lambda:f.tx(1,lambda db:donation.pay(db,1111,1,f.epochs[1],family,command.request_id,f.now(),
            f.org.donation_rules,inv,precommit=encode)),'selected_box_unavailable')
        assert inv.immutable_snapshot()==original
        f.org.execute(f.cmd(1,family,'resolve_family_donation',(command.request_id,)),f.now())
    for args in ((1,()),(1,((box.id,1),(box.id,1))),(2,((box.id,1),)),(1,((True,1),))):
        f.reject(lambda args=args:f.org.execute(f.cmd(1,family,'reserve_family_donation',args),f.now()),'family_donation_selected')
    assert f.org.family_assets(family).funds==3000000


def check_persisted_selection(directory):
    f,family,inv=setup(directory)
    f.tx(1,lambda db:inv.apply_settlement(db,AssetChange('fixture-persist-choice',grants=((36076,3,0),(36201,1,1)))))
    box=next(i for i in inv.immutable_snapshot().items if i.template_id==36076)
    units=((box.id,2),);command=f.cmd(1,family,'reserve_family_donation',(2,units))
    f.org.execute(command,f.now());f.org.initialize()
    paid=f.tx(1,lambda db:donation.pay(db,1111,1,f.epochs[1],family,command.request_id,f.now(),f.org.donation_rules,inv,precommit=encode))
    current=inv.immutable_snapshot();again=f.tx(1,lambda db:donation.pay(db,1111,1,f.epochs[1],family,command.request_id,f.now(),f.org.donation_rules,inv,precommit=encode))
    assert again==paid and again.inventory==current
    f.reject(lambda:f.org.execute(replace(command,args=(1,((box.id,1),))),f.now()),'request_id_conflict')
    f.org.execute(f.cmd(1,family,'resolve_family_donation',(command.request_id,)),f.now())
    assert f.org.family_donation_receipt(family,1,command.request_id).count==2


if __name__=='__main__':
    check_scene_identity();check_window()
    for check in (check_selected,check_no_substitution,check_persisted_selection):
        with tempfile.TemporaryDirectory() as directory:check(directory)
    result=dict(passed=['server-window decode to family reserve, role payment and family settlement retains explicitly selected native keys',
        'exact selection persists across startup and repeated payment without another debit',
        'selected shortage, foreign template or missing key cannot consume another available box',
        'duplicate/malformed/mutable/over-five selection and inconsistent count are refused',
        'server-owned window context/NPC/type must all match; no historical mode is guessed',
        'explicit silver-box prompt retains original generic wire shape and unknown opaque value',
        'FamilyView legacy tail-Q constructor stays compatible while exposing family_scene_identity',
        'family scene projection preserves full signed63 identity; malformed identities are rejected'],
        live_server_changed=False,native_gui_verified=False,npc_service296_registered=False,
        organization_admission_policy_implemented=False,historical_server_window_values_verified=False)
    write_json(OUT/'evidence/family-donation-selection-verification.json',result);print(json.dumps(result))

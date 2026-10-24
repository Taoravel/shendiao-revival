"""NPC service seam: trusted map proof -> immutable owner command, no assets."""
import struct
import unittest
from dataclasses import replace
from npc_services import NpcServices, ServiceBinding, load_services
from world_npcs import NpcInteraction
from world_owner import MapAddress, Location
from task_dialog_protocol import decode_visit_npc


class ServiceChecks(unittest.TestCase):
    def test_native_navigation_cannot_be_registered_as_a_standalone_server_action(self):
        for ident in (10001,10002,10003,10004):
            with self.subTest(service=ident):
                with self.assertRaises(ValueError):
                    NpcServices({ident:'original local navigation'},(
                        ServiceBinding(7,ident,'forged.action','designed','isolated invalid binding'),))

    def test_original_cached_navigation_and_window_call_never_require_action_bindings(self):
        services=load_services(menu_groups=((7,101),(7,265),(7,327)))
        address=MapAddress(1007,1,0);current=Location(9,'epoch',address,7,1680,5311)
        proof=NpcInteraction('navigation-1',9,'epoch',address,7,123,7,1)
        self.assertEqual(decode_visit_npc(services.menu(proof,current)),(123,[101,265,327],[]))
        self.assertEqual(dict(services.bindings),{})
        for ident in (101,265,267,268,327,10001,10002,10003,10004):
            with self.subTest(service=ident):
                with self.assertRaises(ValueError):
                    services.plan(struct.pack('>qi',123,ident),proof,current,
                        request_id='navigation-1',now_ms=1,deadline_ms=10)

    def test_original_information_group_needs_no_fake_action_permission(self):
        services=load_services(menu_groups=((10127,170),))
        address=MapAddress(1007,1,0);current=Location(9,'epoch',address,7,1680,5311)
        proof=NpcInteraction('info-1',9,'epoch',address,7,123,10127,1)
        self.assertEqual(dict(services.bindings),{})
        self.assertEqual(decode_visit_npc(services.menu(proof,current,quest_ids=(100192,))),
                         (123,[170],[100192]))
        for ident in (170,10001):
            with self.assertRaises(ValueError):
                services.plan(struct.pack('>qi',123,ident),proof,current,
                    request_id='info-1',now_ms=1,deadline_ms=10)

    def test_group_rejects_action_permissions_on_intermediate_parent_or_local_return(self):
        labels={1:'root',2:'nested',3:'heal',**{s:'local' for s in range(10001,10005)}}
        children={1:(2,10001,10002,10003,10004),2:(3,)}
        for illegal in (1,2,10001,10002,10003,10004):
            bindings=tuple(ServiceBinding(7,s,'known.action','designed','isolated parent conflict')
                           for s in (3,illegal))
            with self.subTest(illegal=illegal):
                with self.assertRaises(ValueError):
                    NpcServices(labels,bindings,child_services=children,menu_groups=((7,1),))

    def test_submenus_require_every_real_leaf_and_keep_unused_catalog_damage_inactive(self):
        bindings=tuple(ServiceBinding(10086,s,'recovery.pet','designed','explicit trainer fixture')
                       for s in (10,11))
        with self.assertRaises(ValueError):load_services(bindings,menu_groups=((10086,295),))
        services=load_services()
        self.assertEqual(services.menus,{})
        self.assertNotIn(10011,services.labels)  # Original dangling reference is not a permission.
        labels={1:'root',2:'nested',3:'heal',4:'buy',6:'independent',500:'unused',10001:'exit'}
        children={1:(2,4,10001),2:(3,),500:(10011,)}
        bindings=tuple(ServiceBinding(7,s,'known.action','designed','isolated subtree fixture') for s in (3,4,6))
        services=NpcServices(labels,bindings,child_services=children,menu_groups=((7,1),))
        self.assertEqual(services.menus[7],(1,6))
        for groups,tree in ((((7,500),),children),(((7,1),(7,1)),children),
                (((7,1),(7,2)),children),(((7,1),),{1:(2,),2:(1,)}),
                (((7,1),),{1:(10001,),10001:(3,)})):
            with self.subTest(groups=groups,tree=tree):
                with self.assertRaises(ValueError):
                    NpcServices(labels,bindings,child_services=tree,menu_groups=groups)

    def test_native_pet_submenu_preserves_leaf_authority_and_task_vector(self):
        address=MapAddress(1007,1,0);current=Location(9,'epoch',address,7,1680,5311)
        proof=NpcInteraction('submenu-1',9,'epoch',address,7,123,10086,1)
        bindings=tuple(ServiceBinding(10086,s,'recovery.pet','designed','explicit trainer fixture')
                       for s in (10,11,12))
        services=load_services(bindings,menu_groups=((10086,295),))
        self.assertEqual(decode_visit_npc(services.menu(proof,current,quest_ids=(100192,))),
                         (123,[295],[100192]))
        self.assertEqual(set(services.bindings),{(10086,10),(10086,11),(10086,12)})
        for service in (10,11,12):
            command=services.plan(struct.pack('>qi',123,service),proof,current,
                request_id='submenu-1',now_ms=1,deadline_ms=10)
            self.assertEqual((command.service_id,command.handler),(service,'recovery.pet'))
        for service in (295,10001,3):
            with self.assertRaises(ValueError):
                services.plan(struct.pack('>qi',123,service),proof,current,
                    request_id='submenu-1',now_ms=1,deadline_ms=10)

    def test_original_service_labels_do_not_grant_npc_permissions(self):
        services = load_services()
        self.assertEqual(services.labels[6], '打开仓库')
        self.assertEqual(dict(services.bindings), {})

    def test_authorized_service_preserves_task_menu_and_owner_scope(self):
        address = MapAddress(1007, 1, 0)
        current = Location(9, 'epoch', address, 7, 1680, 5311)
        proof = NpcInteraction('command-1', 9, 'epoch', address, 7, 123, 10003, 1)
        # Explicit fixture policy, never a production NPC/service assignment.
        services = NpcServices({6: '打开仓库'}, (
            ServiceBinding(10003, 6, 'warehouse.open', 'designed', 'isolated test policy'),))
        self.assertEqual(decode_visit_npc(services.menu(proof, current, quest_ids=(100192,))),
                         (123, [6], [100192]))
        command = services.plan(struct.pack('>qi', 123, 6), proof, current,
                                request_id='command-1', now_ms=1, deadline_ms=10)
        self.assertEqual((command.role_id, command.login_epoch, command.handler, command.service_id),
                         (9, 'epoch', 'warehouse.open', 6))
        self.assertEqual(command.position_version, 7)
        self.assertEqual(command.source_status, 'designed')

    def test_forged_service_and_stale_map_proofs_are_rejected(self):
        address = MapAddress(1007, 1, 0)
        current = Location(9, 'epoch', address, 7, 1680, 5311)
        proof = NpcInteraction('command-1', 9, 'epoch', address, 7, 123, 10003, 1)
        services = NpcServices({6: '打开仓库', 2: '购买物品'}, (
            ServiceBinding(10003, 6, 'warehouse.open', 'designed', 'isolated test policy'),))
        for body, p, location, request, now in (
            (struct.pack('>qi',123,2),proof,current,'command-1',1),
            (struct.pack('>qi',124,6),proof,current,'command-1',1),
            (struct.pack('>qi',123,6),replace(proof,npc_id=10002),current,'command-1',1),
            (struct.pack('>qi',123,6),proof,replace(current,login_epoch='new'),'command-1',1),
            (struct.pack('>qi',123,6),proof,replace(current,version=8),'command-1',1),
            (struct.pack('>qi',123,6),proof,replace(current,address=MapAddress(1007,2,0)),'command-1',1),
            (struct.pack('>qi',123,6),proof,replace(current,state='loading'),'command-1',1),
            (struct.pack('>qi',123,6),proof,current,'other-command',1),
            (struct.pack('>qi',123,6),proof,current,'command-1',10),
            (b'',proof,current,'command-1',1),
        ):
            with self.subTest(body=body,proof=p,location=location,request=request,now=now):
                with self.assertRaises(ValueError):
                    services.plan(body,p,location,request_id=request,now_ms=now,deadline_ms=10)
        self.assertEqual(decode_visit_npc(NpcServices({6:'打开仓库'}).menu(proof,current)),
                         (123,[],[]))


if __name__ == '__main__':
    unittest.main()

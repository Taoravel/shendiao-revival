"""Re-read original starter branches, movie coordinates, NPCs and maps offline."""
from pathlib import Path
import hashlib,json,re
from pfs import PfsArchive
from bxml import decode
from world_grids import maze_grid
from world_collision import maze_clear
ROOT=Path(__file__).resolve().parent


def main():
 pfs=PfsArchive(ROOT/'runtime/client/artres/config.pfs');mapfs=PfsArchive(ROOT/'runtime/client/artres/map.pfs');sources={}
 def table(name):
  path='autoconfig/'+name+'.xml';raw=pfs.read(path);root=decode(raw)
  sources[path]={'sha256':hashlib.sha256(raw).hexdigest(),'crc_checked':True,'rows':len(root)}
  return {int(e.attrib['id']):{'attributes':dict(e.attrib),'lists':{c.tag:[v.text for v in c] for c in e}} for e in root}
 missions=table('knight.gsp.task.cmainmissioninfo');roles=table('knight.gsp.role.createroleconfig');schools=table('knight.gsp.role.schoolinfo');npcs=table('knight.gsp.npc.cnpcconfig');maps=table('knight.gsp.map.cmapconfig')
 def line(name,id):
  text=(ROOT/'decoded/config/autoconfig'/f'{name}.xml').read_text(encoding='utf-8')
  return next(i+1 for i,l in enumerate(text.splitlines()) if re.search(rf'<record id="{id}"(?: |>)',l))
 roots=[i for i,r in missions.items() if r['attributes'].get('MissionType')=='50' and r['attributes'].get('ScenarioInfoAnimationID','').startswith('110')]
 branches=[];graphnodes={};edges=[]
 for root in roots:
  first=[missions[int(i)] for i in missions[root]['lists']['PostMissionList']]
  home={int(r['attributes']['ActiveInfoMapID']) for r in first};assert len(home)==1;home=home.pop()
  school=[i for i,r in schools.items() if int(r['attributes']['schoolmapid'])==home];assert len(school)==1;school=school[0]
  roleids=sorted(int(v) for r in first for v in r['lists']['RequestRoleIDList'])
  allowed=sorted(i for i,r in roles.items() if str(school) in r['lists']['schools']);assert roleids==allowed,(school,roleids,allowed)
  movie=int(missions[root]['attributes']['ScenarioInfoAnimationID']);path=f'movie/{movie}.txt';raw=pfs.read(path);text=raw.decode('utf-16');sources[path]={'sha256':hashlib.sha256(raw).hexdigest(),'crc_checked':True}
  out=ROOT/'evidence/newbie-source';out.mkdir(exist_ok=True)
  (out/f'{movie}.txt').write_text(text,encoding='utf-8')
  commands=[{'line':n+1,'text':v.strip()} for n,v in enumerate(text.splitlines()) if v.strip().startswith(('Setmap ','Return ','End')) or (v.strip().startswith(('CreateNpc ','MoveNPC ','Jump ')) and 'varname=主角 ' in v)]
  sets=[c for c in commands if c['text'].startswith('Setmap ')];lastset=sets[-1];assert f'id={home} ' in lastset['text']
  hero=[c for c in commands if c['line']>lastset['line'] and 'varname=主角 ' in c['text']]
  endpoint=tuple(map(int,re.search(r'pos=(\d+),(\d+)',hero[-1]['text']).groups()))
  maprow=maps[home]['attributes'];maze=maze_grid(mapfs.read(maprow['resdir']+'/maze.dat'))
  candidate={'cell':endpoint,'logical_pixels':[v*16 for v in endpoint],'source_movie_line':hero[-1]['line'],'source_status':'client_verified_cinematic_actor_endpoint_only','server_spawn_confirmed':False,'maze_mask_1_clear':maze_clear(maze,*[v*16 for v in endpoint],mask=1)}
  mentor=int(first[0]['attributes']['ActiveInfoNpcID']);mentorrow=npcs[mentor]['attributes']
  nodes=[];queue=[root];seen=set()
  while queue:
   i=queue.pop(0)
   if i in seen or i not in missions:continue
   seen.add(i);r=missions[i];a=r['attributes']
   if a.get('MissionName')!='[主线]序章缘起':continue
   nextids=[int(v) for v in r['lists'].get('PostMissionList',[])];npcid=int(a.get('ActiveInfoNpcID','0'))
   node={'id':i,'attributes':a,'lists':r['lists'],'source_line':line('knight.gsp.task.cmainmissioninfo',i),'npc':npcs.get(npcid,{}).get('attributes')}
   nodes.append(node);graphnodes[i]=node
   for j in nextids:edges.append([i,j]);queue.append(j)
  branches.append({'school_id':school,'school_name':schools[school]['attributes']['name'],'root':root,'movie':movie,'home_map_id':home,'home_map_name':maprow['mapName'],'first_mentor_id':mentor,'first_mentor':mentorrow,'role_ids':roleids,'role_names':[roles[i]['attributes']['name'] for i in roleids], 'role_branches':[{'mission':int(r['attributes']['id']),'roles':r['lists']['RequestRoleIDList'],'movie':int(r['attributes']['ScenarioInfoAnimationID'])} for r in first], 'cinematic_home_setmap':lastset,'cinematic_actor_endpoint_candidate':candidate,'movie_commands':commands,'chapter_missions':nodes,'school_source_line':line('knight.gsp.role.schoolinfo',school),'mentor_source_line':line('knight.gsp.npc.cnpcconfig',mentor)})
 result={'sources':sources,'branches':branches,'roles':roles,'graph_edges':edges,'server_birth_coordinates':'not established by client-only files; cinematic endpoints recorded separately','no_client_started':True}
 routes=[]
 for b in branches:
  point=b['cinematic_actor_endpoint_candidate']
  for branch in b['role_branches']:
   for role in branch['roles']:
    routes.append({'role_id':int(role),'school_id':b['school_id'],'home_map_id':b['home_map_id'],
      'intro_task_id':b['root'],'intro_movie_id':b['movie'],'successor_task_id':branch['mission'],
      'successor_card_effect_id':branch['movie'],'first_npc_id':b['first_mentor_id'],
      'cinematic_endpoint':{'cell':list(point['cell']),'logical_pixels':point['logical_pixels'],
        'movie_path':f"movie/{b['movie']}.txt",'line':point['source_movie_line'],'server_spawn_confirmed':False}})
 routes.sort(key=lambda v:(v['school_id'],v['role_id']))
 assert len(routes)==43 and len({(v['role_id'],v['school_id']) for v in routes})==43
 catalog={'schema':1,'source_status':'client_verified','coordinate_contract':{'cell_pixels':16,'server_spawn_confirmed':False},'routes':routes}
 (ROOT/'catalogs/newbie-routes.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
 (ROOT/'evidence/newbie-origin-client.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 diagram=['flowchart TD']
 for i,node in sorted(graphnodes.items()):
  a=node['attributes'];npc=node['npc'];label=f"{i} type {a['MissionType']}"+(f" {npc['name']}" if npc else '')
  diagram.append(f'  T{i}["{label}"]')
 for i,j in sorted(set(tuple(e) for e in edges)):diagram.append(f'  T{i} --> T{j}')
 (ROOT/'evidence/NEWBIE_CHAPTER_FLOW.mmd').write_text('\n'.join(diagram)+'\n',encoding='utf-8')
 print(json.dumps({'schools':len(branches),'role_school_pairs':sum(len(b['role_ids']) for b in branches),'chapter_nodes':len(graphnodes),'edges':len(edges),'endpoints_clear':[b['cinematic_actor_endpoint_candidate']['maze_mask_1_clear'] for b in branches]}))

if __name__=='__main__':main()

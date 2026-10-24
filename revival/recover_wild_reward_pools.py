"""Startup/offline recovery of explicit ordinary loot candidates, not drop rates."""
import json
import hashlib
from collections import defaultdict
from inspect_client import ROOT, OUT, catalog_rows, write_json
from pfs import PfsArchive
from bxml import decode
from equipment_detail import DetailRules


def main():
    archive = PfsArchive(ROOT/'artres/config.pfs')
    tables, evidence = {}, []
    for name in ('citemattr','cequipmakeinfo','cequipeffect'):
        path = 'autoconfig/knight.gsp.item.'+name+'.xml'
        data = archive.read(path)
        tables[name] = catalog_rows(decode(data))
        evidence.append(dict(path=path,sha256=hashlib.sha256(data).hexdigest(),rows=len(tables[name]),crc_verified=True))
    items = {int(r['attributes']['id']):r['attributes'] for r in tables['citemattr']}
    effects = {int(r['attributes']['id']):r['attributes'] for r in tables['cequipeffect']}
    supported = DetailRules.load().templates
    equipment = defaultdict(list)
    for row in tables['cequipmakeinfo']:
        a = row['attributes']; tid,level = int(a['id']),int(a['level'])
        if tid in supported and level <= 80 and int(effects[tid].get('suiting',0)) == 0:
            equipment[level].append(dict(item_id=tid,name=items[tid]['name'],level=level))
    medicine_ids = (33001,33003,33005,33013,33015,33018)
    porcelain_ids = (50001,50015,50002)
    def item(tid):
        a = items[tid]
        if a['name'] == '已删除': raise ValueError('Deleted loot candidate')
        return dict(item_id=tid,name=a['name'],description=a.get('destribe',''),effect=a.get('effectdes',''))
    result = dict(revision='wild-reward-pools-v2',equipment={str(k):sorted(v,key=lambda a:a['item_id'])
        for k,v in sorted(equipment.items())},medicine=[item(i) for i in medicine_ids],
        porcelain=[item(i) for i in porcelain_ids],
        candidate_identity_status='client_verified',drop_assignment_status='designed',
        equipment_limit='ordinary clean non-set craftable templates up to historical level 80; no randomized quality')
    write_json(OUT/'catalogs/wild-reward-pools.json',result)
    write_json(OUT/'evidence/wild-reward-pools-audit.json',dict(tables=evidence,
        equipment_candidates=sum(map(len,equipment.values())),equipment_tiers=sorted(equipment),
        medicines=len(medicine_ids),porcelain=len(porcelain_ids),original_drop_rates_verified=False))
    print(dict(equipment=sum(map(len,equipment.values())),medicine=6,porcelain=3))


if __name__ == '__main__': main()

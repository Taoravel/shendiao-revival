"""Original score projection for the currently emitted ordinary Pet wire fields.

Known evolution is projected independently. Unrestored extra equipment/1760
fields retain their current native constructor zeros.
"""
from dataclasses import dataclass
from types import MappingProxyType
import json
import struct
from inspect_client import OUT
from pet_protocol import growth_wire_float


def _f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]


@dataclass(frozen=True)
class ScoreRules:
    rows: tuple
    templates: object

    @classmethod
    def load(cls):
        rows=json.loads((OUT/'catalogs/knight.gsp.pet.cpetgradecfg.json').read_text(encoding='utf-8'))
        attrs=(540,550,560,570,580,590,600,530,1170,1180,1190,1160,1430,1440,1660,1670,1760)
        if tuple(int(r['attributes']['attrid']) for r in rows)!=attrs:
            raise ValueError('Original pet score fields require review')
        coeff=tuple((int(r['attributes']['attrid']),float(r['attributes']['coefficent'])) for r in rows)
        pets=json.loads((OUT/'catalogs/knight.gsp.pet.cpetattr.json').read_text(encoding='utf-8'))
        templates=MappingProxyType({int(r['attributes']['id']):(int(r['attributes']['kind']),int(r['attributes']['uselevel'])) for r in pets})
        return cls(coeff,templates)

    def project(self,template,aptitudes,growth_raw,insight,learned,blood_level,*,evolution_stage=0):
        """Exact supported native wire projection, not an original RNG rule."""
        if (type(template) is not int or template not in self.templates
                or type(aptitudes) is not tuple or len(aptitudes)!=5
                or any(type(v) is not int or not 0<=v<=0x7fffffff for v in (*aptitudes,insight))
                or type(learned) is not tuple or len(learned)>12
                or any(type(v) is not int or not 0<v<=0x7fffffff for v in learned)
                or type(blood_level) is not int or not 0<=blood_level<=15
                or type(evolution_stage) is not int or not 0<=evolution_stage<=56):
            raise ValueError('Known complete supported pet score inputs required')
        kind,uselevel=self.templates[template]
        attrs=dict(zip((540,550,560,570,580),aptitudes))
        attrs.update({590:0,530:uselevel,1160:insight,1430:blood_level,1440:evolution_stage+1,1660:0,1670:0,1760:0})
        attrs.update({1170+10*i:sum(v%10==i+1 for v in learned) for i in range(3)})
        grow=growth_wire_float(growth_raw);total=0.0
        for key,coefficient in self.rows:
            product=(grow if key==600 else attrs[key])*coefficient
            total=_f32(total+_f32(product))
        if kind!=1:total=_f32(total+(500 if kind==2 else 400))
        # The original two final sums are zero with the currently empty extra
        # pet-equipment map; evolution contributes(raw stage+1)*25 above.
        score=int(total)
        if not 0<=score<=0x7fffffff:raise ValueError('Pet score exceeds native signed32')
        return score

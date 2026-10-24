"""Versioned clean ordinary equipment details and their native item-tip bean.

Only the explicit unenhanced baseline is represented. Advanced/unknown legacy
instances must retain their unknown state until the corresponding model exists.
"""
from dataclasses import asdict, dataclass,replace
import json
import struct
from types import MappingProxyType

from inspect_client import OUT
from wire import octets


@dataclass(frozen=True)
class EquipmentDetail:
    identified: int
    prefix_quality: int
    score: int
    base_properties: tuple

    def __post_init__(self):
        if (type(self.identified) is not int or self.identified not in (0, 1)
                or type(self.prefix_quality) is not int or not 1 <= self.prefix_quality <= 5
                or type(self.score) is not int or not 0 <= self.score <= 0x7fffffff
                or type(self.base_properties) is not tuple or len(self.base_properties) > 64
                or any(type(pair) is not tuple or len(pair) != 2
                       or any(type(v) is not int for v in pair)
                       or not 1 <= pair[0] <= 0x7fffffff or not -0x80000000 <= pair[1] <= 0x7fffffff
                       for pair in self.base_properties)
                or len({pair[0] for pair in self.base_properties}) != len(self.base_properties)):
            raise ValueError('Invalid explicit clean equipment detail')


@dataclass(frozen=True)
class DetailRules:
    revision: str
    initial_identified: int
    initial_quality: int
    initial_score: int
    templates: object
    color_caps: object

    @classmethod
    def load(cls):
        policy = json.loads((OUT / 'design/equipment-detail-v1.json').read_text(encoding='utf-8'))
        if policy['revision'] != '2026-10-23.equipment-detail.1':
            raise ValueError('Equipment detail policy needs implementation review')
        def rows(name):
            return json.loads((OUT / ('catalogs/knight.gsp.item.' + name + '.json')).read_text(encoding='utf-8'))
        items = {int(row['attributes']['id']): int(row['attributes']['itemtypeid']) for row in rows('citemattr')}
        god_weapons = {int(row['attributes']['id']) for row in rows('cgodweapon')}
        templates = {}
        for row in rows('cequipeffect'):
            key = int(row['attributes']['id'])
            kind = items.get(key, 0)
            if key in god_weapons or (kind & 15) != 8 or not 0 <= ((kind >> 4) & 15) <= 5:
                continue
            lists = row['lists']
            types, values = tuple(map(int, lists.get('baseEffectType', ()))), tuple(map(int, lists.get('baseEffect', ())))
            if len(values) > len(types) and all(v == 0 for v in values[len(types):]):
                values = values[:len(types)]
            if len(types) != len(values):
                raise ValueError('Equipment base detail length mismatch')
            thresholds = tuple(map(int, lists['scorecolor']))
            if tuple(sorted(thresholds)) != thresholds or any(v <= 0 for v in thresholds):
                raise ValueError('Equipment color thresholds require review')
            templates[key] = (tuple(zip(types, values)), thresholds)
        caps = {int(row['attributes']['id']): int(row['attributes']['bestcolortype'])
                for row in rows('cequipprefixconfig')}
        if set(caps) != set(range(1, 7)) or any(not 1 <= v <= 6 for v in caps.values()):
            raise ValueError('Equipment prefix color caps require review')
        g = policy['generation']
        rules = cls(policy['revision'], g['identified'], g['prefix_quality'], g['score'],
                    MappingProxyType(templates), MappingProxyType(caps))
        # Validate the generated representation before sessions are accepted.
        for key in templates:
            rules.color(key, rules.generate(key))
        return rules

    def generate(self, template):
        if template not in self.templates:
            raise ValueError('Equipment detail type is not restored')
        return EquipmentDetail(self.initial_identified, self.initial_quality, self.initial_score,
                               self.templates[template][0])

    def color(self, template, detail):
        if not isinstance(detail, EquipmentDetail) or template not in self.templates:
            raise ValueError('Unsupported equipment detail')
        thresholds = self.templates[template][1]
        return min(1 + sum(detail.score >= threshold for threshold in thresholds),
                   self.color_caps[detail.prefix_quality])

    def fixed_clean_unidentified(self,template,detail):
        """Structural rule only; persistent origin/lease/version remain separate fences."""
        return (type(template) is int and template in self.templates and type(detail) is EquipmentDetail
                and detail.identified==0 and detail.prefix_quality==1 and detail.score==0
                and detail.base_properties==self.templates[template][0])


def prepare(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS inventory_equipment_details (
            item_key INTEGER PRIMARY KEY REFERENCES inventory_items(id) ON DELETE CASCADE,
            revision TEXT NOT NULL, origin TEXT NOT NULL, detail TEXT NOT NULL);
    ''')


def _owner(db, account_id, role_id, key):
    if not db.in_transaction:
        raise ValueError('Equipment details require an owner transaction')
    row = db.execute('SELECT i.template_id FROM inventory_items i JOIN roles r ON r.id=i.role_id '
                     'WHERE i.id=? AND i.role_id=? AND r.account_id=? AND i.quantity=1',
                     (key, role_id, account_id)).fetchone()
    if not row:
        raise ValueError('Equipment detail ownership mismatch')
    return row[0]


def initialize(db, account_id, role_id, key, rules, detail, condition, *, origin):
    template = _owner(db, account_id, role_id, key)
    if origin not in ('restoration_grant', 'explicit_known_clean_instance'):
        raise ValueError('Explicit clean equipment origin required')
    if rules.color(template, detail) != condition.color_tier:
        raise ValueError('Equipment score/prefix and condition color disagree')
    if db.execute('SELECT 1 FROM inventory_equipment_details WHERE item_key=?', (key,)).fetchone():
        raise ValueError('Equipment details cannot be reset')
    db.execute('INSERT INTO inventory_equipment_details VALUES(?,?,?,?)',
               (key, rules.revision, origin, json.dumps(asdict(detail))))
    db.execute('INSERT INTO inventory_versions(role_id,revision) VALUES(?,1) '
               'ON CONFLICT(role_id) DO UPDATE SET revision=revision+1', (role_id,))
    return detail


def load(db, account_id, role_id, key, rules):
    template = _owner(db, account_id, role_id, key)
    row = db.execute('SELECT revision,origin,detail FROM inventory_equipment_details WHERE item_key=?', (key,)).fetchone()
    if not row or row[0] != rules.revision or row[1] not in ('restoration_grant', 'explicit_known_clean_instance'):
        raise ValueError('Equipment details require explicit initialization or migration')
    value = json.loads(row[2])
    value['base_properties'] = tuple(tuple(pair) for pair in value['base_properties'])
    detail = EquipmentDetail(**value)
    rules.color(template, detail)
    return detail


def _identify_fixed_clean(db,account_id,role_id,key,rules,expected_json):
    """Inventory owns the current lease/full-item/version fence and outer receipt."""
    template=_owner(db,account_id,role_id,key)
    row=db.execute('SELECT revision,origin,detail FROM inventory_equipment_details WHERE item_key=?',(key,)).fetchone()
    if row!=(rules.revision,'explicit_known_clean_instance',expected_json):
        raise ValueError('Fixed identification detail source changed')
    before=load(db,account_id,role_id,key,rules)
    if not rules.fixed_clean_unidentified(template,before):
        raise ValueError('Explicit canonical clean unidentified result required')
    after=replace(before,identified=1)
    changed=db.execute('UPDATE inventory_equipment_details SET detail=? WHERE item_key=? AND revision=? AND origin=? AND detail=? '
        'AND EXISTS(SELECT 1 FROM inventory_items WHERE id=? AND role_id=? AND quantity=1 AND equipment_slot IS NULL)',
        (json.dumps(asdict(after)),key,rules.revision,'explicit_known_clean_instance',expected_json,key,role_id)).rowcount
    if changed!=1:raise ValueError('Fixed identification source CAS failed')
    return after


def encode(template, detail, condition, rules):
    """Original generic item-tip detail; conditions always come from current DB."""
    if rules.color(template, detail) != condition.color_tier:
        raise ValueError('Equipment detail color diverges from authoritative condition')
    # Clean baseline: additional property triples, gems, enhancement, two
    # unknown scalars, second text, 4-i32 bean, two scalars, 6-i32 bean,
    # and two disabled extension flags. No claim about enabled features.
    return (struct.pack('>7i', detail.identified, 0, condition.current, condition.maximum, 0, 0, 0)
            + octets(b'') + struct.pack('>3i', detail.prefix_quality, detail.score, condition.color_tier)
            + struct.pack('>i', len(detail.base_properties))
            + b''.join(struct.pack('>ii', *pair) for pair in detail.base_properties)
            + struct.pack('>5i', 0, 0, 0, 0, 0) + octets(b'')
            + struct.pack('>12i', *([0] * 12)) + b'\0\0')

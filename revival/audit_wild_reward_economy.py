"""Analytic expected production at matching scene/role level, not a load test."""
from inspect_client import OUT,write_json
from wild_encounters import load_wild_rules
from wild_rewards import load_wild_reward_rules


def main():
    wild,rules = load_wild_rules(),load_wild_reward_rules()
    policy,pools = rules.content['policy'],rules.content['pools']
    rows = []
    for mid,area in wild.maps.items():
        level = area.level
        exp = max(rules.minimum,rules.costs[level]*rules.numerator//rules.denominator)
        tier = max(int(t) for t in pools['equipment'] if int(t) <= level)
        rows.append(dict(map_id=mid,matching_role_level=level,scene_level=level,
            victories=100,role_experience=exp*100,reference_nextexp=rules.costs[level],
            pet_experience_if_eligible=exp*200,cash=level*policy['cash_per_scene_level']*100,
            bound_silver=level*rules.silver_per_level*100,
            expected_medicine_count=policy['medicine']['chance']/100,
            expected_porcelain_counts={str(r['item_id']):policy['porcelain']['chance']*r['weight']/1000000
                for r in policy['porcelain']['items']},
            expected_equipment_count=policy['equipment']['chance']/100,
            equipment_tier=tier,equipment_candidate_count=len(pools['equipment'][str(tier)])))
    write_json(OUT/'evidence/wild-reward-economy-v2.json',dict(revision=rules.revision,
        interpretation='analytic expectations, matching levels, 100 completed victories; not measured drops or final balance',
        source_status='designed',maps=rows,notes=[
            'No multiple-time state, team modifier, field event or item sale income included.',
            'Expected item counts are fractional means, never a per-player guarantee.',
            'Cash and bound silver are independent balances; no exchange or purchasing-power equivalence assumed.',
            'Above scene+10 no base rewards; porcelain additionally requires absolute level gap<=5.',
            'Human playtime, encounter travel time, deaths and supply costs have not been measured.']))
    print(dict(maps=len(rows),expected_items_per_100_matching_level_victories=42,
               expected_equipment_per_100=2,measured_live=False))


if __name__ == '__main__': main()

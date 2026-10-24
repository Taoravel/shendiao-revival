"""Original c563a research refresh. Pure absolute snapshot encoding only."""
import struct
from guild_research import ResearchSnapshot,ResearchSkill
from wire import compact

REFRESH_RESEARCH=0xc563a
# Original clifeskill bCanStudy=1; this is a wire projection allowlist.
RESEARCH_SKILLS=frozenset((300101,300201,300301,310101,310103,310201,320101,
    320102,320103,320104,330101,330102,330103,370001))


def clear_cache():
    """Original empty refresh invalidates stale UI data, without inventing rows."""
    return struct.pack('>iB',0,0)


def refresh(state):
    if (not isinstance(state,ResearchSnapshot) or type(state.skills) is not tuple
            or len(state.skills)!=len(RESEARCH_SKILLS) or type(state.selected_skill) is not int
            or state.selected_skill not in RESEARCH_SKILLS|{0}):
        raise ValueError('complete_guild_research_snapshot_required')
    seen=set();encoded=[]
    for row in state.skills:
        if (not isinstance(row,ResearchSkill)
                or any(type(n) is not int or not 0<=n<2**31
                    for n in (row.skill_id,row.level,row.cap,row.experience,row.next_experience))
                or row.skill_id not in RESEARCH_SKILLS or row.skill_id in seen
                or not 0<=row.level<=row.cap or row.cap==0
                or (row.level<row.cap and not row.experience<row.next_experience)
                or (row.level==row.cap and (row.experience!=0 or row.next_experience!=0))):
            raise ValueError('invalid_guild_research_skill_snapshot')
        seen.add(row.skill_id)
        encoded.append(struct.pack('>5i',row.skill_id,row.level,row.cap,row.experience,row.next_experience))
    return struct.pack('>i',state.selected_skill)+compact(len(encoded))+b''.join(encoded)

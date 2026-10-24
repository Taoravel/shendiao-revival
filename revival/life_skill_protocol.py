"""Native incremental life-skill segment; no clearing the shared assist map."""
import struct
from role_life_skills import LifeSkill
from guild_research_protocol import RESEARCH_SKILLS
from wire import compact

LEARN_ASSIST_SKILL=0xc36b6
UPDATE_ASSIST_SKILL=0xc36b7
ASSIST_SKILL_MAX_LEVELS=0xc36b8


def request(body):
    if type(body) is not bytes or len(body)!=13:raise ValueError('invalid_life_skill_request')
    return struct.unpack('>QiB',body)


def update(state):
    if type(state) is not LifeSkill or any(type(v) is not int or not 0<=v<2**31
            for v in (state.skill,state.level,state.proficiency)) or not state.skill:
        raise ValueError('invalid_life_skill_update')
    return struct.pack('>iii',state.skill,state.level,state.proficiency)


def study_panel(npc,maximums):
    if (type(npc) is not int or not 0<=npc<2**64 or type(maximums) is not tuple
            or any(type(row) is not tuple or len(row)!=2 or any(type(v) is not int for v in row) for row in maximums)
            or tuple(s for s,_ in maximums)!=tuple(sorted(RESEARCH_SKILLS))
            or any(not 0<=level<=160 for _,level in maximums)):
        raise ValueError('complete_current_life_skill_maximums_required')
    return struct.pack('>Q',npc)+compact(14)+b''.join(struct.pack('>ii',*row) for row in maximums)

"""A small deterministic 4-stage resume-matching agent used to demonstrate and test Phase 3.
Stages are pure functions with explicit inputs, so they can be replayed with overrides."""
from __future__ import annotations
import re
from .models import RunRecord, StageEvent

STAGES = ["tokenize", "extract_skills", "score", "decide"]
SKILLS = {"python", "sql", "java", "docker", "aws"}
FAULT_COMPONENT = {"TOY-F01": "tokenize", "TOY-F02": "extract_skills",
                   "TOY-F03": "score", "TOY-F04": "decide"}


def _tokenize(c, f):
    t = re.findall(r"[a-z]+", c["resume"].lower())
    return t[:3] if "TOY-F01" in f else t                      # F01: truncates tokens

def _extract(c, f):
    s = sorted({t for t in c["tokens"] if t in SKILLS})
    return [x for x in s if x != "sql"] if "TOY-F02" in f else s   # F02: drops 'sql'

def _score(c, f):
    den = len(c["required"]) + (1 if "TOY-F03" in f else 0)       # F03: wrong denominator
    return round(len(set(c["skills"]) & set(c["required"])) / den, 4)

def _decide(c, f):
    th = 0.9 if "TOY-F04" in f else 0.5                            # F04: threshold too high
    return "match" if c["score"] >= th else "reject"

_FN = {"tokenize": _tokenize, "extract_skills": _extract, "score": _score, "decide": _decide}


class ToyAdapter:
    def stage_names(self, agent_id):
        return list(STAGES)

    def run(self, agent_id, input, *, faults=(), overrides=None):
        overrides = overrides or {}
        st, events = {}, []
        for name in STAGES:
            consumed = {"tokenize": {"resume": input["resume"]},
                        "extract_skills": {"tokens": st.get("tokenize")},
                        "score": {"skills": st.get("extract_skills"), "required": input["required"]},
                        "decide": {"score": st.get("score")}}[name]
            if name in overrides:
                st[name] = overrides[name]
                events.append(StageEvent(name, consumed, st[name], overridden=True))
                continue
            try:
                st[name] = _FN[name](consumed, tuple(faults))
                events.append(StageEvent(name, consumed, st[name]))
            except Exception as e:                                   # noqa: BLE001
                events.append(StageEvent(name, consumed, None, error=repr(e)))
                return RunRecord("error", None, events, repr(e))
        return RunRecord("success", {"decision": st["decide"], "score": st["score"]}, events)

    def judge(self, agent_id, run, expected):
        return run.status == "success" and run.output["decision"] == expected["decision"]

    def fault_component(self, agent_id, fault_id):
        return FAULT_COMPONENT[fault_id]

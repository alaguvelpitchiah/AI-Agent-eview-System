"""A small deterministic 4-stage resume-matching agent used to demonstrate and test Phases 3-4.
Stages are pure functions of (explicit inputs, config), so they can be replayed with overrides.
Faults and repairs are both config patches applied in order: clean -> faults -> repairs."""
from __future__ import annotations
import re
from .models import RunRecord, StageEvent

STAGES = ["tokenize", "extract_skills", "score", "decide"]
SKILLS = {"python", "sql", "java", "docker", "aws"}
BASE_CFG = {"max_tokens": None, "lowercase": True, "strict": False, "drop": [], "min_len": 0,
            "denom_extra": 0, "threshold": 0.5}
STAGE_KEYS = {"tokenize": ["max_tokens", "lowercase", "strict"], "extract_skills": ["drop", "min_len"],
              "score": ["denom_extra"], "decide": ["threshold"]}
FAULT_PATCH = {"TOY-F01": {"max_tokens": 3},        # truncates tokens
               "TOY-F02": {"drop": ["sql"]},        # drops the 'sql' skill
               "TOY-F03": {"denom_extra": 1},       # wrong score denominator
               "TOY-F04": {"threshold": 0.9},       # decision threshold too high
               # fault types added in Phase 6 and held out from every earlier phase:
               "TOY-F05": {"lowercase": False},     # case-sensitive matching
               "TOY-F06": {"min_len": 4},           # drops short skills (sql, aws)
               "TOY-F07": {"strict": True}}         # crashes on resumes containing digits
FAULT_COMPONENT = {"TOY-F01": "tokenize", "TOY-F02": "extract_skills",
                   "TOY-F03": "score", "TOY-F04": "decide",
                   "TOY-F05": "tokenize", "TOY-F06": "extract_skills", "TOY-F07": "tokenize"}


def make_cfg(faults=(), repairs=()):
    cfg = dict(BASE_CFG)
    for f in faults:
        cfg.update(FAULT_PATCH[f])
    for r in repairs:
        cfg.update(r.patch)
    return cfg


def _tokenize(c, cfg):
    if cfg["strict"] and re.search(r"\d", c["resume"]):
        raise ValueError("unexpected digit in resume")
    t = re.findall(r"[A-Za-z]+", c["resume"])
    if cfg["lowercase"]:
        t = [x.lower() for x in t]
    return t if cfg["max_tokens"] is None else t[:cfg["max_tokens"]]

def _extract(c, cfg):
    return sorted({t for t in c["tokens"] if t in SKILLS and t not in cfg["drop"] and len(t) >= cfg["min_len"]})

def _score(c, cfg):
    return round(len(set(c["skills"]) & set(c["required"])) / (len(c["required"]) + cfg["denom_extra"]), 4)

def _decide(c, cfg):
    return "match" if c["score"] >= cfg["threshold"] else "reject"

_FN = {"tokenize": _tokenize, "extract_skills": _extract, "score": _score, "decide": _decide}


def consumed_inputs(name, input, st):
    return {"tokenize": {"resume": input["resume"]},
            "extract_skills": {"tokens": st.get("tokenize")},
            "score": {"skills": st.get("extract_skills"), "required": input["required"]},
            "decide": {"score": st.get("score")}}[name]


class ToyAdapter:
    def stage_names(self, agent_id):
        return list(STAGES)

    def run(self, agent_id, input, *, faults=(), overrides=None, repairs=()):
        overrides, cfg = overrides or {}, make_cfg(faults, repairs)
        st, events = {}, []
        for name in STAGES:
            consumed = consumed_inputs(name, input, st)
            if name in overrides:
                st[name] = overrides[name]
                events.append(StageEvent(name, consumed, st[name], overridden=True))
                continue
            try:
                st[name] = _FN[name](consumed, cfg)
                events.append(StageEvent(name, consumed, st[name]))
            except Exception as e:                                   # noqa: BLE001
                events.append(StageEvent(name, consumed, None, error=repr(e)))
                return RunRecord("error", None, events, repr(e))
        return RunRecord("success", {"decision": st["decide"], "score": st["score"]}, events)

    def judge(self, agent_id, run, expected):
        return run.status == "success" and run.output["decision"] == expected["decision"]

    def fault_component(self, agent_id, fault_id):
        return FAULT_COMPONENT[fault_id]

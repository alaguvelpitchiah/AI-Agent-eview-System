"""Benchmark construction. Everything is deterministic given the seed.

Case pool: required-skill lists of 2-5 skills x matched-skill counts x 3 resume styles (plain / Capitalised /
with digits). The expected decision comes from the SPEC (match iff matched/required >= 0.5), not from running
the agent; a test checks that the clean agent satisfies every case.
Splits: REG (planning/regression + scenario targets), HELD (hard-gate held-out), HIDDEN (only used to measure
regressions after the fact; never seen by the system)."""
from __future__ import annotations
import random
from dataclasses import dataclass, asdict, field
from itertools import combinations
from phase3.toy_agent import STAGES, FAULT_COMPONENT
from .bench_toy import BenchAdapter

AGENT = "toy"
SKILL_ORDER = ["python", "sql", "docker", "java", "aws"]
STYLES = ("plain", "caps", "digits")
KNOWN_FAULTS = ["TOY-F01", "TOY-F02", "TOY-F03", "TOY-F04"]
HELDOUT_FAULTS = ["TOY-F05", "TOY-F06", "TOY-F07"]      # fault types added in Phase 6, never used earlier


def _text(style, have):
    fmt = (lambda s: s.upper() if len(s) <= 3 else s.capitalize()) if style == "caps" else (lambda s: s)
    skills = " and ".join(fmt(s) for s in have)
    lead = {"plain": "experienced developer", "caps": "Experienced Developer", "digits": "5 years experience"}[style]
    return f"{lead} with {skills}" if have else lead


def make_pool() -> list:
    pool = []
    for n in (2, 3, 4, 5):
        req = SKILL_ORDER[:n]
        for k in range(n + 1):
            have = [req[(i + k) % n] for i in range(k)]
            for style in STYLES:
                pool.append(dict(case_id=f"P-n{n}k{k}-{style}",
                                 input=dict(resume=_text(style, have), required=req),
                                 expected=dict(decision="match" if k / n >= 0.5 else "reject")))
    return pool


# Seeded repair-conflict traps: the planning suite is deliberately sparse (as real suites are). The compensating
# repair RP5 (threshold 0.3) looks valid on it; combined with the true score fix it breaks cases the suite lacks.
SPARSE_IDS = ["P-n3k1-plain", "P-n2k2-plain", "P-n3k2-plain", "P-n2k0-plain", "P-n4k3-plain", "P-n5k4-plain"]
TRAP_TARGET_IDS = [f"P-n{n}k{k}-{st}" for n, k in ((2, 1), (4, 2)) for st in STYLES]


def split_pool(pool, seed, n_reg=30, n_held=6):
    by_id = {c["case_id"]: c for c in pool}
    forced = [by_id[i] for i in SPARSE_IDS + TRAP_TARGET_IDS]
    rest = [c for c in pool if c not in forced]
    random.Random(seed).shuffle(rest)
    reg = forced + rest[:n_reg - len(forced)]
    held = rest[n_reg - len(forced): n_reg - len(forced) + n_held]
    hidden = rest[n_reg - len(forced) + n_held:]
    return reg, held, hidden


@dataclass
class BenchScenario:
    sid: str
    kind: str                    # single_known | single_heldout | double_synergistic | double_independent
    faults: list
    target: dict
    truth_stages: list
    expected_interaction_pairs: list = field(default_factory=list)
    oracle_conflicts: list = field(default_factory=list)
    suite_ids: list = field(default_factory=list)     # custom planning suite (empty = the full REG split)

    def to_dict(self):
        return asdict(self)


def _spread(items, k=3):
    if len(items) <= k:
        return items
    ix = sorted({0, len(items) // 2, len(items) - 1})
    return [items[i] for i in ix]


def build_scenarios(adapter: BenchAdapter, reg, pool, max_per_double_kind: int = 6) -> list:
    out = []

    by_id = {c["case_id"]: c for c in pool}

    def finish(kind, faults, target, expected_pairs=(), suite_ids=()):
        truth = sorted({FAULT_COMPONENT[f] for f in adapter.active_faults(target["input"], faults)}, key=STAGES.index)
        sid = f"{kind}:{'+'.join(f[-3:] for f in faults)}:{target['case_id']}"
        suite = [by_id[i] for i in suite_ids] if suite_ids else reg
        out.append(BenchScenario(sid, kind, list(faults), target, truth, [sorted(p) for p in expected_pairs],
                                 adapter.oracle_conflicts(faults, target, pool, truth, suite), list(suite_ids)))

    for group, kind in ((KNOWN_FAULTS, "single_known"), (HELDOUT_FAULTS, "single_heldout")):
        for f in group:
            for t in _spread([c for c in reg if adapter.fails(c, (f,))]):
                finish(kind, (f,), t)

    for tid in TRAP_TARGET_IDS:
        t = by_id[tid]
        if adapter.fails(t, ("TOY-F03",)):
            finish("conflict_trap", ("TOY-F03",), t, suite_ids=SPARSE_IDS)

    cands = {"synergistic": [], "independent": []}
    for pair in combinations(KNOWN_FAULTS + HELDOUT_FAULTS, 2):
        if FAULT_COMPONENT[pair[0]] == FAULT_COMPONENT[pair[1]]:
            continue
        rounds = 0
        for c in reg:
            if set(adapter.active_faults(c["input"], pair)) != set(pair) or not adapter.fails(c, pair):
                continue
            a, b = adapter.fails(c, (pair[0],)), adapter.fails(c, (pair[1],))
            kind = "synergistic" if not a and not b else "independent" if a and b else None
            if kind:
                cands[kind].append((rounds, pair, c))
                rounds += 1
    for kind, lst in cands.items():
        lst.sort(key=lambda x: (x[0], x[1]))
        for _, pair, c in lst[:max_per_double_kind]:
            pairs = [{FAULT_COMPONENT[pair[0]], FAULT_COMPONENT[pair[1]]}] if kind == "synergistic" else []
            finish(f"double_{kind}", pair, c, pairs)
    return out


def build(seed: int = 7):
    adapter = BenchAdapter()
    pool = make_pool()
    reg, held, hidden = split_pool(pool, seed)
    return adapter, pool, reg, held, hidden, build_scenarios(adapter, reg, pool)

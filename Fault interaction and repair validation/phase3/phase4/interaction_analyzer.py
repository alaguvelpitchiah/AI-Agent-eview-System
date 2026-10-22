"""Failure interaction discovery with a 2^k factorial design.

Factors are the faulty stages found in Phase 3. A factor is "present" if its
stage still runs with the failing configuration and "absent" if its output is
replaced by the reference value. For every present-set P we record whether the
run fails, then compare against the no-interaction prediction:
    predicted_fail(P) = any single factor in P fails on its own.
actual fail but predicted pass  -> synergistic (failure needs the factors together)
actual pass but predicted fail  -> cancelling (factors mask each other)
"""
from __future__ import annotations
from itertools import combinations
from .models import Interaction, InteractionReport


class InteractionAnalyzer:
    def __init__(self, adapter, max_factors: int = 4):
        self.a, self.max_factors = adapter, max_factors

    def analyze(self, agent_id, input, expected, faults, factors, reference=None) -> InteractionReport:
        stages = self.a.stage_names(agent_id)
        factors = [s for s in stages if s in set(factors)]
        rep = InteractionReport(factors=factors)
        if len(factors) < 2:
            rep.note = "Fewer than two factors; no interaction to test."
            return rep
        if len(factors) > self.max_factors:
            rep.note = f"{len(factors)} factors exceeds the 2^k limit of {self.max_factors}."
            return rep
        ref = reference or self.a.run(agent_id, input, faults=())
        fails = {}
        for r in range(len(factors) + 1):                    # r = size of the present-set
            for present in combinations(factors, r):
                absent = [f for f in factors if f not in present]
                ov = {s: ref.event(s).output for s in absent}
                run = self.a.run(agent_id, input, faults=tuple(faults), overrides=ov)
                ok = run.status == "success" and self.a.judge(agent_id, run, expected)
                fails[frozenset(present)] = not ok
                rep.runs += 1
        rep.outcomes = [{"present": [f for f in factors if f in k], "fails": v}
                        for k, v in sorted(fails.items(), key=lambda kv: (len(kv[0]), sorted(kv[0])))]
        for r in range(2, len(factors) + 1):
            for P in combinations(factors, r):
                pred = any(fails[frozenset([f])] for f in P)
                act = fails[frozenset(P)]
                kind = None
                if act and not pred:
                    kind = "synergistic"
                elif pred and not act:
                    kind = "cancelling"
                if r == 2:
                    rep.pairs.append({"pair": list(P), "interacts": kind is not None, "kind": kind})
                if kind:
                    rep.interactions.append(Interaction(list(P), kind,
                        "fails only when all are present" if kind == "synergistic"
                        else "a single factor fails, but the combination passes"))
        kinds = {i.kind for i in rep.interactions}
        rep.summary = "none" if not kinds else (next(iter(kinds)) if len(kinds) == 1 else "mixed")
        return rep

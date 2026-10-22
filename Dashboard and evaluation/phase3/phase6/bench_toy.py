"""Benchmark adapter for the toy agent: repair catalog (specific repairs + a generic per-stage rollback),
and a WHITEBOX ORACLE that gives ground truth independently of the diagnosis engine.

Ground truth used by the benchmark
  active faults : a fault is active on an input if running ITS stage function directly on the clean upstream
                  state (no engine, no overrides) changes that stage's output or raises.
  correct fix   : applying the repairs to the faulty configuration yields exactly the clean configuration.
  interaction   : from direct runs over fault subsets (synergistic = AB fails, A passes, B passes).
  conflicts     : repair pairs that each pass alone (target + every currently-passing pool case) but fail together."""
from __future__ import annotations
from itertools import combinations
from phase3.toy_agent import (STAGES, BASE_CFG, STAGE_KEYS, FAULT_PATCH, FAULT_COMPONENT, make_cfg,
                              consumed_inputs, _FN)
from phase4.models import Repair
from phase4.toy_repairs import ToyRepairAdapter, CATALOG

ROLLBACK = {s: Repair(f"RS-{s}", s, f"roll back '{s}' to its known-good configuration",
                      {k: BASE_CFG[k] for k in STAGE_KEYS[s]}) for s in STAGES}


class BenchAdapter(ToyRepairAdapter):
    def candidate_repairs(self, agent_id, stage):
        return list(CATALOG.get(stage, [])) + [ROLLBACK[stage]]

    def get_repair(self, agent_id, repair_id):
        for s in STAGES:
            for r in self.candidate_repairs(agent_id, s):
                if r.repair_id == repair_id:
                    return r
        raise KeyError(repair_id)

    # ---------------- oracle (independent of phase3/phase4 code)
    def fix_is_correct(self, faults, repair_ids) -> bool:
        return make_cfg(faults, [self.get_repair("toy", i) for i in repair_ids]) == BASE_CFG

    def fails(self, case, faults=(), repairs=()) -> bool:
        run = self.run("toy", case["input"], faults=tuple(faults), repairs=tuple(repairs))
        return not self.judge("toy", run, case["expected"])

    def active_faults(self, input, faults) -> list:
        clean_cfg, st, clean = make_cfg(()), {}, {}
        for name in STAGES:
            c = consumed_inputs(name, input, st)
            clean[name] = (c, _FN[name](c, clean_cfg))
            st[name] = clean[name][1]
        active = []
        for f in faults:
            stage = FAULT_COMPONENT[f]
            c, want = clean[stage]
            try:
                got = _FN[stage](c, make_cfg((f,)))
                if got != want:
                    active.append(f)
            except Exception:                                          # noqa: BLE001
                active.append(f)
        return active

    def oracle_conflicts(self, faults, target, pool, truth_stages, suite) -> list:
        """Emergent conflicts a reviewer holding `suite` could in principle see: both repairs are valid alone on
        the suite, and some pool case passes under A alone, under B alone, but fails under A+B."""
        first = min(STAGES.index(s) for s in truth_stages)
        universe = [r for s in STAGES[first:] for r in self.candidate_repairs("toy", s)]
        cur = [c for c in pool if c["case_id"] != target["case_id"] and not self.fails(c, faults)]
        suite_cur = [c for c in suite if c["case_id"] != target["case_id"] and not self.fails(c, faults)]

        def valid_on_suite(rs):
            return not self.fails(target, faults, rs) and not any(self.fails(c, faults, rs) for c in suite_cur)

        singles = [r for r in universe if valid_on_suite((r,))]
        out = []
        for a, b in combinations(singles, 2):
            orders = [(a, b)] + ([(b, a)] if a.stage == b.stage else [])
            for c in cur + [target]:
                if (not self.fails(c, faults, (a,)) and not self.fails(c, faults, (b,))
                        and any(self.fails(c, faults, o) for o in orders)):
                    out.append(sorted([a.repair_id, b.repair_id]))
                    break
        return sorted(out)

# AI Agent Review System - Final Evaluation

Seed 7; case pool 54 (planning 30, gate held-out 6, hidden 18); 39 scenarios (conflict_trap: 6, double_independent: 6, double_synergistic: 6, single_heldout: 9, single_known: 12). Pipeline = monitor, diagnose, interaction test, repair plan, hard gates (memory off). Baseline = blame by trace rules, first repair on that stage that fixes the target, no validation.

## Headline results

| # | Metric | Pipeline | Baseline | Meaning |
|---|---|---|---|---|
| 1 | Root-cause exact match | 1.00 [0.91-1.00] (39/39) | 0.26 [0.15-0.41] (10/39) | diagnosed stage set equals the oracle-active stage set |
| 2 | Blame precision | 1.00 [0.91-1.00] (39/39) | 0.36 [0.23-0.52] (14/39) | no stage blamed that is not a true cause |
| 3 | Interaction recall | 1.00 [0.61-1.00] (6/6) | 0.00 [0.00-0.39] (0/6) | synergistic stage pairs flagged (baseline never tests) |
| 4 | False-interaction rate | 0.00 [0.00-0.39] (0/6) | n/a | non-interacting pairs flagged (lower is better) |
| 5 | Conflict recall | 1.00 [0.84-1.00] (20/20) | 0.00 [0.00-0.16] (0/20) | emergent repair conflicts found |
| 6 | Conflict precision | 1.00 [0.84-1.00] (20/20) | n/a | reported conflicts that are real |
| 7 | Correct-fix rate | 0.92 [0.80-0.97] (36/39) | 0.26 [0.15-0.41] (10/39) | recommended fix restores the clean configuration (all scenarios) |
| 8 | Regression rate | 0.00 [0.00-0.09] (0/39) | 0.63 [0.44-0.78] (17/27) | recommended fixes breaking >=1 hidden case (lower is better) |
| 9 | Mean agent runs per scenario | 1126 | 2.8 | cost |

Rates show value [95% Wilson interval] (k/n). The baseline never tests interactions or conflicts, so metrics 3, 5 are 0 by design and 4, 6 are undefined for it.

### Other outcomes

| Outcome | Pipeline | Baseline |
|---|---|---|
| Recommended a fix that is not correct | 0.08 [0.03-0.20] (3/39) | 0.44 [0.29-0.59] (17/39) |
| Abstained (no fix recommended) | 0.00 [0.00-0.09] (0/39) | 0.31 [0.19-0.46] (12/39) |

### Paired comparison (exact sign test on discordant scenarios)

| Outcome | Pipeline only | Baseline only | p |
|---|---|---|---|
| Root-cause exact | 29 | 0 | 3.7e-09 |
| Correct fix | 26 | 0 | 3.0e-08 |

## Results by scenario group

| Group | n | RCA exact (pipe / base) | Correct fix (pipe / base) | Wrong fix recommended (pipe / base) | Abstained (pipe) |
|---|---|---|---|---|---|
| conflict_trap | 6 | 6 / 0 | 6 / 0 | 0 / 6 | 0 |
| double_independent | 6 | 6 / 0 | 6 / 0 | 0 / 0 | 0 |
| double_synergistic | 6 | 6 / 0 | 3 / 0 | 3 / 6 | 0 |
| single_heldout | 9 | 9 / 4 | 9 / 4 | 0 / 2 | 0 |
| single_known | 12 | 12 / 6 | 12 / 6 | 0 / 3 | 0 |

`single_heldout` uses fault types never seen in Phases 3-5; `conflict_trap` is seeded by construction (sparse planning suite).

## Two worked cases

### Interacting faults (each alone passes, together they fail)

- Scenario `double_synergistic:F02+F03:P-n2k2-plain`; injected faults ['TOY-F02', 'TOY-F03']; oracle root-cause stages ['extract_skills', 'score'].
- Pipeline diagnosis: ['extract_skills', 'score'] (joint_root_cause, confidence high).
- Interaction test: flagged [['extract_skills', 'score']]; expected [['extract_skills', 'score']].
- Conflicts reported none; oracle none.
- Pipeline recommends ['RP2', 'RP3'] (correct: True); baseline blamed `decide` and applied ['RP5'] (correct: False; breaks 2 of 15 hidden cases).

### Repair conflict (fix A and fix B each pass, A+B fails)

- Scenario `conflict_trap:F03:P-n2k1-plain`; injected faults ['TOY-F03']; oracle root-cause stages ['score'].
- Pipeline diagnosis: ['score'] (single_root_cause, confidence high).
- Interaction test: no interaction flagged; expected none.
- Conflicts reported [['RP3', 'RP5'], ['RP5', 'RS-score']]; oracle [['RP3', 'RP5'], ['RP5', 'RS-score']].
- Pipeline recommends ['RP3'] (correct: True); baseline blamed `decide` and applied ['RP5'] (correct: False; breaks 2 of 18 hidden cases).

## Where the pipeline went wrong (as shipped)

| Scenario | Oracle stages | Diagnosed | Recommended | Correct | Gates failed |
|---|---|---|---|---|---|
| double_synergistic:F03+F06:P-n2k2-plain | ['extract_skills', 'score'] | ['extract_skills', 'score'] | ['RP2', 'RP3'] | False | [] |
| double_synergistic:F03+F06:P-n4k3-plain | ['extract_skills', 'score'] | ['extract_skills', 'score'] | ['RP2', 'RP3'] | False | [] |
| double_synergistic:F03+F06:P-n4k3-digits | ['extract_skills', 'score'] | ['extract_skills', 'score'] | ['RP2', 'RP3'] | False | [] |

The recommended repairs pass every shipped gate yet leave a fault in place: `RP2` clears only the `drop` setting, so it does nothing for the held-out `min_len` fault, and the coverage gate checks stage names, not effects.

## Post-hoc variant (NOT a clean result)

After seeing the misses above I added an optional gate that re-runs stage isolation with the repairs applied (no stage may still deviate from the reference) and made the orchestrator fall back to the next-ranked repair set when one is blocked. These changes were designed with knowledge of this benchmark, so the numbers below are optimistic and need fresh faults.

| Metric | As shipped | Post-hoc |
|---|---|---|
| Correct-fix rate | 0.92 [0.80-0.97] (36/39) | 1.00 [0.91-1.00] (39/39) |
| Wrong fix recommended | 0.08 [0.03-0.20] (3/39) | 0.00 [0.00-0.09] (0/39) |
| Abstained | 0.00 [0.00-0.09] (0/39) | 0.00 [0.00-0.09] (0/39) |
| Regression rate | 0.00 [0.00-0.09] (0/39) | 0.00 [0.00-0.09] (0/39) |
| Mean agent runs | 1126 | 1152 |

## Limitations

- **One toy agent.** A deterministic 4-stage resume matcher whose stages are pure functions and whose faults are configuration patches. Results show the method works on replayable, deterministic, stage-structured agents; they do not show it works on LLM agents, stochastic agents or code-level bugs.
- **I wrote everything the system is graded on.** Faults, the repair catalog, the case pool and the oracle are mine. The oracle is independent code (it calls the stage functions directly) but it encodes the same structural assumption as the engine (stage outputs replaced by reference values), so near-perfect root-cause accuracy here is expected, not impressive.
- **Held-out fault types are only partly held out.** Faults F05-F07 did not exist when Phases 3-5 were written, but the first full run was seen before this report was finalised. One weakness it exposed (residual faults passing the gates) led to a post-hoc change, which is why that variant is reported separately and should not be read as unbiased.
- **The generic rollback repair is strong.** Every fault is a config patch, so 'roll the stage back to its known-good config' always works. Real faults (prompt changes, tool bugs, data drift) usually have no such one-step undo.
- **Small samples.** 39 scenarios in five groups of 6-12; the 95% intervals are wide and group-level differences are anecdotal. The conflict counts (metrics 5-6) are inflated by repetition: the same two repair pairs recur across about ten scenarios, so 20/20 is closer to two distinct conflicts found repeatedly. The paired sign tests treat scenarios as independent, but several share a fault and differ only in the input.
- **Conflict ground truth depends on the suites.** 'Conflict' means emergent failure (A alone passes, B alone passes, A+B fails) for pairs that are valid on the reviewer's own suite. The six conflict-trap scenarios are seeded by construction with a deliberately sparse suite, so they test the mechanism, not the ability to find unknown conflicts.
- **Gates are only as strong as the suites.** A repair no test exercises passes. The shipped gates also checked coverage by stage name, not by effect, which is exactly how three wrong fixes got through (see 'Where the pipeline went wrong').
- **Cost.** The pipeline uses roughly two to three orders of magnitude more agent runs than the baseline because it validates many repair sets exhaustively. Cheap here, expensive for an LLM agent; pruning or sequential search is future work.
- **Not measured:** CPU/memory use, nondeterminism (no repeated trials were needed because the agent is deterministic), and any second-person test design (a single author wrote all cases).
- **Not verified against the real Phase 2 code.** The adapter to the real system is an unfilled template; the FastAPI routers and the Streamlit dashboard have never been run in this environment.

## Reproduce

`python -m phase6.run_benchmark --seed 7 --out phase6_results` rebuilds the benchmark and regenerates every file here (`benchmark.json`, `results.json`, `results.md`, `report.html`).

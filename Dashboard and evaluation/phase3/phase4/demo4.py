from phase3.evaluation import Case
from .toy_repairs import ToyRepairAdapter
from .evaluation4 import Scenario, evaluate4

A = "toy"
M, X = {"decision": "match"}, {"decision": "reject"}
def C(i, resume, req, exp): return Case(i, A, {"resume": resume, "required": req}, exp)

R1 = C("R1", "Python and SQL developer with Docker", ["python", "sql"], M)
R2 = C("R2", "Experienced developer with python and sql", ["python", "sql"], M)
R3 = C("R3", "python sql", ["python", "sql", "docker"], M)
R4 = C("R4", "I know python and sql", ["python", "sql", "docker"], M)
R6 = C("R6", "I know python", ["python", "sql"], M)
RX = C("RX", "I know python", ["python", "sql", "docker"], X)       # clean score 0.33 -> reject
RY = C("RY", "I know java", ["python", "sql"], X)
REG = [R1, R2, R3, R4, R6, RX, RY]
CONFLICT = {frozenset({"RP3", "RP5"})}

SCENARIOS = [
    Scenario("single F03 (conflict trap)", A, R6, ("TOY-F03",), REG, CONFLICT),
    Scenario("joint F02+F03 (synergistic)", A, R1, ("TOY-F02", "TOY-F03"), REG, CONFLICT,
             {frozenset({"extract_skills", "score"})}),
    Scenario("independent F01+F04 (decoy)", A, R4, ("TOY-F01", "TOY-F04"), REG),
    Scenario("independent F03+F04 (decoy)", A, R6, ("TOY-F03", "TOY-F04"), REG),
]

if __name__ == "__main__":
    res = evaluate4(ToyRepairAdapter(), SCENARIOS)
    for r in res["rows"]:
        print(f"{r['scenario']}\n  diagnosis={r['diagnosis']} interaction={r['interaction']} status={r['plan_status']}\n"
              f"  planner={r['planner']} (truth {r['truth']})  baseline blamed '{r['baseline_blamed']}' -> {r['baseline']}\n"
              f"  conflicts={r['conflicts']}")
        for w in r["warnings"]:
            print("  warning:", w)
    print({k: v for k, v in res.items() if k != "rows"})

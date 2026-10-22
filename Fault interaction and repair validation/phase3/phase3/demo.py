from .toy_agent import ToyAdapter
from .root_cause_engine import RootCauseEngine
from .evaluation import Case, evaluate

A = "toy"
R1 = {"resume": "Python and SQL developer with Docker", "required": ["python", "sql"]}
R2 = {"resume": "Experienced developer with python and sql", "required": ["python", "sql"]}
R3 = {"resume": "python sql", "required": ["python", "sql", "docker"]}
R4 = {"resume": "I know python and sql", "required": ["python", "sql", "docker"]}
M = {"decision": "match"}
CASES = [
    Case("S1-tokenize", A, R2, M, ("TOY-F01",)),
    Case("S2-extract", A, R3, M, ("TOY-F02",)),     # sql dropped -> 0.33 -> reject
    Case("S3-score", A, R3, M, ("TOY-F03",)),       # 2/4 = 0.5 -> still match (not failing)
    Case("S4-decide", A, R3, M, ("TOY-F04",)),
    Case("J1-extract+score", A, R1, M, ("TOY-F02", "TOY-F03")),   # each alone passes, together fail
    Case("J2-tokenize+decide", A, R4, M, ("TOY-F01", "TOY-F04")),   # both active
    Case("L1-latent-decide", A, R2, M, ("TOY-F01", "TOY-F04")),   # decide fault never exercised: only tokenize is a cause
]

if __name__ == "__main__":
    ad = ToyAdapter()
    res = evaluate(ad, RootCauseEngine(ad), CASES)
    for r in res["rows"]:
        print(f"{r['case']:20} truth={r['truth']} engine={r['engine']} ({r['verdict']}, {r['confidence']}, "
              f"{r['experiments']} exp) baseline={r['baseline']} pattern={r['pattern']}")
    print({k: v for k, v in res.items() if k != "rows"})

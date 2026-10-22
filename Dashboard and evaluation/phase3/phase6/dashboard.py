"""Streamlit dashboard.   Run:  python -m phase6.run_benchmark   then   streamlit run phase6/dashboard.py
(NOTE: written without Streamlit available in the build environment; the data layer it uses is tested, the UI itself is not.)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
from phase5.db import Database
from phase5.jobs import JobRunner
from phase5.orchestrator import ReviewOrchestrator
from phase6 import dashboard_data as dd
from phase6.benchmark import build, AGENT

OUT = os.environ.get("PHASE6_OUT", "phase6_results")
st.set_page_config(page_title="AI Agent Review System", layout="wide")


@st.cache_resource
def services():
    adapter, pool, reg, held, hidden, scenarios = build(7)
    db = Database(os.path.join(OUT, "app.db")) if os.path.isdir(OUT) else Database()
    orch = ReviewOrchestrator(adapter, db)
    runner = JobRunner(db)
    orch.register_with(runner)
    runner.start(2)
    return orch, runner, reg, held, scenarios


page = st.sidebar.radio("Page", ["Overview", "Case explorer", "Approvals", "Jobs & memory"])
orch, runner, reg, held, scenarios = services()

if page == "Overview":
    st.title("Final evaluation: pipeline vs baseline reviewer")
    if not os.path.exists(os.path.join(OUT, "results.json")):
        st.warning(f"No results in '{OUT}'. Run: python -m phase6.run_benchmark --out {OUT}")
        st.stop()
    res = dd.load_results(OUT)
    st.caption(f"{res['meta']['scenarios']} scenarios, seed {res['meta']['seed']}")
    st.subheader("Nine headline metrics")
    st.dataframe(dd.metric_table(res["summary"]), use_container_width=True, hide_index=True)
    st.subheader("By scenario group")
    st.dataframe(dd.slice_table(res["summary"]), use_container_width=True, hide_index=True)
    st.subheader("Post-hoc variant (added after seeing results; optimistic)")
    st.dataframe(dd.metric_table(res["summary_posthoc"]), use_container_width=True, hide_index=True)
    st.subheader("Where the pipeline went wrong (as shipped)")
    st.dataframe(res["summary"]["pipeline_misses"] or [{"note": "no misses"}], use_container_width=True)
    rep = os.path.join(OUT, "report.html")
    if os.path.exists(rep):
        st.download_button("Download full report (HTML)", open(rep, "rb").read(), "report.html", "text/html")

elif page == "Case explorer":
    st.title("Case explorer")
    kind = st.selectbox("Group", sorted({s.kind for s in scenarios}),
                        index=sorted({s.kind for s in scenarios}).index("double_synergistic"))
    sid = st.selectbox("Scenario", [s.sid for s in scenarios if s.kind == kind])
    resid = st.checkbox("Enable post-hoc residual-fault gate", value=False)
    if st.button("Run full review"):
        w = dd.walkthrough(sid, residual_check=resid)
        st.session_state["walk"] = w
    w = st.session_state.get("walk")
    if w and w["scenario"]["sid"] == sid:
        c1, c2 = st.columns(2)
        c1.metric("Outcome", w["outcome"])
        c2.metric("Selected repairs", ", ".join(r["repair_id"] for r in w["selected_repairs"]) or "none")
        st.write("**Injected faults**", w["scenario"]["faults"], "**Oracle root-cause stages**", w["scenario"]["truth_stages"])
        st.subheader("Pipeline steps"); st.dataframe(w["steps"], use_container_width=True, hide_index=True)
        if w["diagnosis"]:
            st.subheader("Diagnosis"); st.write(w["diagnosis"]["verdict"], w["diagnosis"]["suspected_stages"], w["diagnosis"]["confidence"])
            st.write(w["diagnosis"]["evidence"])
        if w["interaction"]:
            st.subheader(f"Interaction test (2^k factorial): {w['interaction']['summary']}")
            st.dataframe(w["interaction"]["outcomes"], use_container_width=True)
        if w["plan"]:
            st.subheader("Repair candidates"); st.dataframe(w["plan"]["candidates"], use_container_width=True)
            st.subheader("Repair conflicts"); st.dataframe(w["plan"]["conflicts"] or [{"note": "none"}], use_container_width=True)
            st.write(w["plan"]["warnings"])
        if w["gate_attempts"]:
            st.subheader("Hard gates"); st.dataframe(w["gate_attempts"], use_container_width=True)
            if w["gates"]:
                st.dataframe(w["gates"]["results"], use_container_width=True, hide_index=True)

elif page == "Approvals":
    st.title("Human approval queue")
    reviewer = st.text_input("Your name (required)")
    for req in orch.approvals.list("pending"):
        with st.expander(f"#{req['id']} {req['agent_id']} - {[r['repair_id'] for r in req['payload']['repairs']]}"):
            st.json(req["payload"])
            note = st.text_input("Note", key=f"n{req['id']}")
            a, b = st.columns(2)
            if a.button("Approve", key=f"a{req['id']}") and reviewer.strip():
                orch.approve(req["id"], reviewer, note); st.rerun()
            if b.button("Reject", key=f"r{req['id']}") and reviewer.strip():
                orch.reject(req["id"], reviewer, note); st.rerun()
    st.subheader("Approved, awaiting apply")
    for req in orch.approvals.list("approved"):
        if st.button(f"Apply #{req['id']}", key=f"ap{req['id']}"):
            st.write("Deploy these repairs:", orch.apply(req["id"]))

else:
    st.title("Jobs & failure memory")
    pick = st.selectbox("Submit a scenario as a background job", [s.sid for s in scenarios])
    if st.button("Submit"):
        s = next(x for x in scenarios if x.sid == pick)
        d = lambda c: dict(case_id=c["case_id"], input=c["input"], expected=c["expected"])
        runner.submit("review", dict(agent_id=AGENT, target=d(s.target), faults=s.faults,
                                     regression=[d(c) for c in reg], heldout=[d(c) for c in held]))
    st.dataframe([{k: j[k] for k in ("id", "status", "attempts", "error")} for j in runner.list()], use_container_width=True)
    st.subheader("Failure memory")
    st.dataframe([dict(zip(("id", "stages", "repairs", "status", "confirmations", "uses", "successes", "rejections"), r))
                  for r in orch.db.query("SELECT id,suspected_stages,repair_ids,status,confirmations,uses,successes,rejections "
                                         "FROM failure_memory")], use_container_width=True)

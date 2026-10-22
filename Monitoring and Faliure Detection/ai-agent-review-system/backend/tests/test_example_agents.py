"""Behaviour of the three example agents against their benchmark expectations."""
import pytest

from app.integration import OVERRIDE_CONFIG, OVERRIDE_STAGE, OVERRIDE_TOOL, OverrideError
from app.integration.case_loader import load_cases
from app.target_agents.recruitment.resume_parser import extract_education, extract_skills, extract_years
from app.target_agents.recruitment.settings import apply_overrides, load_config


# ---- recruitment -------------------------------------------------------------------

def test_recruitment_parser_details():
    config = load_config()
    assert extract_skills("Built apps in JavaScript and ReactJS", config) == ["javascript", "react"]
    assert "java" not in extract_skills("Expert in JavaScript", config)
    assert extract_years("3 years here, then 5+ years there") == 5.0
    assert extract_education("Master of Science", config) == (3, "master")
    assert extract_education("Mastering the art of cooking", config) == (0, "none")
    reduced = apply_overrides(config, {"parser.disabled_skills": ["python"]})
    assert "python" not in extract_skills("Python and SQL", reduced) and "python" in extract_skills("Python and SQL", config)


def test_recruitment_overrides_change_results(executor, settings):
    case = next(c for c in load_cases(settings.data_dir, "recruitment-agent") if "below_min_experience" in c["tags"])
    capped = executor.execute("recruitment-agent", case["input"])
    relaxed = executor.execute(
        "recruitment-agent", case["input"], overrides={OVERRIDE_CONFIG: {"ranking.enforce_experience_filter": False}}
    )
    assert capped.output["match_score"] <= 40 < relaxed.output["match_score"]

    # Counterfactual hook: pretend the parser lost skills for a fully qualified candidate.
    qualified = next(c for c in load_cases(settings.data_dir, "recruitment-agent") if "qualified" in c["tags"])
    baseline = executor.execute("recruitment-agent", qualified["input"])
    profile = dict(baseline.output["candidate_profile"], skills=["sql"])
    replaced = executor.execute("recruitment-agent", qualified["input"], overrides={OVERRIDE_STAGE: {"resume_parser": profile}})
    assert replaced.output["match_score"] < baseline.output["match_score"]
    assert [e.name for e in replaced.events if e.overridden] == ["resume_parser"]


def test_recruitment_rejects_malformed_stage_override(executor, settings):
    case = load_cases(settings.data_dir, "recruitment-agent")[0]
    with pytest.raises(OverrideError):
        executor.execute("recruitment-agent", case["input"], overrides={OVERRIDE_STAGE: {"resume_parser": {"skills": []}}})
    with pytest.raises(OverrideError):
        executor.execute("recruitment-agent", case["input"], overrides={OVERRIDE_STAGE: {"job_retrieval": {"not": "list"}}})


# ---- FAQ chatbot -----------------------------------------------------------------------

def test_faq_unanswerable_question_gets_fallback(executor):
    out = executor.execute("faq-chatbot", {"question": "What is the weather today?"}).output
    assert out["source_id"] is None and "could not find" in out["answer"]


def test_faq_stage_and_config_overrides(executor):
    question = {"question": "How do I reset my password?"}
    forced = executor.execute("faq-chatbot", question, overrides={OVERRIDE_STAGE: {"intent_detection": "greeting"}})
    assert forced.output["answer"].startswith("Hello") and forced.events[0].overridden
    strict = executor.execute("faq-chatbot", question, overrides={OVERRIDE_CONFIG: {"response.answer_threshold": 0.99}})
    assert strict.output["source_id"] is None  # retrieval still found F01, but the threshold rejects it
    assert strict.output["retrieved"][0]["faq_id"] == "F01"
    with pytest.raises(OverrideError):
        executor.execute("faq-chatbot", question, overrides={OVERRIDE_STAGE: {"response_generation": {"no_answer": 1}}})


# ---- calculator (tool-using) --------------------------------------------------------------

def test_calculator_trace_contains_a_tool_call(executor):
    result = executor.execute("calculator-agent", {"question": "What is 12 plus 30 times 2?"})
    assert [(e.kind, e.name) for e in result.events] == [("stage", "plan"), ("tool_call", "calculator"), ("stage", "respond")]
    assert result.events[1].input == {"expression": "12 + 30 * 2"} and result.events[1].output == 72


def test_calculator_tool_failure_keeps_partial_trace(executor):
    result = executor.execute("calculator-agent", {"question": "What is 5 divided by 0?"})
    assert result.status == "error" and result.error["message"] == "Division by zero"
    assert [e.name for e in result.events] == ["plan", "calculator"]
    assert result.events[-1].error.startswith("ToolError")


def test_calculator_tool_override_mocks_the_tool(executor):
    result = executor.execute(
        "calculator-agent", {"question": "What is 2 plus 2?"}, overrides={OVERRIDE_TOOL: {"calculator": 99}}
    )
    assert result.output["result"] == 99 and result.events[1].overridden
    with pytest.raises(OverrideError):
        executor.execute("calculator-agent", {"question": "What is 2 plus 2?"}, overrides={OVERRIDE_TOOL: {"calculator": "99"}})
    with pytest.raises(OverrideError):
        executor.execute("calculator-agent", {"question": "What is 2 plus 2?"}, overrides={OVERRIDE_TOOL: {"browser": 1}})


def test_calculator_never_executes_arbitrary_code(executor):
    # Letters are stripped by the planner; direct tool misuse is also rejected.
    from app.integration.config_utils import load_yaml
    from app.target_agents.calculator_agent.calculator_agent import ToolError, safe_eval
    from pathlib import Path
    import app.target_agents.calculator_agent as pkg

    cfg = load_yaml(Path(pkg.__file__).parent / "config.yaml")
    for bad in ("__import__('os').system('echo hi')", "2 ** 999", "(1", "[1, 2]", "abs(3)"):
        with pytest.raises(ToolError):
            safe_eval(bad, cfg)
    out = executor.execute("calculator-agent", {"question": "import os; os.system('ls') plus 2"})
    assert out.status in ("success", "error")  # never crashes the reviewer

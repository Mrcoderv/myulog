import pytest

from ulog.parsers.agentic import AgenticParser


@pytest.fixture()
def p():
    return AgenticParser()


def test_langchain_gt_lines_chain_start_and_end(p):
    res1 = p.parse("> Entering new AgentExecutor chain...")
    assert res1.success is True
    assert res1.data["category"] == "workflow"
    assert res1.data["step_kind"] in {"chain_start", "step"}
    # chain name extraction is best-effort; don't assert for exact value

    res2 = p.parse("> Finished chain.")
    assert res2.success is True
    assert res2.data["step_kind"] in {"chain_end", "step"}


@pytest.mark.parametrize(
    "line,expected",
    [
        ("Thought: we should call a tool", "reasoning"),
        ("Action: web_search", "tool_selection"),
        ("Action Input: {'q': 'python'}", "tool_input"),
        ("Observation: 5 results", "tool_output"),
        ("Final Answer: Done", "final_answer"),
    ],
)
def test_langchain_step_lines(p, line, expected):
    r = p.parse(line)
    assert r.success
    assert r.data["step_kind"] == expected
    assert r.data["message"]


def test_session_start_with_kv_extraction(p):
    line = (
        "[Agent] session_start id=agnt-6f21f req_id=42 model=llm-7b "
        "locale='es-ES' tz=\"Europe/Madrid\""
    )
    r = p.parse(line)
    assert r.success
    d = r.data
    assert d["category"] == "workflow"
    assert d["step_kind"] == "session_start"
    # typed KV extraction
    assert d["req_id"] == 42
    assert d["model"] == "llm-7b"
    assert d["locale"] == "es-ES"
    assert d["tz"] == "Europe/Madrid"


def test_tool_call_success_and_failure_levels(p):
    ok = p.parse("[Tool] call web_search args={'q':'python','k':5} timeout=6000ms")
    assert ok.success
    assert ok.data["category"] == "tool"
    assert ok.data["step_kind"] == "tool_call"
    assert ok.data["tool_name"] == "web_search"
    # no explicit level -> infer info -> outcome success
    assert ok.data["level"] == "info"
    assert ok.data["outcome"] == "success"

    fail = p.parse("[Tool][ERROR] code_exec exit_code=1 stderr='ModuleNotFoundError'")
    assert fail.success
    assert fail.data["level"] == "error"
    assert fail.data["outcome"] == "failure"
    assert fail.data["tool_name"] == "code_exec"
    assert fail.data["exit_code"] == 1


def test_graph_state_transition(p):
    r = p.parse("[Graph] state=PLAN -> ACT reason='ready_to_execute_first_tool'")
    assert r.success
    d = r.data
    assert d["category"] == "workflow"
    assert d["step_kind"] == "state_transition"
    assert d["from_state"] == "PLAN"
    assert d["to_state"] == "ACT"
    assert d["reason"] == "ready_to_execute_first_tool"


@pytest.mark.parametrize(
    "line,cat,step",
    [
        ("[Planner] plan_created steps=7", "planning", "plan"),
        ("[Selector] ranked_tools=[('a',0.9)] chosen='a'", "decision", "tool_selection"),
        ("[Memory] read scope=session k=5", "memory", "memory_access"),
        ("[Guard] jailbreak_check=clean", "safety", "safety_check"),
        ("[RAG] vector_search top_k=6", "rag", "retrieval"),
        ("[Reviewer] code ok", "review", "code_review"),
        ("[SelfHeal] attempt=2", "self_healing", "error_recovery"),
        ("[Handoff] to='arbiter'", "orchestration", "handoff"),
        ("[Cost] usd=0.004", "observability", "cost_tracking"),
        ("[Events] stream open", "streaming", "stream_event"),
        ("[RateLimit] hits=10", "rate_limiting", "rate_limit"),
        ("[Auth] ok", "security", "auth"),
        ("[Retry] backoff=2", "resilience", "retry"),
        ("[CircuitBreaker] closed", "resilience", "circuit_breaker"),
        ("[Orchestrator] tick", "orchestration", "orchestration"),
        ("[Researcher] query", "research", "research"),
        ("[Timeout] after=30s", "timeout", "timeout"),
        ("[Cancel] by=user", "cancellation", "cancel"),
        ("[Router] chosen='A'", "routing", "route"),
        ("[Sampler] t=1.0", "inference", "sampling"),
        ("[JSON] formatted", "formatting", "format"),
        ("[Compliance] ok", "compliance", "audit"),
        ("[Output] delivered", "output", "output"),
        ("[Shutdown] now", "lifecycle", "shutdown"),
        ("[Fallback] used", "error_handling", "fallback"),
        ("[Structured] emitted", "output", "structured_output"),
    ],
)
def test_agentic_component_mapping_and_inferred_level(p, line, cat, step):
    r = p.parse(line)
    assert r.success
    d = r.data
    assert d["category"] == cat
    assert d["step_kind"] == step
    assert d["level"] in {"info", "warning", "error"}


def test_agentic_parse_failure_branch(p):
    r = p.parse("this does not look like an agent log")
    assert r.success is False
    assert r.error == "no_pattern_match"
    assert r.unparsed_reason == "no_pattern_match"

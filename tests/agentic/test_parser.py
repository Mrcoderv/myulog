"""Tests for Agentic parser."""
from ulog.parsers.agentic import AgenticParser


class TestAgenticParser:
    def setup_method(self):
        self.parser = AgenticParser()

    def test_session_start(self):
        log = "[Agent] session_start id=agnt-6f21f req_id=4a2c model=llm-7b locale=es-ES tz=Europe/Madrid"
        res = self.parser.parse(log)
        assert res.success
        assert res.pattern_id == "agent_session_event"
        assert res.data["step_kind"] == "session_start"
        assert res.data["category"] == "workflow"

    def test_state_transition(self):
        log = "[Graph] state=PLAN -> ACT reason='ready_to_execute_first_tool'"
        res = self.parser.parse(log)
        assert res.success
        assert res.pattern_id == "graph_state_transition"
        assert res.data["from_state"] == "PLAN"
        assert res.data["to_state"] == "ACT"

    def test_tool_call_success(self):
        log = "[Tool] call web_search args={'q':'python logging'} timeout=6000ms"
        res = self.parser.parse(log)
        assert res.success
        assert res.pattern_id == "tool_call_event"
        assert res.data["tool_name"] == "web_search"
        assert res.data["step_kind"] == "tool_call"
        assert res.data["outcome"] == "success"

    def test_agentic_component_planner(self):
        log = "[Planner] plan_created plan_id=pln-0a91 steps=7"
        res = self.parser.parse(log)
        assert res.success
        assert res.pattern_id == "agentic_component_log"
        assert res.data["category"] == "planning"
        assert res.data["step_kind"] == "plan"
        assert res.data["steps"] == 7

    def test_agentic_component_guard_warning(self):
        log = "[Guard][WARN] jailbreak_check=clean prompt_injection=none"
        res = self.parser.parse(log)
        assert res.success
        assert res.data["category"] == "safety"
        assert res.data["level"] in ("warning", "warn")  # normalized downstream

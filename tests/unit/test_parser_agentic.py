"""
Unit tests for Agentic parser (raw → json).
"""



class TestAgenticParserRawToJson:
    """Test raw log parsing for agentic domain (≥8 tests)."""

    def test_agentic_tool_call_success(self, agentic_parser):
        """Test parsing successful tool call."""
        raw = "Tool call: search_web completed successfully in 2500ms"
        result = agentic_parser.parse(raw)
        
        assert result is not None

    def test_agentic_tool_call_failure(self, agentic_parser):
        """Test parsing failed tool call."""
        raw = "Tool call: database_query failed with error: Connection timeout"
        result = agentic_parser.parse(raw)
        
        assert result is not None

    def test_agentic_planner_step(self, agentic_parser):
        """Test parsing planner step."""
        raw = "Planner step: analyzing user intent for workflow wf_123"
        result = agentic_parser.parse(raw)
        
        assert result is not None

    def test_agentic_guardrail_triggered(self, agentic_parser):
        """Test parsing guardrail trigger."""
        raw = "Guardrail triggered: content_safety for step step_456"
        result = agentic_parser.parse(raw)
        
        assert result is not None

    def test_agentic_workflow_start(self, agentic_parser):
        """Test parsing workflow start."""
        raw = "Workflow started: id=wf_789, user=user_abc"
        result = agentic_parser.parse(raw)
        
        assert result is not None

    def test_agentic_cost_tracking(self, agentic_parser):
        """Test parsing cost tracking log."""
        raw = "Cost tracking: workflow wf_123 accumulated $0.45 USD"
        result = agentic_parser.parse(raw)
        
        assert result is not None

    def test_agentic_tool_dependency_error(self, agentic_parser):
        """Test parsing tool dependency error."""
        raw = "ModuleNotFoundError: No module named 'requests' in tool http_client"
        result = agentic_parser.parse(raw)
        
        assert result is not None

    def test_agentic_step_duration(self, agentic_parser):
        """Test parsing step duration measurement."""
        raw = "Step completed: step_kind=tool_call, duration=65000ms"
        result = agentic_parser.parse(raw)
        
        assert result is not None

    def test_agentic_ranked_tools(self, agentic_parser):
        """Test parsing ranked tools selection."""
        raw = "Ranked tools for task: [search_web, calculator, database_query]"
        result = agentic_parser.parse(raw)
        
        assert result is not None

    def test_agentic_plan_generation(self, agentic_parser):
        """Test parsing plan generation."""
        raw = "Generated plan: 5 steps for goal 'analyze data'"
        result = agentic_parser.parse(raw)
        
        assert result is not None

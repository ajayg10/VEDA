import sys
import types
import unittest

openai = types.ModuleType("openai")
openai.AsyncOpenAI = object
sys.modules.setdefault("openai", openai)
from core.planner import Planner
from shared.models import ExecutionPlan, TaskStep, ToolType


class PlannerBrowserRoutingTests(unittest.TestCase):
    def test_open_website_goal_uses_browser_action_instead_of_http_get(self):
        plan = ExecutionPlan(goal="Open google.com", reasoning="test", steps=[TaskStep(step_id=1, description="Open", tool=ToolType.HTTP_REQUEST, parameters={"method": "GET", "url": "https://google.com"}, rationale="test")], estimated_complexity="low", requires_confirmation=False)

        routed = Planner._prefer_browser_actions("Open google.com", plan)

        self.assertEqual(routed.steps[0].tool, ToolType.BROWSER_ACTION)
        self.assertTrue(routed.requires_confirmation)

    def test_explicit_http_goal_remains_an_http_request(self):
        plan = ExecutionPlan(goal="GET API", reasoning="test", steps=[TaskStep(step_id=1, description="Get", tool=ToolType.HTTP_REQUEST, parameters={"method": "GET", "url": "https://example.com"}, rationale="test")], estimated_complexity="low", requires_confirmation=False)

        routed = Planner._prefer_browser_actions("Make an HTTP GET API request", plan)

        self.assertEqual(routed.steps[0].tool, ToolType.HTTP_REQUEST)

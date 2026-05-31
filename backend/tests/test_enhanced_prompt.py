"""Tests for _build_enhanced_prompt in orchestrator."""

import unittest

from app.agents.review.orchestrator import _build_enhanced_prompt
from app.agents.review.specialist import SECURITY_AGENT, STYLE_AGENT
from app.schemas.review_rule import ReviewRuleOut


def _make_rule(category: str = "security", name: str = "test_rule") -> ReviewRuleOut:
    return ReviewRuleOut(
        id=1,
        user_id=1,
        name=name,
        category=category,
        prompt_content="Check for SQL injection patterns.",
        is_enabled=True,
        priority=10,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _make_example(file: str = "auth.py", issue: str = "Hardcoded secret") -> dict:
    return {"file": file, "line": 42, "issue": issue, "suggestion": "Use env var"}


class BuildEnhancedPromptTests(unittest.TestCase):
    def test_returns_base_prompt_when_no_rules_or_examples(self) -> None:
        prompt = _build_enhanced_prompt(SECURITY_AGENT)
        self.assertEqual(prompt, SECURITY_AGENT.system_prompt)

    def test_injects_matching_custom_rules(self) -> None:
        rule = _make_rule("security")
        prompt = _build_enhanced_prompt(SECURITY_AGENT, custom_rules=[rule])
        self.assertIn("## 团队自定义审查规则", prompt)
        self.assertIn("[自定义规则: test_rule]", prompt)
        self.assertIn("Check for SQL injection patterns.", prompt)

    def test_skips_non_matching_rules(self) -> None:
        rule = _make_rule("style")  # style rule for security agent
        prompt = _build_enhanced_prompt(SECURITY_AGENT, custom_rules=[rule])
        self.assertNotIn("团队自定义审查规则", prompt)

    def test_custom_category_matches_all_agents(self) -> None:
        rule = _make_rule("custom")
        prompt = _build_enhanced_prompt(SECURITY_AGENT, custom_rules=[rule])
        self.assertIn("团队自定义审查规则", prompt)

    def test_sorts_rules_by_priority_desc(self) -> None:
        rules = [
            ReviewRuleOut(id=1, user_id=1, name="low", category="security",
                          prompt_content="low prio", is_enabled=True, priority=1,
                          created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z"),
            ReviewRuleOut(id=2, user_id=1, name="high", category="security",
                          prompt_content="high prio", is_enabled=True, priority=99,
                          created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z"),
        ]
        prompt = _build_enhanced_prompt(SECURITY_AGENT, custom_rules=rules)
        high_pos = prompt.index("high prio")
        low_pos = prompt.index("low prio")
        self.assertLess(high_pos, low_pos)

    def test_injects_helpful_examples(self) -> None:
        examples = [_make_example()]
        prompt = _build_enhanced_prompt(SECURITY_AGENT, helpful_examples=examples)
        self.assertIn("## 参考示例", prompt)
        self.assertIn("Hardcoded secret", prompt)
        self.assertIn("Use env var", prompt)

    def test_example_omits_line_when_none(self) -> None:
        examples = [{"file": "util.py", "line": None, "issue": "X", "suggestion": "Y"}]
        prompt = _build_enhanced_prompt(SECURITY_AGENT, helpful_examples=examples)
        self.assertNotIn(":None", prompt)

    def test_caps_examples_at_five(self) -> None:
        examples = [_make_example(f"f{i}.py", f"issue{i}") for i in range(10)]
        prompt = _build_enhanced_prompt(SECURITY_AGENT, helpful_examples=examples)
        # "示例N" appears 5 times (header "参考示例" is excluded because it uses "示例N" not bare "示例")
        self.assertEqual(prompt.count("示例"), 6)  # 5 examples + header line

    def test_combines_rules_and_examples(self) -> None:
        rule = _make_rule()
        examples = [_make_example()]
        prompt = _build_enhanced_prompt(SECURITY_AGENT, custom_rules=[rule], helpful_examples=examples)
        self.assertIn("参考示例", prompt)
        self.assertIn("团队自定义审查规则", prompt)


if __name__ == "__main__":
    unittest.main()

from dataclasses import dataclass

from app.agents.review.prompts.performance import SYSTEM_PROMPT as PERFORMANCE_PROMPT
from app.agents.review.prompts.security import SYSTEM_PROMPT as SECURITY_PROMPT
from app.agents.review.prompts.style import SYSTEM_PROMPT as STYLE_PROMPT


@dataclass(frozen=True)
class SpecialistAgent:
    name: str
    model: str
    system_prompt: str
    category_prefix: str
    include_pattern: str | None
    max_files: int


SECURITY_AGENT = SpecialistAgent(
    name="security",
    model="deepseek-v4-pro",
    system_prompt=SECURITY_PROMPT,
    category_prefix="[安全]",
    include_pattern=r"auth|login|token|session|permission|middleware|config|crypto|secret",
    max_files=30,
)

PERFORMANCE_AGENT = SpecialistAgent(
    name="performance",
    model="deepseek-v4-pro",
    system_prompt=PERFORMANCE_PROMPT,
    category_prefix="[性能]",
    include_pattern=None,
    max_files=40,
)

STYLE_AGENT = SpecialistAgent(
    name="style",
    model="deepseek-v4-flash",
    system_prompt=STYLE_PROMPT,
    category_prefix="[风格]",
    include_pattern=None,
    max_files=35,
)

MULTI_AGENTS = (SECURITY_AGENT, PERFORMANCE_AGENT, STYLE_AGENT)

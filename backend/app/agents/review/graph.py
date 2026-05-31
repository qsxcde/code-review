import time

from langgraph.graph import END, StateGraph

from app.agents.interfaces import GitHubProvider, LLMProvider
from app.agents.review.nodes import ReviewWorkflowNodes
from app.agents.state import ReviewState
from app.schemas.review import ReviewAnalyzeResponse


class ReviewGraphRunner:
    def __init__(
        self,
        github_service: GitHubProvider,
        llm_service: LLMProvider,
    ) -> None:
        nodes = ReviewWorkflowNodes(github_service, llm_service)
        graph = StateGraph(ReviewState)
        graph.add_node("parse_pr_url", nodes.parse_pr_url)
        graph.add_node("fetch_pr_data", nodes.fetch_pr_data)
        graph.add_node("build_context", nodes.build_context)
        graph.add_node("analyze_review", nodes.analyze_review)
        graph.add_node("validate_result", nodes.validate_result)

        graph.set_entry_point("parse_pr_url")
        graph.add_edge("parse_pr_url", "fetch_pr_data")
        graph.add_edge("fetch_pr_data", "build_context")
        graph.add_edge("build_context", "analyze_review")
        graph.add_edge("analyze_review", "validate_result")
        graph.add_edge("validate_result", END)

        self.graph = graph.compile()

    async def analyze(self, pr_url: str) -> ReviewAnalyzeResponse:
        final_state = await self.graph.ainvoke(
            {
                "pr_url": pr_url,
                "started_at": time.perf_counter(),
                "errors": [],
            }
        )
        return final_state["response"]

from app.agents.state import ReviewState
from app.services.github_pr import GitHubPRService
from app.services.llm_review import LLMReviewService
from app.services.review_context import (
    build_context,
    build_validate_response,
    normalize_analysis,
)


class ReviewWorkflowNodes:
    def __init__(
        self,
        github_service: GitHubPRService,
        llm_service: LLMReviewService,
    ) -> None:
        self.github_service = github_service
        self.llm_service = llm_service

    async def parse_pr_url(self, state: ReviewState) -> ReviewState:
        owner, repo, pull_number = self.github_service.parse_pr_url(state["pr_url"])
        return {
            **state,
            "owner": owner,
            "repo": repo,
            "pull_number": pull_number,
        }

    async def fetch_pr_data(self, state: ReviewState) -> ReviewState:
        pr_data = await self.github_service.fetch_parsed_pr(
            state["owner"],
            state["repo"],
            state["pull_number"],
        )
        return {
            **state,
            "pr_data": pr_data,
        }

    async def build_context(self, state: ReviewState) -> ReviewState:
        context, file_count = build_context(state["pr_data"])
        return {
            **state,
            "context": context,
            "analyzed_file_count": file_count,
        }

    async def analyze_review(self, state: ReviewState) -> ReviewState:
        analysis = await self.llm_service.analyze_payload(state["context"])
        return {
            **state,
            "analysis": analysis,
        }

    async def validate_result(self, state: ReviewState) -> ReviewState:
        analysis = normalize_analysis(
            state["analysis"],
            analyzed_file_count=state["analyzed_file_count"],
        )
        response = build_validate_response(
            state["pr_data"],
            analysis,
            state["started_at"],
        )
        return {
            **state,
            "analysis": analysis,
            "response": response,
        }

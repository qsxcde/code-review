import time

from app.agents.review.context import ReviewContextBuilder
from app.agents.review.normalizer import ReviewResultNormalizer
from app.agents.state import ReviewState
from app.schemas.review import ReviewAnalyzeResponse, ReviewPRInfo
from app.services.github import GitHubPRService
from app.services.llm import LLMReviewService


class ReviewWorkflowNodes:
    def __init__(
        self,
        github_service: GitHubPRService,
        llm_service: LLMReviewService,
        context_builder: ReviewContextBuilder | None = None,
        normalizer: ReviewResultNormalizer | None = None,
    ) -> None:
        self.github_service = github_service
        self.llm_service = llm_service
        self.context_builder = context_builder or ReviewContextBuilder()
        self.normalizer = normalizer or ReviewResultNormalizer()

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
        context, analyzed_file_count = self.context_builder.build(state["pr_data"])
        return {
            **state,
            "context": context,
            "analyzed_file_count": analyzed_file_count,
        }

    async def analyze_review(self, state: ReviewState) -> ReviewState:
        analysis = await self.llm_service.analyze_payload(state["context"])
        return {
            **state,
            "analysis": analysis,
        }

    async def validate_result(self, state: ReviewState) -> ReviewState:
        analysis = self.normalizer.normalize(
            state["analysis"],
            analyzed_file_count=state["analyzed_file_count"],
        )
        pr_data = state["pr_data"]
        response = ReviewAnalyzeResponse(
            pr=ReviewPRInfo(
                title=pr_data.title,
                url=pr_data.html_url,
                author=pr_data.author,
                owner=pr_data.owner,
                repo=pr_data.repo,
                number=pr_data.number,
                baseBranch=pr_data.base_branch,
                headBranch=pr_data.head_branch,
            ),
            analysis=analysis,
            durationMs=int((time.perf_counter() - state["started_at"]) * 1000),
        )
        return {
            **state,
            "analysis": analysis,
            "response": response,
        }

from fastapi import APIRouter

from app.api.v1.endpoints import auth, github, health, review, review_history, review_progress

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(github.router)
api_router.include_router(review.router)
api_router.include_router(review_history.router)
api_router.include_router(review_progress.router)
api_router.include_router(auth.router)

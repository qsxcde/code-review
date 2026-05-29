from pydantic import BaseModel


class HealthCheck(BaseModel):
    status: str


class DependencyCheck(BaseModel):
    name: str
    status: str
    detail: str | None = None


class ReadinessCheck(BaseModel):
    status: str
    dependencies: list[DependencyCheck]

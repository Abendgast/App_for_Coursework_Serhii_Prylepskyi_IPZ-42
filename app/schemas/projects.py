from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

ProjectName = Annotated[
    str,
    StringConstraints(min_length=1, max_length=100, strip_whitespace=True),
]
ProjectDescription = Annotated[
    str | None,
    StringConstraints(max_length=5_000, strip_whitespace=True),
]


class ProjectCreate(BaseModel):
    name: ProjectName
    description: ProjectDescription = None


class ProjectUpdate(BaseModel):
    name: ProjectName | None = None
    description: ProjectDescription = None


class ProjectReplace(BaseModel):
    name: ProjectName
    description: ProjectDescription


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    runs_count: int


class ProjectCreatedResponse(ProjectResponse):
    api_key: str


class FlakyTestResponse(BaseModel):
    classname: str
    name: str
    total_runs: int
    failed_runs: int
    failure_rate: float


class ProjectStatisticsResponse(BaseModel):
    project_id: str
    total_runs: int
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    average_pass_rate: float
    latest_run_id: str | None
    latest_run_status: str | None

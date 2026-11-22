from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TestCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    classname: str
    name: str
    status: str
    duration_seconds: float
    error_message: str | None


class TestSuiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    cases: list[TestCaseResponse]


class TestRunResponse(BaseModel):
    id: str
    project_id: str
    source_filename: str
    report_format: str
    build_number: int | None
    branch: str
    status: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    duration_seconds: float
    pass_rate: float
    created_at: datetime


class TestRunDetailsResponse(TestRunResponse):
    suites: list[TestSuiteResponse]


class TestRunListResponse(BaseModel):
    items: list[TestRunResponse]
    total: int

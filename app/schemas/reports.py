from math import isfinite
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

CaseStatus = Literal["passed", "failed", "skipped"]


class JsonCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str,
        StringConstraints(min_length=1, max_length=255, strip_whitespace=True),
    ]
    status: CaseStatus
    classname: Annotated[str, StringConstraints(max_length=255, strip_whitespace=True)] = ""
    duration_seconds: Annotated[float, Field(ge=0, le=604800)] = 0
    error_message: Annotated[str | None, Field(max_length=10_000)] = None

    @field_validator("duration_seconds")
    @classmethod
    def duration_must_be_finite(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("duration_seconds must be finite")
        return value

    @field_validator("error_message")
    @classmethod
    def error_message_only_for_failed_case(cls, value: str | None, info):
        if value is not None and info.data.get("status") != "failed":
            raise ValueError("error_message is only valid for failed tests")
        return value


class JsonSuite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str,
        StringConstraints(min_length=1, max_length=255, strip_whitespace=True),
    ]
    tests: Annotated[list[JsonCase], Field(max_length=10_000)]


class JsonTestReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    build_number: Annotated[int | None, Field(ge=0)] = None
    branch: Annotated[
        str,
        StringConstraints(min_length=1, max_length=255, strip_whitespace=True),
    ] = "main"
    suites: Annotated[list[JsonSuite], Field(min_length=1, max_length=1_000)]

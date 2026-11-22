from collections import defaultdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import DatabaseSession, IngestionProject, get_current_user
from app.models import Project, TestCase, TestRun, TestSuite, User
from app.schemas.projects import (
    FlakyTestResponse,
    ProjectCreate,
    ProjectCreatedResponse,
    ProjectReplace,
    ProjectResponse,
    ProjectStatisticsResponse,
    ProjectUpdate,
)
from app.schemas.runs import (
    TestRunDetailsResponse,
    TestRunListResponse,
    TestRunResponse,
)
from app.services.projects import (
    ProjectAlreadyExists,
    ProjectNotFound,
    create_project,
    delete_project,
    get_owned_project,
    ingest_report,
    list_owned_projects,
    update_project,
)
from app.services.reports import MAX_REPORT_BYTES, InvalidReport, parse_report

router = APIRouter(tags=["projects", "test runs"])
AuthenticatedUser = Annotated[User, Depends(get_current_user)]


def _project_response(project: Project, runs_count: int = 0) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        runs_count=runs_count,
    )


def _get_owned_project_or_404(
    project_id: UUID,
    current_user: User,
    session: Session,
) -> Project:
    try:
        return get_owned_project(str(project_id), current_user.id, session)
    except ProjectNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from error


def _run_response(run: TestRun) -> TestRunResponse:
    return TestRunResponse.model_validate(
        {
            "id": run.id,
            "project_id": run.project_id,
            "source_filename": run.source_filename,
            "report_format": run.report_format,
            "build_number": run.build_number,
            "branch": run.branch,
            "status": run.status,
            "total_tests": run.total_tests,
            "passed_tests": run.passed_tests,
            "failed_tests": run.failed_tests,
            "skipped_tests": run.skipped_tests,
            "duration_seconds": run.duration_seconds,
            "pass_rate": run.pass_rate,
            "created_at": run.created_at,
        }
    )


@router.post(
    "/projects",
    response_model=ProjectCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_endpoint(
    payload: ProjectCreate,
    current_user: AuthenticatedUser,
    session: DatabaseSession,
) -> ProjectCreatedResponse:
    try:
        project, api_key = create_project(payload, current_user.id, session)
    except ProjectAlreadyExists as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A project with this name already exists",
        ) from error
    return ProjectCreatedResponse(
        **_project_response(project).model_dump(),
        api_key=api_key,
    )


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(
    current_user: AuthenticatedUser,
    session: DatabaseSession,
) -> list[ProjectResponse]:
    return [
        _project_response(project, runs_count)
        for project, runs_count in list_owned_projects(current_user.id, session)
    ]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def read_project(
    project_id: UUID,
    current_user: AuthenticatedUser,
    session: DatabaseSession,
) -> ProjectResponse:
    project = _get_owned_project_or_404(project_id, current_user, session)
    runs_count = session.scalar(
        select(func.count(TestRun.id)).where(TestRun.project_id == project.id)
    )
    return _project_response(project, runs_count or 0)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
def edit_project(
    project_id: UUID,
    payload: ProjectUpdate,
    current_user: AuthenticatedUser,
    session: DatabaseSession,
) -> ProjectResponse:
    project = _get_owned_project_or_404(project_id, current_user, session)
    try:
        project = update_project(project, payload, session)
    except ProjectAlreadyExists as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A project with this name already exists",
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    runs_count = session.scalar(
        select(func.count(TestRun.id)).where(TestRun.project_id == project.id)
    )
    return _project_response(project, runs_count or 0)


@router.put("/projects/{project_id}", response_model=ProjectResponse)
def replace_project(
    project_id: UUID,
    payload: ProjectReplace,
    current_user: AuthenticatedUser,
    session: DatabaseSession,
) -> ProjectResponse:
    project = _get_owned_project_or_404(project_id, current_user, session)
    try:
        project = update_project(
            project,
            ProjectUpdate.model_validate(payload.model_dump()),
            session,
        )
    except ProjectAlreadyExists as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A project with this name already exists",
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    runs_count = session.scalar(
        select(func.count(TestRun.id)).where(TestRun.project_id == project.id)
    )
    return _project_response(project, runs_count or 0)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project(
    project_id: UUID,
    current_user: AuthenticatedUser,
    session: DatabaseSession,
) -> None:
    project = _get_owned_project_or_404(project_id, current_user, session)
    delete_project(project, session)


@router.post(
    "/projects/{project_id}/runs",
    response_model=TestRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_test_report(
    project: IngestionProject,
    session: DatabaseSession,
    report_file: Annotated[UploadFile, File(alias="file")],
) -> TestRunResponse:
    filename = (report_file.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not filename or len(filename) > 255 or any(ord(char) < 32 for char in filename):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid report filename is required",
        )

    chunks: list[bytes] = []
    size = 0
    while chunk := await report_file.read(64 * 1024):
        size += len(chunk)
        if size > MAX_REPORT_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Report files must not exceed {MAX_REPORT_BYTES // (1024 * 1024)} MB",
            )
        chunks.append(chunk)
    content = b"".join(chunks)

    try:
        parsed_report = parse_report(filename, content)
    except InvalidReport as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    run = ingest_report(
        project=project,
        filename=filename,
        content_type=report_file.content_type or "application/octet-stream",
        content=content,
        report=parsed_report,
        session=session,
    )
    return _run_response(run)


@router.get("/projects/{project_id}/runs", response_model=TestRunListResponse)
def list_project_runs(
    project_id: UUID,
    current_user: AuthenticatedUser,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TestRunListResponse:
    project = _get_owned_project_or_404(project_id, current_user, session)
    base_query = select(TestRun).where(TestRun.project_id == project.id)
    total = session.scalar(select(func.count(TestRun.id)).where(TestRun.project_id == project.id))
    runs = session.scalars(
        base_query.order_by(TestRun.created_at.desc(), TestRun.id).limit(limit).offset(offset)
    ).all()
    return TestRunListResponse(items=[_run_response(run) for run in runs], total=total or 0)


@router.get(
    "/projects/{project_id}/statistics",
    response_model=ProjectStatisticsResponse,
)
def project_statistics(
    project_id: UUID,
    current_user: AuthenticatedUser,
    session: DatabaseSession,
) -> ProjectStatisticsResponse:
    project = _get_owned_project_or_404(project_id, current_user, session)
    aggregates = session.execute(
        select(
            func.count(TestRun.id),
            func.coalesce(func.sum(TestRun.total_tests), 0),
            func.coalesce(func.sum(TestRun.passed_tests), 0),
            func.coalesce(func.sum(TestRun.failed_tests), 0),
            func.coalesce(func.sum(TestRun.skipped_tests), 0),
            func.coalesce(func.avg(TestRun.pass_rate), 0.0),
        ).where(TestRun.project_id == project.id)
    ).one()
    latest_run = session.scalar(
        select(TestRun)
        .where(TestRun.project_id == project.id)
        .order_by(TestRun.created_at.desc(), TestRun.id)
        .limit(1)
    )
    return ProjectStatisticsResponse(
        project_id=project.id,
        total_runs=aggregates[0],
        total_tests=aggregates[1],
        passed_tests=aggregates[2],
        failed_tests=aggregates[3],
        skipped_tests=aggregates[4],
        average_pass_rate=round(float(aggregates[5]), 2),
        latest_run_id=latest_run.id if latest_run else None,
        latest_run_status=latest_run.status if latest_run else None,
    )


@router.get(
    "/projects/{project_id}/flaky-tests",
    response_model=list[FlakyTestResponse],
)
def list_flaky_tests(
    project_id: UUID,
    current_user: AuthenticatedUser,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[FlakyTestResponse]:
    project = _get_owned_project_or_404(project_id, current_user, session)
    records = session.execute(
        select(TestCase.classname, TestCase.name, TestRun.id, TestCase.status)
        .join(TestSuite, TestSuite.id == TestCase.suite_id)
        .join(TestRun, TestRun.id == TestSuite.run_id)
        .where(
            TestRun.project_id == project.id,
            TestCase.status.in_(("passed", "failed")),
        )
    )
    outcomes: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for classname, name, run_id, case_status in records:
        outcomes[(classname, name)][run_id].add(case_status)

    flaky_tests = []
    for (classname, name), runs in outcomes.items():
        failed_runs = sum("failed" in run_statuses for run_statuses in runs.values())
        passed_runs = sum("passed" in run_statuses for run_statuses in runs.values())
        has_cross_run_flakiness = any(
            passed_run != failed_run
            for passed_run, passed_statuses in runs.items()
            if "passed" in passed_statuses
            for failed_run, failed_statuses in runs.items()
            if "failed" in failed_statuses
        )
        if failed_runs and passed_runs and has_cross_run_flakiness:
            total_runs = len(runs)
            flaky_tests.append(
                FlakyTestResponse(
                    classname=classname,
                    name=name,
                    total_runs=total_runs,
                    failed_runs=failed_runs,
                    failure_rate=round(failed_runs / total_runs * 100, 2),
                )
            )
    return sorted(
        flaky_tests,
        key=lambda item: (-item.failed_runs, item.classname, item.name),
    )[:limit]


@router.get("/runs/{run_id}", response_model=TestRunDetailsResponse)
def read_test_run(
    run_id: UUID,
    current_user: AuthenticatedUser,
    session: DatabaseSession,
) -> TestRunDetailsResponse:
    run = session.scalar(
        select(TestRun)
        .join(Project, Project.id == TestRun.project_id)
        .where(TestRun.id == str(run_id), Project.owner_id == current_user.id)
        .options(selectinload(TestRun.suites).selectinload(TestSuite.cases))
    )
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test run not found")
    return TestRunDetailsResponse(
        **_run_response(run).model_dump(),
        suites=run.suites,
    )

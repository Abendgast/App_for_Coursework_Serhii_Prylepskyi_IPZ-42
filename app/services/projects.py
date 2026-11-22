import hashlib
import secrets
from hmac import compare_digest

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Project, TestAttachment, TestCase, TestRun, TestSuite
from app.schemas.projects import ProjectCreate, ProjectUpdate
from app.services.reports import ParsedReport


class ProjectAlreadyExists(Exception):
    pass


class ProjectNotFound(Exception):
    pass


class ProjectAccessDenied(Exception):
    pass


def _project_api_key_hash(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def create_project(payload: ProjectCreate, owner_id: str, session: Session) -> tuple[Project, str]:
    project = Project(
        owner_id=owner_id,
        name=payload.name,
        description=payload.description or None,
        api_key_hash="",
    )
    api_key = f"ath_{secrets.token_urlsafe(32)}"
    project.api_key_hash = _project_api_key_hash(api_key)
    session.add(project)

    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if session.scalar(
            select(Project.id).where(
                Project.owner_id == owner_id,
                Project.name == payload.name,
            )
        ):
            raise ProjectAlreadyExists from error
        raise

    session.refresh(project)
    return project, api_key


def get_owned_project(project_id: str, owner_id: str, session: Session) -> Project:
    project = session.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    )
    if project is None:
        raise ProjectNotFound
    return project


def list_owned_projects(owner_id: str, session: Session) -> list[tuple[Project, int]]:
    statement = (
        select(Project, func.count(TestRun.id).label("runs_count"))
        .outerjoin(TestRun, TestRun.project_id == Project.id)
        .where(Project.owner_id == owner_id)
        .group_by(Project.id)
        .order_by(Project.created_at.desc(), Project.id)
    )
    return list(session.execute(statement).all())


def update_project(
    project: Project,
    payload: ProjectUpdate,
    session: Session,
) -> Project:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return project
    if "name" in changes and changes["name"] is None:
        raise ValueError("Project name cannot be null")
    if changes.get("description") == "":
        changes["description"] = None

    for key, value in changes.items():
        setattr(project, key, value)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        existing = session.scalar(
            select(Project.id).where(
                Project.owner_id == project.owner_id,
                Project.name == changes.get("name", project.name),
                Project.id != project.id,
            )
        )
        if existing is not None:
            raise ProjectAlreadyExists from error
        raise
    session.refresh(project)
    return project


def delete_project(project: Project, session: Session) -> None:
    session.delete(project)
    session.commit()


def get_project_for_ingestion(
    project_id: str,
    owner_id: str | None,
    api_key: str | None,
    session: Session,
) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise ProjectNotFound
    if api_key is not None:
        valid_key = compare_digest(project.api_key_hash, _project_api_key_hash(api_key))
        if not valid_key:
            raise ProjectAccessDenied
    elif owner_id is None or project.owner_id != owner_id:
        raise ProjectAccessDenied
    return project


def ingest_report(
    project: Project,
    filename: str,
    content_type: str,
    content: bytes,
    report: ParsedReport,
    session: Session,
) -> TestRun:
    counts = report.counts
    run = TestRun(
        project_id=project.id,
        source_filename=filename,
        report_format=report.report_format,
        build_number=report.build_number,
        branch=report.branch,
        status=report.status,
        total_tests=counts["total_tests"],
        passed_tests=counts["passed_tests"],
        failed_tests=counts["failed_tests"],
        skipped_tests=counts["skipped_tests"],
        duration_seconds=counts["duration_seconds"],
        pass_rate=counts["pass_rate"],
    )
    for parsed_suite in report.suites:
        suite = TestSuite(name=parsed_suite.name)
        suite.cases = [
            TestCase(
                classname=case.classname,
                name=case.name,
                status=case.status,
                duration_seconds=case.duration_seconds,
                error_message=case.error_message,
            )
            for case in parsed_suite.cases
        ]
        run.suites.append(suite)
    run.attachment = TestAttachment(
        filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        content=content,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run

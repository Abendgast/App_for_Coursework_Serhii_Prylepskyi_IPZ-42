import io
import uuid

from sqlalchemy import select

from app.models import TestAttachment as AttachmentRecord
from app.models import TestCase as CaseRecord
from app.models import TestRun as RunRecord
from app.models import TestSuite as SuiteRecord

JUNIT_REPORT = b"""<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="payments" tests="3" failures="1" skipped="1">
    <testcase classname="billing.InvoiceTests" name="test_create_invoice" time="0.25" />
    <testcase classname="billing.InvoiceTests" name="test_refund" time="0.50">
      <failure message="expected 200, got 500">AssertionError</failure>
    </testcase>
    <testcase classname="billing.InvoiceTests" name="test_legacy_flow" time="0.05">
      <skipped message="not configured" />
    </testcase>
  </testsuite>
</testsuites>
"""

JSON_REPORT = b"""{
  "build_number": 42,
  "branch": "feature/payments",
  "suites": [
    {
      "name": "checkout",
      "tests": [
        {"name": "test_checkout", "status": "passed", "duration_seconds": 0.1},
        {"name": "test_declined_card", "status": "failed", "duration_seconds": 0.2,
         "error_message": "Expected a decline response"}
      ]
    }
  ]
}
"""


def setup_project(client, email="reports@example.com"):
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "display_name": "Report Owner",
            "password": "a-very-long-test-password",
        },
    )
    assert registered.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "a-very-long-test-password"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    project_response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Report Project"},
    )
    assert project_response.status_code == 201
    return headers, project_response.json()


def upload(client, project_id, filename, content, headers):
    return client.post(
        f"/api/v1/projects/{project_id}/runs",
        headers=headers,
        files={"file": (filename, io.BytesIO(content), "application/octet-stream")},
    )


def test_junit_report_is_imported_with_results_and_original_attachment(client):
    headers, project = setup_project(client)
    response = upload(
        client,
        project["id"],
        "junit.xml",
        JUNIT_REPORT,
        {"X-Project-Key": project["api_key"]},
    )
    assert response.status_code == 201
    run = response.json()
    assert run["report_format"] == "junit_xml"
    assert run["status"] == "failed"
    assert run["total_tests"] == 3
    assert run["passed_tests"] == 1
    assert run["failed_tests"] == 1
    assert run["skipped_tests"] == 1
    assert run["duration_seconds"] == 0.8
    assert run["pass_rate"] == 50.0

    details = client.get(f"/api/v1/runs/{run['id']}", headers=headers)
    assert details.status_code == 200
    assert details.json()["suites"][0]["cases"][1]["error_message"] == ("expected 200, got 500")

    session = client.app.state.session_factory()
    try:
        attachment = session.scalar(
            select(AttachmentRecord).where(AttachmentRecord.run_id == run["id"])
        )
        assert attachment.filename == "junit.xml"
        assert attachment.content == JUNIT_REPORT
        assert attachment.size_bytes == len(JUNIT_REPORT)
    finally:
        session.close()


def test_json_report_is_imported_with_build_metadata(client):
    headers, project = setup_project(client)
    response = upload(
        client,
        project["id"],
        "pytest-results.json",
        JSON_REPORT,
        headers,
    )
    assert response.status_code == 201
    assert response.json()["report_format"] == "json"
    assert response.json()["build_number"] == 42
    assert response.json()["branch"] == "feature/payments"
    assert response.json()["pass_rate"] == 50.0


def test_report_upload_rejects_missing_authentication(client):
    _, project = setup_project(client)
    response = upload(client, project["id"], "tests.xml", JUNIT_REPORT, {})
    assert response.status_code == 401


def test_report_upload_rejects_wrong_project_key(client):
    _, project = setup_project(client)
    response = upload(
        client,
        project["id"],
        "tests.xml",
        JUNIT_REPORT,
        {"X-Project-Key": "ath_not-the-project-key"},
    )
    assert response.status_code == 401


def test_report_upload_rejects_invalid_files_and_preserves_run_history(client):
    headers, project = setup_project(client)
    invalid_reports = [
        ("report.txt", JUNIT_REPORT),
        ("broken.xml", b"<testsuites>"),
        ("empty.xml", b""),
        ("malformed.json", b'{"suites": []}'),
    ]
    for filename, content in invalid_reports:
        response = upload(
            client,
            project["id"],
            filename,
            content,
            {"X-Project-Key": project["api_key"]},
        )
        assert response.status_code == 422, (filename, response.text)

    response = client.get(f"/api/v1/projects/{project['id']}/runs", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_report_upload_rejects_xml_external_entities(client):
    headers, project = setup_project(client)
    unsafe_xml = b"""<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
    <testsuite name="unsafe"><testcase name="&xxe;" /></testsuite>"""
    response = upload(
        client,
        project["id"],
        "unsafe.xml",
        unsafe_xml,
        {"X-Project-Key": project["api_key"]},
    )
    assert response.status_code == 422


def test_project_statistics_run_history_and_flaky_test_detection(client):
    headers, project = setup_project(client)
    project_key = {"X-Project-Key": project["api_key"]}
    first = upload(
        client,
        project["id"],
        "first.xml",
        JUNIT_REPORT,
        project_key,
    )
    assert first.status_code == 201
    second_junit = JUNIT_REPORT.replace(
        b'<failure message="expected 200, got 500">AssertionError</failure>',
        b"",
    )
    second = upload(
        client,
        project["id"],
        "second.xml",
        second_junit,
        project_key,
    )
    assert second.status_code == 201

    stats = client.get(
        f"/api/v1/projects/{project['id']}/statistics",
        headers=headers,
    )
    assert stats.status_code == 200
    assert stats.json()["total_runs"] == 2
    assert stats.json()["total_tests"] == 6
    assert stats.json()["passed_tests"] == 3
    assert stats.json()["failed_tests"] == 1
    assert stats.json()["skipped_tests"] == 2
    assert stats.json()["average_pass_rate"] == 75.0

    history = client.get(f"/api/v1/projects/{project['id']}/runs", headers=headers)
    assert history.status_code == 200
    assert history.json()["total"] == 2
    assert len(history.json()["items"]) == 2

    flaky = client.get(
        f"/api/v1/projects/{project['id']}/flaky-tests",
        headers=headers,
    )
    assert flaky.status_code == 200
    assert flaky.json() == [
        {
            "classname": "billing.InvoiceTests",
            "name": "test_refund",
            "total_runs": 2,
            "failed_runs": 1,
            "failure_rate": 50.0,
        }
    ]


def test_invalid_project_id_is_rejected(client):
    headers, _ = setup_project(client)
    response = client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


def test_project_deletion_cascades_through_imported_results(client):
    headers, project = setup_project(client)
    run = upload(
        client,
        project["id"],
        "junit.xml",
        JUNIT_REPORT,
        {"X-Project-Key": project["api_key"]},
    )
    assert run.status_code == 201
    run_id = run.json()["id"]

    deleted = client.delete(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
    )
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/runs/{run_id}", headers=headers).status_code == 404

    session = client.app.state.session_factory()
    try:
        assert session.scalar(select(RunRecord).where(RunRecord.id == run_id)) is None
        assert session.scalar(select(SuiteRecord).where(SuiteRecord.run_id == run_id)) is None
        assert (
            session.scalar(
                select(CaseRecord)
                .join(SuiteRecord, SuiteRecord.id == CaseRecord.suite_id)
                .where(SuiteRecord.run_id == run_id)
            )
            is None
        )
        assert (
            session.scalar(select(AttachmentRecord).where(AttachmentRecord.run_id == run_id))
            is None
        )
    finally:
        session.close()

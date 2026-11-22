# Lab 11 test execution record

The functional cases below map to executable API tests. Expected and actual
results are taken from the assertions in those tests; statuses are the latest
executed results. Unit coverage and database integration cases follow the
functional matrix.

## Functional test cases

| ID | Type | Test | Expected result | Actual result | Status |
|---|---|---|---|---|---|
| TC-001 | Positive | `test_register_login_and_read_current_user` | Register, log in, and read the authenticated profile | User created, bearer token issued, `/me` returned the matching profile | PASS |
| TC-002 | Positive | `test_project_crud_and_one_time_project_key` | Create/list/read/PATCH/delete an owned project | CRUD succeeded; key omitted from later project reads | PASS |
| TC-003 | Positive | `test_junit_report_is_imported_with_results_and_original_attachment` | Import JUnit results and retain original report | Three cases persisted with correct counts, failure details, and attachment bytes | PASS |
| TC-004 | Positive | `test_json_report_is_imported_with_build_metadata` | Upload a JSON report as project owner | Report imported with build, branch, and pass-rate metadata | PASS |
| TC-005 | Positive | `test_project_statistics_run_history_and_flaky_test_detection` | Aggregate run history and detect cross-run test changes | Totals, pass rate, history, and one flaky test matched expectations | PASS |
| TC-006 | Positive | `test_registration_normalizes_email` | Normalize email before storage | Mixed-case address stored in lowercase | PASS |
| TC-007 | Negative | `test_wrong_password_returns_generic_unauthorized` | Reject an incorrect password without leaking account details | Generic `401` returned | PASS |
| TC-008 | Negative | `test_duplicate_registration_returns_conflict` | Reject a duplicate email | `409` returned with the documented message | PASS |
| TC-009 | Negative | `test_protected_endpoint_requires_bearer_token` | Reject access to a protected endpoint without credentials | `401` returned with a Bearer challenge | PASS |
| TC-010 | Negative | `test_project_validation_and_authentication` | Reject unauthenticated project creation and overlong project names | `401` and `422` returned respectively | PASS |
| TC-011 | Negative | `test_report_upload_rejects_invalid_files_and_preserves_run_history` | Reject unsupported, malformed, empty, and invalid reports | Each upload returned `422`; run history remained empty | PASS |
| TC-012 | Negative | `test_report_upload_rejects_xml_external_entities` | Reject unsafe XML entity declarations | Upload returned `422`; no unsafe report was imported | PASS |
| TC-013 | Positive | `test_project_can_be_replaced_with_put` | Replace all project fields using PUT | Name and description were replaced; response returned `200` | PASS |
| TC-014 | Negative | `test_project_put_requires_all_replace_fields` | Reject an incomplete PUT replacement | Missing description returned `422` | PASS |

The 14 cases include 7 positive and 7 negative scenarios. Additional negative
coverage includes invalid email/password, malformed tokens, duplicate project
names, wrong project keys, and cross-owner project access.

## Unit tests

`tests/test_reports_unit.py` contains 10 unit tests for report result
calculation, status selection, JSON/XML parser strategies, extension dispatch,
and invalid input. All 10 pass.

## Database integration tests

| ID | Test | Expected and actual result | Status |
|---|---|---|---|
| IT-001 | `test_junit_report_is_imported_with_results_and_original_attachment` | API import persisted the run, suites, cases, and exact original attachment in SQLite; read-back matched the upload | PASS |
| IT-002 | `test_project_statistics_run_history_and_flaky_test_detection` | Multiple report uploads were visible to separate aggregate/history endpoints; totals and flaky result matched expected values | PASS |
| IT-003 | `test_project_deletion_cascades_through_imported_results` | Deleting a project removed its run, suites, cases, and original attachment | PASS |

## Defects

No defects remain from the executed test cases. Invalid input is rejected with
the expected HTTP errors, and the security cases confirm authentication and
project ownership boundaries.

## Execution

Run the cases from the project root on Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Latest full-suite result during this stage: **35 passed, 3 warnings**. The
warnings are upstream deprecations from Starlette/httpx and FastAPI's
`HTTP_422_UNPROCESSABLE_ENTITY` constant. The report-parser unit subset is
independently runnable with:

```powershell
.\.venv\Scripts\python.exe -m pytest -v tests\test_reports_unit.py
```

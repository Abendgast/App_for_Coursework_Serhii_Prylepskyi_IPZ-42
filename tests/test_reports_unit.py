import pytest

from app.services.reports import InvalidReport, ParsedCase, ParsedReport, ParsedSuite, parse_report


def test_report_counts_exclude_skipped_cases_from_pass_rate():
    report = ParsedReport(
        report_format="json",
        build_number=None,
        branch="main",
        suites=(
            ParsedSuite(
                name="unit",
                cases=(
                    ParsedCase("tests.Sample", "passes", "passed", 0.1, None),
                    ParsedCase("tests.Sample", "fails", "failed", 0.2, "assertion"),
                    ParsedCase("tests.Sample", "skips", "skipped", 0.3, None),
                ),
            ),
        ),
    )

    assert report.counts == {
        "total_tests": 3,
        "passed_tests": 1,
        "failed_tests": 1,
        "skipped_tests": 1,
        "duration_seconds": pytest.approx(0.6),
        "pass_rate": 50.0,
    }


def test_report_status_is_failed_when_any_test_fails():
    report = parse_report(
        "report.json",
        b'{"suites":[{"name":"unit","tests":[{"name":"fails","status":"failed"}]}]}',
    )

    assert report.status == "failed"


def test_all_skipped_report_has_zero_pass_rate_and_skipped_status():
    report = parse_report(
        "report.json",
        b'{"suites":[{"name":"unit","tests":[{"name":"skip","status":"skipped"}]}]}',
    )

    assert report.status == "skipped"
    assert report.counts["pass_rate"] == 0.0


def test_json_strategy_parses_metadata_and_uses_suite_as_classname_fallback():
    report = parse_report(
        "results.json",
        b"""{
            "build_number": 17,
            "branch": "release",
            "suites": [{"name": "payments", "tests": [
                {"name": "test_refund", "status": "passed"}
            ]}]
        }""",
    )

    assert report.report_format == "json"
    assert (report.build_number, report.branch) == (17, "release")
    assert report.suites[0].cases[0].classname == "payments"


def test_junit_strategy_parses_pass_fail_skip_and_failure_message():
    report = parse_report(
        "results.xml",
        b"""<testsuite name="payments">
            <testcase classname="PaymentTests" name="test_ok" time="0.1"/>
            <testcase classname="PaymentTests" name="test_error" time="0.2">
                <error message="unexpected response"/>
            </testcase>
            <testcase classname="PaymentTests" name="test_skip">
                <skipped/>
            </testcase>
        </testsuite>""",
    )

    assert [case.status for case in report.suites[0].cases] == [
        "passed",
        "failed",
        "skipped",
    ]
    assert report.suites[0].cases[1].error_message == "unexpected response"
    assert report.counts["duration_seconds"] == pytest.approx(0.3)


def test_parser_dispatch_accepts_windows_path_and_case_insensitive_extension():
    report = parse_report(
        r"reports\junit.XML",
        b'<testsuite name="unit"><testcase name="passes"/></testsuite>',
    )

    assert report.report_format == "junit_xml"


def test_empty_report_is_rejected():
    with pytest.raises(InvalidReport, match="empty"):
        parse_report("empty.json", b"")


def test_unsupported_report_format_is_rejected():
    with pytest.raises(InvalidReport, match="Only .xml and .json"):
        parse_report("report.csv", b"name,status\ncase,passed")


def test_malformed_json_report_is_rejected():
    with pytest.raises(InvalidReport, match="Invalid JSON test report"):
        parse_report("broken.json", b'{"suites": [}')


def test_invalid_xml_test_duration_is_rejected():
    with pytest.raises(InvalidReport, match="Invalid test duration"):
        parse_report(
            "bad-duration.xml",
            b'<testsuite name="unit"><testcase name="test" time="fast"/></testsuite>',
        )

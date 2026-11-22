from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Protocol

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from pydantic import ValidationError

from app.schemas.reports import JsonTestReport

MAX_REPORT_BYTES = 10 * 1024 * 1024
MAX_TEST_CASES = 10_000


class InvalidReport(Exception):
    pass


@dataclass(frozen=True)
class ParsedCase:
    classname: str
    name: str
    status: str
    duration_seconds: float
    error_message: str | None


@dataclass(frozen=True)
class ParsedSuite:
    name: str
    cases: tuple[ParsedCase, ...]


@dataclass(frozen=True)
class ParsedReport:
    report_format: str
    build_number: int | None
    branch: str
    suites: tuple[ParsedSuite, ...]

    @property
    def counts(self) -> dict[str, int | float]:
        cases = [case for suite in self.suites for case in suite.cases]
        passed = sum(case.status == "passed" for case in cases)
        failed = sum(case.status == "failed" for case in cases)
        skipped = sum(case.status == "skipped" for case in cases)
        completed = passed + failed
        return {
            "total_tests": len(cases),
            "passed_tests": passed,
            "failed_tests": failed,
            "skipped_tests": skipped,
            "duration_seconds": sum(case.duration_seconds for case in cases),
            "pass_rate": round(passed / completed * 100, 2) if completed else 0.0,
        }

    @property
    def status(self) -> str:
        counts = self.counts
        if counts["failed_tests"]:
            return "failed"
        if counts["passed_tests"]:
            return "passed"
        return "skipped"


class ReportParser(Protocol):
    def parse(self, content: bytes) -> ParsedReport: ...


class JUnitXmlReportParser:
    def parse(self, content: bytes) -> ParsedReport:
        return _parse_xml(content)


class JsonReportParser:
    def parse(self, content: bytes) -> ParsedReport:
        return _parse_json(content)


def _read_duration(value: str | None, *, location: str) -> float:
    if value is None:
        return 0.0
    try:
        duration = float(value)
    except ValueError as error:
        raise InvalidReport(f"Invalid test duration in {location}") from error
    if not isfinite(duration) or duration < 0 or duration > 604800:
        raise InvalidReport(f"Test duration is outside the allowed range in {location}")
    return duration


def _parse_xml(content: bytes) -> ParsedReport:
    try:
        root = ElementTree.fromstring(content)
    except (DefusedXmlException, ElementTree.ParseError, ValueError) as error:
        raise InvalidReport("The XML report is malformed or unsafe") from error

    if root.tag == "testsuite":
        top_suites = [root]
    elif root.tag == "testsuites":
        top_suites = [child for child in root if child.tag == "testsuite"]
    else:
        raise InvalidReport("Expected a JUnit <testsuite> or <testsuites> root element")

    parsed_suites: list[ParsedSuite] = []
    test_count = 0

    def visit_suite(element, ancestors: tuple[str, ...]) -> None:
        nonlocal test_count
        suite_name = element.attrib.get("name", "").strip()
        if not suite_name:
            raise InvalidReport("Each JUnit testsuite must have a non-empty name")
        full_name = ".".join((*ancestors, suite_name))
        cases: list[ParsedCase] = []

        for testcase in element:
            if testcase.tag == "testcase":
                name = testcase.attrib.get("name", "").strip()
                if not name or len(name) > 255:
                    raise InvalidReport(
                        "Each JUnit testcase must have a name of at most 255 characters"
                    )
                classname = testcase.attrib.get("classname", "").strip()
                if len(classname) > 255:
                    raise InvalidReport("JUnit testcase classname must not exceed 255 characters")
                failures = [child for child in testcase if child.tag in {"failure", "error"}]
                skipped = next((child for child in testcase if child.tag == "skipped"), None)
                status = "failed" if failures else "skipped" if skipped is not None else "passed"
                error_message = None
                if failures:
                    failure = failures[0]
                    error_message = (
                        failure.attrib.get("message") or (failure.text or "").strip() or None
                    )
                    if error_message is not None:
                        error_message = error_message[:10_000]
                cases.append(
                    ParsedCase(
                        classname=classname,
                        name=name,
                        status=status,
                        duration_seconds=_read_duration(
                            testcase.attrib.get("time"), location=f"testcase {name}"
                        ),
                        error_message=error_message,
                    )
                )
                test_count += 1
                if test_count > MAX_TEST_CASES:
                    raise InvalidReport(f"Reports may contain at most {MAX_TEST_CASES} test cases")
            elif testcase.tag == "testsuite":
                visit_suite(testcase, (*ancestors, suite_name))

        parsed_suites.append(ParsedSuite(name=full_name, cases=tuple(cases)))

    for suite in top_suites:
        visit_suite(suite, ())

    if not parsed_suites or not any(suite.cases for suite in parsed_suites):
        raise InvalidReport("The JUnit report must contain at least one testcase")

    return ParsedReport(
        report_format="junit_xml",
        build_number=None,
        branch="main",
        suites=tuple(parsed_suites),
    )


def _parse_json(content: bytes) -> ParsedReport:
    try:
        document = JsonTestReport.model_validate_json(content)
    except ValidationError as error:
        messages = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()[:5]
        )
        raise InvalidReport(f"Invalid JSON test report: {messages}") from error
    except ValueError as error:
        raise InvalidReport("The JSON report is malformed or is not valid UTF-8") from error

    test_count = sum(len(suite.tests) for suite in document.suites)
    if test_count == 0:
        raise InvalidReport("The JSON report must contain at least one test")
    if test_count > MAX_TEST_CASES:
        raise InvalidReport(f"Reports may contain at most {MAX_TEST_CASES} test cases")

    suites = tuple(
        ParsedSuite(
            name=suite.name,
            cases=tuple(
                ParsedCase(
                    classname=test.classname or suite.name,
                    name=test.name,
                    status=test.status,
                    duration_seconds=test.duration_seconds,
                    error_message=test.error_message,
                )
                for test in suite.tests
            ),
        )
        for suite in document.suites
    )
    return ParsedReport(
        report_format="json",
        build_number=document.build_number,
        branch=document.branch,
        suites=suites,
    )


def parse_report(filename: str, content: bytes) -> ParsedReport:
    if not content:
        raise InvalidReport("The report file is empty")
    if len(content) > MAX_REPORT_BYTES:
        raise InvalidReport(f"Report files must not exceed {MAX_REPORT_BYTES // (1024 * 1024)} MB")

    extension = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    parser = _REPORT_PARSERS.get(extension)
    if parser is None:
        raise InvalidReport("Only .xml and .json test reports are supported")
    return parser.parse(content)


_REPORT_PARSERS: Mapping[str, ReportParser] = MappingProxyType(
    {
        ".xml": JUnitXmlReportParser(),
        ".json": JsonReportParser(),
    }
)

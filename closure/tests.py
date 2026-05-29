import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from closure.models import (
    Check,
    CheckEvidence,
    ClosureSnapshot,
    Project,
    RegressionRun,
    Requirement,
    RequirementCategory,
    RequirementCheckMapping,
    RequirementEvidence,
    RequirementTestMapping,
    Test,
    TestRun,
)
from closure.services.closure import compute_closure_snapshot
from closure.services.parser import SpecLinkParseError, parse_log_text


class SpecLinkTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="AXI Project", slug="axi", description="")
        self.category = RequirementCategory.objects.create(project=self.project, name="Write Address", code="AXI.AW")
        self.req = Requirement.objects.create(
            project=self.project,
            category=self.category,
            requirement_id="AXI-AW-001",
            title="AWADDR stable while stalled",
            description="AWADDR must remain stable while AWVALID is high and AWREADY is low.",
            priority=Requirement.PRIORITY_HIGH,
            status=Requirement.STATUS_ACTIVE,
        )
        self.req2 = Requirement.objects.create(
            project=self.project,
            category=self.category,
            requirement_id="AXI-AW-002",
            title="AWVALID stable",
            description="AWVALID must remain stable.",
            status=Requirement.STATUS_ACTIVE,
        )
        self.test = Test.objects.create(project=self.project, test_id="axi_basic_write_test")
        self.test2 = Test.objects.create(project=self.project, test_id="axi_backpressure_test")
        self.check = Check.objects.create(
            project=self.project,
            test=self.test,
            check_id="AWADDR_STABLE_CHECK",
            name="AWADDR stable",
        )
        self.check2 = Check.objects.create(
            project=self.project,
            test=self.test,
            check_id="AWVALID_STABLE_CHECK",
            name="AWVALID stable",
        )

    def map_req(self, req=None, test=None, check=None):
        req = req or self.req
        test = test or self.test
        check = check or self.check
        RequirementTestMapping.objects.create(requirement=req, test=test)
        RequirementCheckMapping.objects.create(requirement=req, verification_check=check)

    def make_run_with_pass(self):
        self.map_req()
        run = RegressionRun.objects.create(project=self.project, run_id="nightly_001")
        test_run = TestRun.objects.create(regression_run=run, test=self.test, test_name=self.test.test_id, status=TestRun.STATUS_PASSED)
        CheckEvidence.objects.create(
            regression_run=run,
            test_run=test_run,
            requirement=self.req,
            verification_check=self.check,
            check_id=self.check.check_id,
            observed=True,
            result=CheckEvidence.RESULT_PASS,
            hit_count=5,
        )
        return run

    def test_requirement_can_map_to_multiple_tests(self):
        RequirementTestMapping.objects.create(requirement=self.req, test=self.test)
        RequirementTestMapping.objects.create(requirement=self.req, test=self.test2)
        self.assertEqual(self.req.tests.count(), 2)

    def test_test_can_map_to_multiple_requirements(self):
        RequirementTestMapping.objects.create(requirement=self.req, test=self.test)
        RequirementTestMapping.objects.create(requirement=self.req2, test=self.test)
        self.assertEqual(self.test.requirements.count(), 2)

    def test_test_can_have_multiple_checks(self):
        self.assertEqual(self.test.checks.count(), 2)

    def test_requirement_closes_only_when_all_required_tests_and_checks_pass(self):
        run = self.make_run_with_pass()
        snapshot = compute_closure_snapshot(run)
        evidence = RequirementEvidence.objects.get(regression_run=run, requirement=self.req)
        self.assertEqual(evidence.status, RequirementEvidence.STATUS_CLOSED)
        self.assertEqual(snapshot.closed_requirements, 1)

    def test_failed_check_makes_requirement_failed(self):
        self.map_req()
        run = RegressionRun.objects.create(project=self.project, run_id="nightly_002")
        test_run = TestRun.objects.create(regression_run=run, test=self.test, test_name=self.test.test_id, status=TestRun.STATUS_PASSED)
        CheckEvidence.objects.create(
            regression_run=run,
            test_run=test_run,
            requirement=self.req,
            verification_check=self.check,
            check_id=self.check.check_id,
            observed=True,
            result=CheckEvidence.RESULT_FAIL,
        )
        compute_closure_snapshot(run)
        self.assertEqual(RequirementEvidence.objects.get(regression_run=run, requirement=self.req).status, RequirementEvidence.STATUS_FAILED)

    def test_missing_expected_check_is_not_closed(self):
        self.map_req()
        run = RegressionRun.objects.create(project=self.project, run_id="nightly_003")
        TestRun.objects.create(regression_run=run, test=self.test, test_name=self.test.test_id, status=TestRun.STATUS_PASSED)
        compute_closure_snapshot(run)
        evidence = RequirementEvidence.objects.get(regression_run=run, requirement=self.req)
        self.assertEqual(evidence.status, RequirementEvidence.STATUS_PARTIAL)

    def test_parser_extracts_valid_summary(self):
        parsed = parse_log_text(valid_log())
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].payload["test"], "axi_basic_write_test")

    def test_parser_rejects_malformed_summary(self):
        with self.assertRaises(SpecLinkParseError):
            parse_log_text("=== SPECLINK_SUMMARY_BEGIN ===\n{\"schema_version\":\n=== SPECLINK_SUMMARY_END ===")

    def test_evidence_upload_creates_run_test_check_evidence(self):
        self.map_req()
        report = {
            "schema_version": "1.0",
            "parser_version": "test",
            "project": "axi",
            "run_id": "nightly_upload",
            "tests": [json.loads(valid_log().split("=== SPECLINK_SUMMARY_BEGIN ===")[1].split("=== SPECLINK_SUMMARY_END ===")[0])],
        }
        uploaded = SimpleUploadedFile("evidence.json", json.dumps(report).encode("utf-8"), content_type="application/json")
        response = self.client.post(reverse("evidence_upload"), {"project": self.project.pk, "evidence_file": uploaded})
        self.assertEqual(response.status_code, 302)
        run = RegressionRun.objects.get(run_id="nightly_upload")
        self.assertEqual(run.test_runs.count(), 1)
        self.assertEqual(run.check_evidence.count(), 1)

    def test_closure_snapshot_counts_are_correct(self):
        run = self.make_run_with_pass()
        snapshot = compute_closure_snapshot(run)
        self.assertIsInstance(snapshot, ClosureSnapshot)
        self.assertEqual(snapshot.total_requirements, 2)
        self.assertEqual(snapshot.closed_requirements, 1)
        self.assertEqual(snapshot.open_requirements, 1)


def valid_log():
    return """
noise
=== SPECLINK_SUMMARY_BEGIN ===
{
  "schema_version": "1.0",
  "project": "axi",
  "package_version": "abc123",
  "test": "axi_basic_write_test",
  "status": "passed",
  "expected_requirements_count": 1,
  "covered_requirements_count": 1,
  "expected_checks_count": 1,
  "passed_checks_count": 1,
  "failed_checks_count": 0,
  "missing_checks_count": 0,
  "requirements": [
    {
      "id": "AXI-AW-001",
      "title": "AWADDR stable while stalled",
      "expected": true,
      "status": "closed",
      "checks": [
        {
          "id": "AWADDR_STABLE_CHECK",
          "expected": true,
          "observed": true,
          "result": "pass",
          "hit_count": 5,
          "fail_count": 0,
          "messages": []
        }
      ]
    }
  ]
}
=== SPECLINK_SUMMARY_END ===
"""

# Create your tests here.

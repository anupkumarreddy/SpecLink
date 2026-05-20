from decimal import Decimal

from django.db import transaction

from closure.models import (
    CheckEvidence,
    ClosureSnapshot,
    RegressionRun,
    Requirement,
    RequirementEvidence,
    TestRun,
)


def compute_requirement_evidence(regression_run: RegressionRun):
    """Apply the MVP closure policy for every active requirement in a run."""
    results = []
    requirements = (
        Requirement.objects.filter(project=regression_run.project, status=Requirement.STATUS_ACTIVE)
        .select_related("category")
        .prefetch_related("test_mappings__test", "check_mappings__verification_check__test")
    )

    with transaction.atomic():
        RequirementEvidence.objects.filter(regression_run=regression_run).delete()
        for requirement in requirements:
            required_test_mappings = [
                mapping for mapping in requirement.test_mappings.all() if mapping.required_for_closure
            ]
            required_check_mappings = [
                mapping for mapping in requirement.check_mappings.all() if mapping.required_for_closure
            ]

            expected_tests_count = len(required_test_mappings)
            passed_tests_count = 0
            failed_tests_count = 0
            missing_tests_count = 0
            meaningful_evidence = False

            for mapping in required_test_mappings:
                test_runs = TestRun.objects.filter(regression_run=regression_run, test=mapping.test)
                if not test_runs.exists():
                    missing_tests_count += 1
                    continue
                meaningful_evidence = True
                if test_runs.filter(status=TestRun.STATUS_FAILED).exists():
                    failed_tests_count += 1
                elif test_runs.filter(status=TestRun.STATUS_PASSED).exists():
                    passed_tests_count += 1
                else:
                    missing_tests_count += 1

            expected_checks_count = len(required_check_mappings)
            passed_checks_count = 0
            failed_checks_count = 0
            missing_checks_count = 0

            for mapping in required_check_mappings:
                evidence = CheckEvidence.objects.filter(
                    regression_run=regression_run,
                    requirement=requirement,
                    check_id=mapping.verification_check.check_id,
                )
                if evidence.filter(result=CheckEvidence.RESULT_FAIL).exists():
                    meaningful_evidence = True
                    failed_checks_count += 1
                elif evidence.filter(result=CheckEvidence.RESULT_PASS, observed=True).exists():
                    meaningful_evidence = True
                    passed_checks_count += 1
                else:
                    missing_checks_count += 1

            if failed_tests_count or failed_checks_count:
                status = RequirementEvidence.STATUS_FAILED
            elif (
                expected_tests_count
                and expected_checks_count
                and missing_tests_count == 0
                and missing_checks_count == 0
                and passed_tests_count == expected_tests_count
                and passed_checks_count == expected_checks_count
            ):
                status = RequirementEvidence.STATUS_CLOSED
            elif meaningful_evidence or passed_tests_count or passed_checks_count:
                status = RequirementEvidence.STATUS_PARTIAL
            else:
                status = RequirementEvidence.STATUS_OPEN

            results.append(
                RequirementEvidence.objects.create(
                    regression_run=regression_run,
                    requirement=requirement,
                    expected=True,
                    status=status,
                    expected_checks_count=expected_checks_count,
                    passed_checks_count=passed_checks_count,
                    failed_checks_count=failed_checks_count,
                    missing_checks_count=missing_checks_count,
                    expected_tests_count=expected_tests_count,
                    passed_tests_count=passed_tests_count,
                    failed_tests_count=failed_tests_count,
                    missing_tests_count=missing_tests_count,
                    raw_data={
                        "required_tests": [m.test.test_id for m in required_test_mappings],
                        "required_checks": [m.verification_check.check_id for m in required_check_mappings],
                    },
                )
            )
    return results


def compute_closure_snapshot(regression_run: RegressionRun):
    with transaction.atomic():
        evidence = list(compute_requirement_evidence(regression_run))
        total = len(evidence)
        closed = sum(1 for item in evidence if item.status == RequirementEvidence.STATUS_CLOSED)
        partial = sum(1 for item in evidence if item.status == RequirementEvidence.STATUS_PARTIAL)
        failed = sum(1 for item in evidence if item.status == RequirementEvidence.STATUS_FAILED)
        open_count = total - closed - partial - failed
        closure_percent = Decimal("0.00") if total == 0 else Decimal(closed * 100 / total).quantize(Decimal("0.01"))
        snapshot, _ = ClosureSnapshot.objects.update_or_create(
            regression_run=regression_run,
            defaults={
                "project": regression_run.project,
                "total_requirements": total,
                "closed_requirements": closed,
                "partial_requirements": partial,
                "failed_requirements": failed,
                "open_requirements": open_count,
                "closure_percent": closure_percent,
                "summary": {
                    "closed": closed,
                    "partial": partial,
                    "failed": failed,
                    "open": open_count,
                },
            },
        )
    return snapshot

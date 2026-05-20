from django.db import transaction

from closure.models import (
    Check,
    CheckEvidence,
    EvidenceReport,
    Project,
    RegressionRun,
    Requirement,
    Test,
    TestRun,
)
from closure.services.closure import compute_closure_snapshot


class EvidenceIngestError(ValueError):
    pass


def validate_evidence_report(report: dict):
    required = {"schema_version", "project", "run_id", "tests"}
    missing = sorted(required - report.keys())
    if missing:
        raise EvidenceIngestError(f"Evidence report missing fields: {', '.join(missing)}")
    if not isinstance(report["tests"], list):
        raise EvidenceIngestError("Evidence report field 'tests' must be a list.")


@transaction.atomic
def ingest_evidence_report(project: Project, report: dict):
    validate_evidence_report(report)
    run, _ = RegressionRun.objects.update_or_create(
        project=project,
        run_id=report["run_id"],
        defaults={
            "name": report.get("name", report["run_id"]),
            "branch": report.get("branch", ""),
            "commit_sha": report.get("commit_sha", ""),
            "tool": report.get("tool", ""),
            "status": RegressionRun.STATUS_PROCESSING,
            "metadata": report.get("metadata", {}),
        },
    )
    run.test_runs.all().delete()

    for summary in report["tests"]:
        test = Test.objects.filter(project=project, test_id=summary["test"]).first()
        test_run = TestRun.objects.create(
            regression_run=run,
            test=test,
            test_name=summary["test"],
            status=summary.get("status", TestRun.STATUS_UNKNOWN),
            seed=str(summary.get("seed", "")),
            log_path=summary.get("log_path", ""),
            raw_summary=summary,
        )
        for req_summary in summary.get("requirements", []):
            requirement = Requirement.objects.filter(project=project, requirement_id=req_summary["id"]).first()
            if requirement is None:
                continue
            for check_summary in req_summary.get("checks", []):
                check = None
                if test is not None:
                    check = Check.objects.filter(project=project, test=test, check_id=check_summary["id"]).first()
                CheckEvidence.objects.create(
                    regression_run=run,
                    test_run=test_run,
                    requirement=requirement,
                    verification_check=check,
                    check_id=check_summary["id"],
                    expected=bool(check_summary.get("expected", True)),
                    observed=bool(check_summary.get("observed", False)),
                    result=check_summary.get("result", CheckEvidence.RESULT_UNKNOWN),
                    hit_count=int(check_summary.get("hit_count", 0) or 0),
                    fail_count=int(check_summary.get("fail_count", 0) or 0),
                    messages=check_summary.get("messages", []),
                    raw_data=check_summary,
                )

    EvidenceReport.objects.create(
        project=project,
        regression_run=run,
        raw_json=report,
        schema_version=report.get("schema_version", "1.0"),
        parser_version=report.get("parser_version", ""),
        validation_status=EvidenceReport.STATUS_VALID,
        validation_errors=[],
    )
    run.status = RegressionRun.STATUS_PROCESSED
    run.save(update_fields=["status"])
    snapshot = compute_closure_snapshot(run)
    return run, snapshot

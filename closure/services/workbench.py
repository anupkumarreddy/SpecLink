"""Helpers that power the workbench tree + detail panel.

Two modes are supported:

* Definition mode — pure structural data, no run context.
* Evidence mode — given a regression run, returns per-node status maps so the
  tree can color-code requirements / tests / checks.
"""
from collections import defaultdict

from closure.models import (
    Check,
    CheckEvidence,
    RegressionRun,
    Requirement,
    RequirementCategory,
    RequirementEvidence,
    Test,
    TestRun,
)


# Status vocab used by the templates; matches partials/badge.html values.
REQUIREMENT_STATUSES = ("closed", "partial", "failed", "open", "missing")
TEST_STATUSES = ("passed", "failed", "skipped", "unknown", "missing")
CHECK_STATUSES = ("pass", "fail", "missing", "unknown")


def get_overlay(run: RegressionRun | None) -> "EvidenceOverlay":
    """Return an overlay object (empty if run is None)."""
    return EvidenceOverlay(run)


class EvidenceOverlay:
    """Per-run status lookups for tree decoration.

    Each ``*_status`` method returns ``""`` when the overlay is inactive (no
    run) so callers can blindly add a CSS class without branching.
    """

    def __init__(self, run: RegressionRun | None):
        self.run = run
        self._requirement_status: dict[int, str] = {}
        self._test_status: dict[int, str] = {}
        self._check_status: dict[tuple[int, int], str] = {}
        self._requirement_counts: dict[int, dict] = {}
        if run is not None:
            self._load()

    @property
    def active(self) -> bool:
        return self.run is not None

    def _load(self) -> None:
        req_qs = RequirementEvidence.objects.filter(regression_run=self.run)
        for item in req_qs:
            self._requirement_status[item.requirement_id] = item.status
            self._requirement_counts[item.requirement_id] = {
                "passed_tests": item.passed_tests_count,
                "failed_tests": item.failed_tests_count,
                "missing_tests": item.missing_tests_count,
                "expected_tests": item.expected_tests_count,
                "passed_checks": item.passed_checks_count,
                "failed_checks": item.failed_checks_count,
                "missing_checks": item.missing_checks_count,
                "expected_checks": item.expected_checks_count,
            }

        test_run_status: dict[int, list[str]] = defaultdict(list)
        for tr in TestRun.objects.filter(regression_run=self.run).exclude(test__isnull=True):
            test_run_status[tr.test_id].append(tr.status)
        for test_id, statuses in test_run_status.items():
            if TestRun.STATUS_FAILED in statuses:
                self._test_status[test_id] = "failed"
            elif TestRun.STATUS_PASSED in statuses:
                self._test_status[test_id] = "passed"
            elif TestRun.STATUS_SKIPPED in statuses:
                self._test_status[test_id] = "skipped"
            else:
                self._test_status[test_id] = "unknown"

        for ev in CheckEvidence.objects.filter(regression_run=self.run).exclude(verification_check__isnull=True):
            key = (ev.requirement_id, ev.verification_check_id)
            prior = self._check_status.get(key)
            new = ev.result if ev.result else "unknown"
            # fail wins over pass wins over missing/unknown
            if prior == "fail" or new == "fail":
                self._check_status[key] = "fail"
            elif prior == "pass" or new == "pass":
                self._check_status[key] = "pass"
            else:
                self._check_status[key] = new

    def requirement_status(self, requirement_id: int) -> str:
        if not self.active:
            return ""
        return self._requirement_status.get(requirement_id, "missing")

    def requirement_counts(self, requirement_id: int) -> dict:
        return self._requirement_counts.get(requirement_id, {})

    def test_status(self, test_id: int) -> str:
        if not self.active:
            return ""
        return self._test_status.get(test_id, "missing")

    def check_status_for_requirement(self, requirement_id: int, check_id: int) -> str:
        if not self.active:
            return ""
        return self._check_status.get((requirement_id, check_id), "missing")

    def check_aggregate_status(self, check_id: int) -> str:
        """Status for a check across all requirements it's mapped to in this run."""
        if not self.active:
            return ""
        seen = [v for (_, cid), v in self._check_status.items() if cid == check_id]
        if not seen:
            return "missing"
        if "fail" in seen:
            return "fail"
        if "pass" in seen:
            return "pass"
        return seen[0]


# ---------------------------------------------------------------------------
# Tree builders. Each returns a list of dicts shaped for tree_node.html.
# A node dict has: kind, id, label, sublabel, status, count, has_children,
#                  meta (for caller-specific extras).
# ---------------------------------------------------------------------------


def project_root_children(project, view: str, overlay: EvidenceOverlay):
    if view == "test":
        tests = (
            Test.objects.filter(project=project)
            .order_by("test_id")
        )
        return [_test_node(t, overlay) for t in tests]

    # Default: requirement-centric. Show top-level categories.
    top_categories = (
        RequirementCategory.objects.filter(project=project, parent__isnull=True)
        .order_by("display_order", "code")
    )
    return [_category_node(c, overlay) for c in top_categories]


def category_children(category: RequirementCategory, overlay: EvidenceOverlay):
    nodes = []
    for child in category.children.order_by("display_order", "code"):
        nodes.append(_category_node(child, overlay))
    for req in category.requirements.order_by("requirement_id"):
        nodes.append(_requirement_node(req, overlay))
    return nodes


def requirement_children(requirement: Requirement, overlay: EvidenceOverlay):
    nodes = []
    for mapping in requirement.test_mappings.select_related("test").order_by("test__test_id"):
        nodes.append(_test_node(mapping.test, overlay, parent_requirement=requirement, role=mapping.role))
    # directly mapped checks (may be checks whose parent test isn't mapped)
    mapped_test_ids = {m.test_id for m in requirement.test_mappings.all()}
    for cm in requirement.check_mappings.select_related("verification_check", "verification_check__test").order_by(
        "verification_check__check_id"
    ):
        check = cm.verification_check
        if check.test_id in mapped_test_ids:
            continue  # already shown under the test
        nodes.append(_check_node(check, overlay, parent_requirement=requirement))
    return nodes


def test_children(test: Test, overlay: EvidenceOverlay, parent_requirement: Requirement | None = None):
    return [
        _check_node(c, overlay, parent_requirement=parent_requirement)
        for c in test.checks.order_by("check_id")
    ]


def _category_node(category: RequirementCategory, overlay: EvidenceOverlay) -> dict:
    req_count = category.requirements.count()
    sub_count = category.children.count()
    return {
        "kind": "category",
        "id": category.pk,
        "label": f"{category.code} — {category.name}",
        "sublabel": "category",
        "status": "",
        "count": req_count + sub_count,
        "has_children": (req_count + sub_count) > 0,
    }


def _requirement_node(requirement: Requirement, overlay: EvidenceOverlay) -> dict:
    test_count = requirement.test_mappings.count()
    check_count = requirement.check_mappings.count()
    return {
        "kind": "requirement",
        "id": requirement.pk,
        "label": requirement.requirement_id,
        "sublabel": requirement.title,
        "status": overlay.requirement_status(requirement.pk),
        "count": test_count + check_count,
        "has_children": (test_count + check_count) > 0,
        "meta": {"priority": requirement.priority},
    }


def _test_node(test: Test, overlay: EvidenceOverlay, parent_requirement: Requirement | None = None, role: str = "") -> dict:
    check_count = test.checks.count()
    node = {
        "kind": "test",
        "id": test.pk,
        "label": test.test_id,
        "sublabel": test.get_test_type_display(),
        "status": overlay.test_status(test.pk),
        "count": check_count,
        "has_children": check_count > 0,
        "meta": {"role": role},
    }
    if parent_requirement is not None:
        node["parent_requirement_id"] = parent_requirement.pk
    return node


def _check_node(check: Check, overlay: EvidenceOverlay, parent_requirement: Requirement | None = None) -> dict:
    if parent_requirement is not None:
        status = overlay.check_status_for_requirement(parent_requirement.pk, check.pk)
    else:
        status = overlay.check_aggregate_status(check.pk)
    return {
        "kind": "check",
        "id": check.pk,
        "label": check.check_id,
        "sublabel": check.get_check_type_display(),
        "status": status,
        "count": 0,
        "has_children": False,
        "meta": {"test_id": check.test.test_id if check.test_id else ""},
    }

from django.core.management.base import BaseCommand

from closure.models import (
    Check,
    GeneratedPackage,
    Project,
    Requirement,
    RequirementCategory,
    RequirementCheckMapping,
    RequirementTestMapping,
    Test,
)
from closure.services.generator import create_generated_package
from closure.services.ingest import ingest_evidence_report


class Command(BaseCommand):
    help = "Seed a small AXI demo project with requirements, tests, checks, mappings, and evidence."

    def handle(self, *args, **options):
        project, _ = Project.objects.update_or_create(
            slug="axi",
            defaults={
                "name": "AXI Demo Project",
                "description": "Seed data for exercising SpecLink requirement closure workflows.",
            },
        )

        categories = self._create_categories(project)
        tests = self._create_tests(project)
        checks = self._create_checks(project, tests)
        requirements = self._create_requirements(project, categories)
        self._create_mappings(requirements, tests, checks)

        report = self._demo_evidence_report()
        run, snapshot = ingest_evidence_report(project, report)

        GeneratedPackage.objects.filter(project=project, notes="Seeded demo package").delete()
        package = create_generated_package(project, notes="Seeded demo package")

        self.stdout.write(self.style.SUCCESS("Seeded SpecLink demo data."))
        self.stdout.write(f"Project: {project.name} ({project.slug})")
        self.stdout.write(f"Regression run: {run.run_id}")
        self.stdout.write(
            "Closure: "
            f"{snapshot.closed_requirements} closed, "
            f"{snapshot.partial_requirements} partial, "
            f"{snapshot.failed_requirements} failed, "
            f"{snapshot.open_requirements} open "
            f"({snapshot.closure_percent}%)"
        )
        self.stdout.write(f"Generated package: {package.version}")

    def _create_categories(self, project):
        axi, _ = RequirementCategory.objects.update_or_create(
            project=project,
            code="AXI",
            defaults={"name": "AXI Protocol", "description": "Top-level AXI protocol requirements.", "display_order": 1},
        )
        aw, _ = RequirementCategory.objects.update_or_create(
            project=project,
            code="AXI.AW",
            defaults={"parent": axi, "name": "Write Address", "display_order": 10},
        )
        w, _ = RequirementCategory.objects.update_or_create(
            project=project,
            code="AXI.W",
            defaults={"parent": axi, "name": "Write Data", "display_order": 20},
        )
        b, _ = RequirementCategory.objects.update_or_create(
            project=project,
            code="AXI.B",
            defaults={"parent": axi, "name": "Write Response", "display_order": 30},
        )
        return {"aw": aw, "w": w, "b": b}

    def _create_tests(self, project):
        data = [
            ("axi_basic_write_test", "Directed smoke test for a single AXI write.", Test.TYPE_DIRECTED),
            ("axi_backpressure_test", "Constrained random write with AW/W channel stalls.", Test.TYPE_CONSTRAINED_RANDOM),
            ("axi_error_response_test", "Injects an address decode error and checks BRESP.", Test.TYPE_DIRECTED),
            ("axi_outstanding_write_test", "Exercises multiple outstanding write transactions.", Test.TYPE_CONSTRAINED_RANDOM),
        ]
        tests = {}
        for test_id, description, test_type in data:
            tests[test_id], _ = Test.objects.update_or_create(
                project=project,
                test_id=test_id,
                defaults={
                    "description": description,
                    "test_type": test_type,
                    "file_path": f"dv/tests/{test_id}.sv",
                    "enabled": True,
                    "owner": "dv-team",
                },
            )
        return tests

    def _create_checks(self, project, tests):
        data = [
            ("axi_basic_write_test", "AWADDR_STABLE_CHECK", "AWADDR stable while stalled", Check.TYPE_SCOREBOARD),
            ("axi_basic_write_test", "AWVALID_STABLE_CHECK", "AWVALID stable during wait states", Check.TYPE_ASSERTION),
            ("axi_backpressure_test", "WDATA_STABLE_CHECK", "WDATA stable while stalled", Check.TYPE_SCOREBOARD),
            ("axi_backpressure_test", "WSTRB_VALID_CHECK", "WSTRB legal for write transfer", Check.TYPE_MONITOR),
            ("axi_error_response_test", "BRESP_ERROR_CHECK", "BRESP reports decode error", Check.TYPE_COMPARISON),
            ("axi_outstanding_write_test", "OUTSTANDING_DEPTH_CHECK", "Outstanding counter never exceeds configured limit", Check.TYPE_MONITOR),
        ]
        checks = {}
        for test_id, check_id, name, check_type in data:
            check, _ = Check.objects.update_or_create(
                project=project,
                test=tests[test_id],
                check_id=check_id,
                defaults={
                    "name": name,
                    "description": name,
                    "check_type": check_type,
                    "source_path": f"dv/checks/{check_id.lower()}.sv",
                    "required_by_default": True,
                },
            )
            checks[check_id] = check
        return checks

    def _create_requirements(self, project, categories):
        data = [
            (
                "AXI-AW-001",
                categories["aw"],
                "AWADDR must remain stable while stalled",
                "AWADDR must remain stable while AWVALID is high and AWREADY is low.",
                Requirement.PRIORITY_CRITICAL,
                "Alice",
            ),
            (
                "AXI-AW-002",
                categories["aw"],
                "AWVALID must remain asserted until accepted",
                "AWVALID remains asserted until a transfer occurs.",
                Requirement.PRIORITY_HIGH,
                "Bob",
            ),
            (
                "AXI-W-001",
                categories["w"],
                "WDATA and WSTRB must remain stable while stalled",
                "Write data channel payload must not change while WVALID is high and WREADY is low.",
                Requirement.PRIORITY_HIGH,
                "Chandra",
            ),
            (
                "AXI-B-001",
                categories["b"],
                "Decode errors must return SLVERR",
                "Writes to unmapped regions must return an error response.",
                Requirement.PRIORITY_MEDIUM,
                "Deepa",
            ),
            (
                "AXI-AW-003",
                categories["aw"],
                "Outstanding write depth must be bounded",
                "The master must not exceed the configured outstanding write transaction limit.",
                Requirement.PRIORITY_MEDIUM,
                "Alice",
            ),
        ]
        requirements = {}
        for requirement_id, category, title, description, priority, owner in data:
            req, _ = Requirement.objects.update_or_create(
                project=project,
                requirement_id=requirement_id,
                defaults={
                    "category": category,
                    "title": title,
                    "description": description,
                    "spec_section": f"AXI4 {requirement_id[-3:]}",
                    "priority": priority,
                    "status": Requirement.STATUS_ACTIVE,
                    "owner": owner,
                    "rationale": "Protocol compliance and closure tracking.",
                },
            )
            requirements[requirement_id] = req
        return requirements

    def _create_mappings(self, requirements, tests, checks):
        mapping_data = [
            ("AXI-AW-001", "axi_basic_write_test", "AWADDR_STABLE_CHECK"),
            ("AXI-AW-002", "axi_basic_write_test", "AWVALID_STABLE_CHECK"),
            ("AXI-W-001", "axi_backpressure_test", "WDATA_STABLE_CHECK"),
            ("AXI-W-001", "axi_backpressure_test", "WSTRB_VALID_CHECK"),
            ("AXI-B-001", "axi_error_response_test", "BRESP_ERROR_CHECK"),
            ("AXI-AW-003", "axi_outstanding_write_test", "OUTSTANDING_DEPTH_CHECK"),
        ]
        for requirement_id, test_id, check_id in mapping_data:
            RequirementTestMapping.objects.update_or_create(
                requirement=requirements[requirement_id],
                test=tests[test_id],
                defaults={"required_for_closure": True, "role": RequirementTestMapping.ROLE_PROVES},
            )
            RequirementCheckMapping.objects.update_or_create(
                requirement=requirements[requirement_id],
                verification_check=checks[check_id],
                defaults={
                    "required_for_closure": True,
                    "expected_count": 1,
                    "closure_role": RequirementCheckMapping.ROLE_PROVES,
                },
            )

    def _demo_evidence_report(self):
        return {
            "schema_version": "1.0",
            "parser_version": "seed",
            "project": "axi",
            "run_id": "nightly_001",
            "branch": "main",
            "commit_sha": "deadbeef1234",
            "tool": "simulator-demo",
            "metadata": {"seeded": True},
            "tests": [
                {
                    "schema_version": "1.0",
                    "project": "axi",
                    "package_version": "seed",
                    "test": "axi_basic_write_test",
                    "status": "passed",
                    "requirements": [
                        {
                            "id": "AXI-AW-001",
                            "expected": True,
                            "status": "closed",
                            "checks": [
                                {
                                    "id": "AWADDR_STABLE_CHECK",
                                    "expected": True,
                                    "observed": True,
                                    "result": "pass",
                                    "hit_count": 5,
                                    "fail_count": 0,
                                    "messages": [],
                                }
                            ],
                        },
                        {
                            "id": "AXI-AW-002",
                            "expected": True,
                            "status": "partial",
                            "checks": [
                                {
                                    "id": "AWVALID_STABLE_CHECK",
                                    "expected": True,
                                    "observed": False,
                                    "result": "missing",
                                    "hit_count": 0,
                                    "fail_count": 0,
                                    "messages": [],
                                }
                            ],
                        },
                    ],
                },
                {
                    "schema_version": "1.0",
                    "project": "axi",
                    "package_version": "seed",
                    "test": "axi_backpressure_test",
                    "status": "passed",
                    "requirements": [
                        {
                            "id": "AXI-W-001",
                            "expected": True,
                            "status": "closed",
                            "checks": [
                                {
                                    "id": "WDATA_STABLE_CHECK",
                                    "expected": True,
                                    "observed": True,
                                    "result": "pass",
                                    "hit_count": 11,
                                    "fail_count": 0,
                                    "messages": [],
                                },
                                {
                                    "id": "WSTRB_VALID_CHECK",
                                    "expected": True,
                                    "observed": True,
                                    "result": "pass",
                                    "hit_count": 11,
                                    "fail_count": 0,
                                    "messages": [],
                                },
                            ],
                        }
                    ],
                },
                {
                    "schema_version": "1.0",
                    "project": "axi",
                    "package_version": "seed",
                    "test": "axi_error_response_test",
                    "status": "failed",
                    "requirements": [
                        {
                            "id": "AXI-B-001",
                            "expected": True,
                            "status": "failed",
                            "checks": [
                                {
                                    "id": "BRESP_ERROR_CHECK",
                                    "expected": True,
                                    "observed": True,
                                    "result": "fail",
                                    "hit_count": 1,
                                    "fail_count": 1,
                                    "messages": ["Expected SLVERR, observed OKAY"],
                                }
                            ],
                        }
                    ],
                },
            ],
        }

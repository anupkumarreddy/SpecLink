import hashlib
import json
import re

from django.template.loader import render_to_string

from closure.models import GeneratedPackage, Project, RequirementCheckMapping


def sv_identifier(value: str) -> str:
    ident = re.sub(r"[^a-zA-Z0-9_]", "_", value)
    if not ident or ident[0].isdigit():
        ident = f"_{ident}"
    return ident


def package_context(project: Project) -> dict:
    requirements = list(project.requirements.select_related("category").prefetch_related("check_mappings__verification_check__test"))
    tests = list(project.tests.prefetch_related("checks"))
    requirement_rows = [
        {
            "id": req.requirement_id,
            "sv_id": sv_identifier(req.requirement_id),
            "title": req.title,
            "category": req.category.code,
        }
        for req in requirements
    ]
    test_expectations = []
    for test in tests:
        mappings = RequirementCheckMapping.objects.filter(
            requirement__project=project,
            requirement__test_mappings__test=test,
            required_for_closure=True,
        ).select_related("requirement", "verification_check")
        expected = [
            {"requirement_id": mapping.requirement.requirement_id, "check_id": mapping.verification_check.check_id}
            for mapping in mappings
        ]
        test_expectations.append({"test_id": test.test_id, "checks": expected})
    return {
        "project": project,
        "requirements": requirement_rows,
        "test_expectations": test_expectations,
    }


def render_sv_package(project: Project) -> tuple[str, str]:
    context = package_context(project)
    artifact = render_to_string("generator/speclink_pkg.sv", context)
    checksum = hashlib.sha256(artifact.encode("utf-8")).hexdigest()
    return artifact, checksum


def create_generated_package(project: Project, generated_by=None, notes: str = "") -> GeneratedPackage:
    artifact, checksum = render_sv_package(project)
    version = checksum[:12]
    return GeneratedPackage.objects.create(
        project=project,
        version=version,
        generated_by=generated_by if getattr(generated_by, "is_authenticated", False) else None,
        artifact=artifact,
        checksum=checksum,
        notes=notes,
    )

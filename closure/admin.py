from django.contrib import admin

from closure.models import (
    Check,
    CheckEvidence,
    ClosureSnapshot,
    EvidenceReport,
    GeneratedPackage,
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


class RequirementTestMappingInline(admin.TabularInline):
    model = RequirementTestMapping
    extra = 1
    autocomplete_fields = ["test"]


class RequirementCheckMappingInline(admin.TabularInline):
    model = RequirementCheckMapping
    extra = 1
    autocomplete_fields = ["verification_check"]


class CheckInline(admin.TabularInline):
    model = Check
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at", "updated_at"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(RequirementCategory)
class RequirementCategoryAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "project", "parent", "display_order"]
    list_filter = ["project"]
    search_fields = ["name", "code", "description"]


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = ["requirement_id", "title", "project", "category", "priority", "status", "owner"]
    list_filter = ["project", "category", "priority", "status"]
    search_fields = ["requirement_id", "title", "description", "owner", "spec_section"]
    inlines = [RequirementTestMappingInline, RequirementCheckMappingInline]


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ["test_id", "project", "test_type", "enabled", "owner"]
    list_filter = ["project", "test_type", "enabled"]
    search_fields = ["test_id", "description", "owner", "file_path"]
    inlines = [CheckInline]


@admin.register(Check)
class CheckAdmin(admin.ModelAdmin):
    list_display = ["check_id", "name", "project", "test", "check_type", "required_by_default"]
    list_filter = ["project", "check_type", "required_by_default"]
    search_fields = ["check_id", "name", "description", "source_path"]


@admin.register(RequirementTestMapping)
class RequirementTestMappingAdmin(admin.ModelAdmin):
    list_display = ["requirement", "test", "role", "required_for_closure"]
    list_filter = ["role", "required_for_closure", "requirement__project"]
    search_fields = ["requirement__requirement_id", "test__test_id", "rationale"]
    autocomplete_fields = ["requirement", "test"]


@admin.register(RequirementCheckMapping)
class RequirementCheckMappingAdmin(admin.ModelAdmin):
    list_display = ["requirement", "verification_check", "closure_role", "required_for_closure", "expected_count"]
    list_filter = ["closure_role", "required_for_closure", "requirement__project"]
    search_fields = ["requirement__requirement_id", "verification_check__check_id", "rationale"]
    autocomplete_fields = ["requirement", "verification_check"]


@admin.register(GeneratedPackage)
class GeneratedPackageAdmin(admin.ModelAdmin):
    list_display = ["project", "version", "generated_at", "generated_by", "checksum"]
    list_filter = ["project", "generated_at"]
    search_fields = ["version", "checksum", "notes"]


@admin.register(RegressionRun)
class RegressionRunAdmin(admin.ModelAdmin):
    list_display = ["run_id", "project", "status", "branch", "commit_sha", "uploaded_at"]
    list_filter = ["project", "status", "tool", "uploaded_at"]
    search_fields = ["run_id", "name", "branch", "commit_sha"]


@admin.register(EvidenceReport)
class EvidenceReportAdmin(admin.ModelAdmin):
    list_display = ["project", "regression_run", "schema_version", "parser_version", "validation_status", "uploaded_at"]
    list_filter = ["project", "validation_status", "schema_version"]


@admin.register(TestRun)
class TestRunAdmin(admin.ModelAdmin):
    list_display = ["regression_run", "test_name", "test", "status", "seed"]
    list_filter = ["regression_run__project", "status"]
    search_fields = ["test_name", "seed", "log_path"]


@admin.register(CheckEvidence)
class CheckEvidenceAdmin(admin.ModelAdmin):
    list_display = ["regression_run", "requirement", "check_id", "result", "observed", "hit_count", "fail_count"]
    list_filter = ["regression_run__project", "result", "observed", "expected"]
    search_fields = ["requirement__requirement_id", "check_id"]


@admin.register(RequirementEvidence)
class RequirementEvidenceAdmin(admin.ModelAdmin):
    list_display = ["regression_run", "requirement", "status", "passed_checks_count", "missing_checks_count"]
    list_filter = ["regression_run__project", "status"]
    search_fields = ["requirement__requirement_id"]


@admin.register(ClosureSnapshot)
class ClosureSnapshotAdmin(admin.ModelAdmin):
    list_display = [
        "project",
        "regression_run",
        "closure_percent",
        "closed_requirements",
        "partial_requirements",
        "failed_requirements",
        "open_requirements",
        "created_at",
    ]
    list_filter = ["project", "created_at"]

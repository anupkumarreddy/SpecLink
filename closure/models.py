from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Project(TimeStampedModel):
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("project_detail", args=[self.slug])


class RequirementCategory(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="categories")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="children", null=True, blank=True)
    name = models.CharField(max_length=180)
    code = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["project", "display_order", "code"]
        unique_together = [("project", "code")]
        verbose_name_plural = "requirement categories"

    def __str__(self):
        return f"{self.code} - {self.name}"


class Requirement(TimeStampedModel):
    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"
    PRIORITY_CRITICAL = "critical"
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Low"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_HIGH, "High"),
        (PRIORITY_CRITICAL, "Critical"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_DEPRECATED = "deprecated"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_DEPRECATED, "Deprecated"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="requirements")
    category = models.ForeignKey(RequirementCategory, on_delete=models.PROTECT, related_name="requirements")
    requirement_id = models.CharField(max_length=120)
    title = models.CharField(max_length=240)
    description = models.TextField()
    spec_section = models.CharField(max_length=160, blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    owner = models.CharField(max_length=120, blank=True)
    rationale = models.TextField(blank=True)
    tests = models.ManyToManyField("Test", through="RequirementTestMapping", related_name="requirements")
    checks = models.ManyToManyField(
        "Check",
        through="RequirementCheckMapping",
        through_fields=("requirement", "verification_check"),
        related_name="requirements",
    )

    class Meta:
        ordering = ["requirement_id"]
        unique_together = [("project", "requirement_id")]

    def __str__(self):
        return self.requirement_id

    def get_absolute_url(self):
        return reverse("requirement_detail", args=[self.pk])


class Test(TimeStampedModel):
    TYPE_DIRECTED = "directed"
    TYPE_CONSTRAINED_RANDOM = "constrained_random"
    TYPE_FORMAL = "formal"
    TYPE_MANUAL = "manual"
    TYPE_CHOICES = [
        (TYPE_DIRECTED, "Directed"),
        (TYPE_CONSTRAINED_RANDOM, "Constrained random"),
        (TYPE_FORMAL, "Formal"),
        (TYPE_MANUAL, "Manual"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tests")
    test_id = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    test_type = models.CharField(max_length=40, choices=TYPE_CHOICES, default=TYPE_CONSTRAINED_RANDOM)
    file_path = models.CharField(max_length=300, blank=True)
    enabled = models.BooleanField(default=True)
    owner = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["test_id"]
        unique_together = [("project", "test_id")]

    def __str__(self):
        return self.test_id

    def get_absolute_url(self):
        return reverse("test_detail", args=[self.pk])


class Check(TimeStampedModel):
    TYPE_SCOREBOARD = "scoreboard"
    TYPE_ASSERTION = "assertion"
    TYPE_COVERAGE = "coverage"
    TYPE_MANUAL = "manual"
    TYPE_MONITOR = "monitor"
    TYPE_COMPARISON = "comparison"
    TYPE_CHOICES = [
        (TYPE_SCOREBOARD, "Scoreboard"),
        (TYPE_ASSERTION, "Assertion"),
        (TYPE_COVERAGE, "Coverage"),
        (TYPE_MANUAL, "Manual"),
        (TYPE_MONITOR, "Monitor"),
        (TYPE_COMPARISON, "Comparison"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="checks")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="checks")
    check_id = models.CharField(max_length=160)
    name = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    check_type = models.CharField(max_length=40, choices=TYPE_CHOICES, default=TYPE_SCOREBOARD)
    source_path = models.CharField(max_length=300, blank=True)
    source_line = models.PositiveIntegerField(null=True, blank=True)
    required_by_default = models.BooleanField(default=True)

    class Meta:
        ordering = ["test__test_id", "check_id"]
        unique_together = [("project", "test", "check_id")]

    def __str__(self):
        return self.check_id

    def get_absolute_url(self):
        return reverse("check_detail", args=[self.pk])


class RequirementTestMapping(TimeStampedModel):
    ROLE_PROVES = "proves"
    ROLE_STIMULATES = "stimulates"
    ROLE_OBSERVES = "observes"
    ROLE_GUARDS = "guards"
    ROLE_PARTIAL = "partial"
    ROLE_CHOICES = [
        (ROLE_PROVES, "Proves"),
        (ROLE_STIMULATES, "Stimulates"),
        (ROLE_OBSERVES, "Observes"),
        (ROLE_GUARDS, "Guards"),
        (ROLE_PARTIAL, "Partial"),
    ]

    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE, related_name="test_mappings")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="requirement_mappings")
    required_for_closure = models.BooleanField(default=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default=ROLE_PROVES)
    rationale = models.TextField(blank=True)

    class Meta:
        unique_together = [("requirement", "test")]

    def __str__(self):
        return f"{self.requirement} -> {self.test}"


class RequirementCheckMapping(TimeStampedModel):
    ROLE_PROVES = "proves"
    ROLE_OBSERVES = "observes"
    ROLE_COVERS = "covers"
    ROLE_GUARDS = "guards"
    ROLE_CHOICES = [
        (ROLE_PROVES, "Proves"),
        (ROLE_OBSERVES, "Observes"),
        (ROLE_COVERS, "Covers"),
        (ROLE_GUARDS, "Guards"),
    ]

    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE, related_name="check_mappings")
    verification_check = models.ForeignKey(Check, on_delete=models.CASCADE, related_name="requirement_mappings")
    required_for_closure = models.BooleanField(default=True)
    expected_count = models.PositiveIntegerField(null=True, blank=True, default=1)
    closure_role = models.CharField(max_length=30, choices=ROLE_CHOICES, default=ROLE_PROVES)
    rationale = models.TextField(blank=True)

    class Meta:
        unique_together = [("requirement", "verification_check")]

    def __str__(self):
        return f"{self.requirement} -> {self.verification_check}"


class GeneratedPackage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="generated_packages")
    version = models.CharField(max_length=80)
    generated_at = models.DateTimeField(default=timezone.now)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    artifact = models.TextField()
    checksum = models.CharField(max_length=128)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.project.slug} {self.version}"


class RegressionRun(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_PROCESSED = "processed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_PROCESSED, "Processed"),
        (STATUS_FAILED, "Failed"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="regression_runs")
    run_id = models.CharField(max_length=160)
    name = models.CharField(max_length=220, blank=True)
    branch = models.CharField(max_length=160, blank=True)
    commit_sha = models.CharField(max_length=80, blank=True)
    tool = models.CharField(max_length=120, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        unique_together = [("project", "run_id")]

    def __str__(self):
        return self.run_id

    def get_absolute_url(self):
        return reverse("run_detail", args=[self.pk])


class EvidenceReport(models.Model):
    STATUS_VALID = "valid"
    STATUS_INVALID = "invalid"
    STATUS_CHOICES = [
        (STATUS_VALID, "Valid"),
        (STATUS_INVALID, "Invalid"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="evidence_reports")
    regression_run = models.ForeignKey(RegressionRun, on_delete=models.CASCADE, related_name="evidence_reports")
    raw_json = models.JSONField()
    schema_version = models.CharField(max_length=20)
    parser_version = models.CharField(max_length=40, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)
    validation_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    validation_errors = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]


class TestRun(models.Model):
    STATUS_PASSED = "passed"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_UNKNOWN = "unknown"
    STATUS_CHOICES = [
        (STATUS_PASSED, "Passed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_SKIPPED, "Skipped"),
        (STATUS_UNKNOWN, "Unknown"),
    ]

    regression_run = models.ForeignKey(RegressionRun, on_delete=models.CASCADE, related_name="test_runs")
    test = models.ForeignKey(Test, on_delete=models.SET_NULL, null=True, blank=True, related_name="runs")
    test_name = models.CharField(max_length=160)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UNKNOWN)
    seed = models.CharField(max_length=80, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    log_path = models.CharField(max_length=400, blank=True)
    raw_summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["test_name"]

    def __str__(self):
        return f"{self.regression_run.run_id}:{self.test_name}"


class CheckEvidence(models.Model):
    RESULT_PASS = "pass"
    RESULT_FAIL = "fail"
    RESULT_MISSING = "missing"
    RESULT_UNKNOWN = "unknown"
    RESULT_CHOICES = [
        (RESULT_PASS, "Pass"),
        (RESULT_FAIL, "Fail"),
        (RESULT_MISSING, "Missing"),
        (RESULT_UNKNOWN, "Unknown"),
    ]

    regression_run = models.ForeignKey(RegressionRun, on_delete=models.CASCADE, related_name="check_evidence")
    test_run = models.ForeignKey(TestRun, on_delete=models.CASCADE, related_name="check_evidence")
    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE, related_name="check_evidence")
    verification_check = models.ForeignKey(Check, on_delete=models.SET_NULL, null=True, blank=True, related_name="evidence")
    check_id = models.CharField(max_length=160)
    expected = models.BooleanField(default=True)
    observed = models.BooleanField(default=False)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default=RESULT_UNKNOWN)
    hit_count = models.PositiveIntegerField(default=0)
    fail_count = models.PositiveIntegerField(default=0)
    messages = models.JSONField(default=list, blank=True)
    first_seen_at = models.DateTimeField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)


class RequirementEvidence(models.Model):
    STATUS_CLOSED = "closed"
    STATUS_PARTIAL = "partial"
    STATUS_OPEN = "open"
    STATUS_FAILED = "failed"
    STATUS_MISSING = "missing"
    STATUS_CHOICES = [
        (STATUS_CLOSED, "Closed"),
        (STATUS_PARTIAL, "Partial"),
        (STATUS_OPEN, "Open"),
        (STATUS_FAILED, "Failed"),
        (STATUS_MISSING, "Missing"),
    ]

    regression_run = models.ForeignKey(RegressionRun, on_delete=models.CASCADE, related_name="requirement_evidence")
    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE, related_name="evidence")
    expected = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    expected_checks_count = models.PositiveIntegerField(default=0)
    passed_checks_count = models.PositiveIntegerField(default=0)
    failed_checks_count = models.PositiveIntegerField(default=0)
    missing_checks_count = models.PositiveIntegerField(default=0)
    expected_tests_count = models.PositiveIntegerField(default=0)
    passed_tests_count = models.PositiveIntegerField(default=0)
    failed_tests_count = models.PositiveIntegerField(default=0)
    missing_tests_count = models.PositiveIntegerField(default=0)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("regression_run", "requirement")]
        ordering = ["requirement__requirement_id"]


class ClosureSnapshot(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="closure_snapshots")
    regression_run = models.OneToOneField(RegressionRun, on_delete=models.CASCADE, related_name="closure_snapshot")
    total_requirements = models.PositiveIntegerField(default=0)
    closed_requirements = models.PositiveIntegerField(default=0)
    partial_requirements = models.PositiveIntegerField(default=0)
    failed_requirements = models.PositiveIntegerField(default=0)
    open_requirements = models.PositiveIntegerField(default=0)
    closure_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(default=timezone.now)
    summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.project.slug} {self.regression_run.run_id} {self.closure_percent}%"

# Create your models here.

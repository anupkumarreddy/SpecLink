import csv

from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from closure.forms import (
    CheckForm,
    EvidenceUploadForm,
    ProjectForm,
    RequirementCheckMappingForm,
    RequirementForm,
    RequirementTestMappingForm,
    TestForm,
)
from closure.models import (
    Check,
    CheckEvidence,
    ClosureSnapshot,
    GeneratedPackage,
    Project,
    RegressionRun,
    Requirement,
    RequirementCategory,
    RequirementCheckMapping,
    RequirementEvidence,
    RequirementTestMapping,
    Test,
)
from closure.services.generator import create_generated_package
from closure.services.ingest import EvidenceIngestError, ingest_evidence_report


def _latest_project():
    return Project.objects.first()


def dashboard(request):
    project = _latest_project()
    latest_snapshot = None
    latest_run = None
    evidence = RequirementEvidence.objects.none()
    if project:
        latest_run = project.regression_runs.order_by("-uploaded_at").first()
        latest_snapshot = getattr(latest_run, "closure_snapshot", None) if latest_run else None
        evidence = RequirementEvidence.objects.filter(regression_run=latest_run).select_related("requirement") if latest_run else evidence
    context = {
        "project": project,
        "latest_run": latest_run,
        "snapshot": latest_snapshot,
        "projects_count": Project.objects.count(),
        "requirements_count": Requirement.objects.count(),
        "tests_count": Test.objects.count(),
        "checks_count": Check.objects.count(),
        "recent_runs": RegressionRun.objects.select_related("project").order_by("-uploaded_at")[:8],
        "failing_requirements": evidence.filter(status=RequirementEvidence.STATUS_FAILED)[:8],
        "partial_requirements": evidence.filter(status=RequirementEvidence.STATUS_PARTIAL)[:8],
        "missing_checks": CheckEvidence.objects.filter(result=CheckEvidence.RESULT_MISSING).select_related("requirement", "test_run")[:10],
        "unmapped_requirements": Requirement.objects.annotate(mapping_count=Count("test_mappings")).filter(mapping_count=0)[:10],
    }
    return render(request, "closure/dashboard.html", context)


def project_list(request):
    return render(request, "closure/project_list.html", {"projects": Project.objects.all()})


def project_create(request):
    form = ProjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        project = form.save()
        messages.success(request, "Project created.")
        return redirect(project)
    return render(request, "closure/form.html", {"form": form, "title": "Create Project"})


def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug)
    return render(
        request,
        "closure/project_detail.html",
        {
            "project": project,
            "latest_snapshot": project.closure_snapshots.first(),
            "requirements": project.requirements.select_related("category")[:20],
            "runs": project.regression_runs.all()[:10],
        },
    )


def category_tree(request):
    categories = RequirementCategory.objects.select_related("project", "parent").annotate(requirement_count=Count("requirements"))
    return render(request, "closure/category_tree.html", {"categories": categories})


def requirement_list(request):
    requirements = Requirement.objects.select_related("project", "category")
    query = request.GET.get("q", "")
    if query:
        requirements = requirements.filter(Q(requirement_id__icontains=query) | Q(title__icontains=query) | Q(owner__icontains=query))
    if request.GET.get("priority"):
        requirements = requirements.filter(priority=request.GET["priority"])
    if request.GET.get("status"):
        requirements = requirements.filter(status=request.GET["status"])
    return render(request, "closure/requirement_list.html", {"requirements": requirements, "query": query})


def requirement_create(request):
    form = RequirementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        requirement = form.save()
        messages.success(request, "Requirement created.")
        return redirect(requirement)
    return render(request, "closure/form.html", {"form": form, "title": "Create Requirement"})


def requirement_detail(request, pk):
    requirement = get_object_or_404(Requirement.objects.select_related("project", "category"), pk=pk)
    return render(
        request,
        "closure/requirement_detail.html",
        {
            "requirement": requirement,
            "test_mappings": requirement.test_mappings.select_related("test"),
            "check_mappings": requirement.check_mappings.select_related("verification_check", "verification_check__test"),
            "evidence": requirement.evidence.select_related("regression_run")[:20],
        },
    )


def test_list(request):
    tests = Test.objects.select_related("project").annotate(check_count=Count("checks"), requirement_count=Count("requirement_mappings"))
    return render(request, "closure/test_list.html", {"tests": tests})


def test_create(request):
    form = TestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        test = form.save()
        messages.success(request, "Test created.")
        return redirect(test)
    return render(request, "closure/form.html", {"form": form, "title": "Create Test"})


def test_detail(request, pk):
    test = get_object_or_404(Test.objects.select_related("project"), pk=pk)
    return render(
        request,
        "closure/test_detail.html",
        {
            "test": test,
            "checks": test.checks.all(),
            "requirement_mappings": test.requirement_mappings.select_related("requirement"),
            "runs": test.runs.select_related("regression_run")[:20],
        },
    )


def check_list(request):
    checks = Check.objects.select_related("project", "test").annotate(requirement_count=Count("requirement_mappings"))
    return render(request, "closure/check_list.html", {"checks": checks})


def check_create(request):
    form = CheckForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        check = form.save()
        messages.success(request, "Check created.")
        return redirect(check)
    return render(request, "closure/form.html", {"form": form, "title": "Create Check"})


def check_detail(request, pk):
    check = get_object_or_404(Check.objects.select_related("project", "test"), pk=pk)
    return render(request, "closure/check_detail.html", {"check": check, "mappings": check.requirement_mappings.select_related("requirement")})


def mapping_page(request):
    return render(
        request,
        "closure/mapping.html",
        {
            "test_form": RequirementTestMappingForm(),
            "check_form": RequirementCheckMappingForm(),
            "test_mappings": RequirementTestMapping.objects.select_related("requirement", "test")[:100],
            "check_mappings": RequirementCheckMapping.objects.select_related("requirement", "verification_check", "verification_check__test")[:100],
        },
    )


def mapping_test_create(request):
    form = RequirementTestMappingForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Requirement-test mapping saved.")
    else:
        messages.error(request, "Could not save requirement-test mapping.")
    return redirect("mapping_page")


def mapping_check_create(request):
    form = RequirementCheckMappingForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Requirement-check mapping saved.")
    else:
        messages.error(request, "Could not save requirement-check mapping.")
    return redirect("mapping_page")


def generate_package(request):
    projects = Project.objects.all()
    packages = GeneratedPackage.objects.select_related("project", "generated_by")[:20]
    if request.method == "POST":
        project = get_object_or_404(Project, pk=request.POST.get("project"))
        package = create_generated_package(project, generated_by=request.user, notes=request.POST.get("notes", ""))
        messages.success(request, f"Generated package {package.version}.")
        return redirect("download_package", pk=package.pk)
    return render(request, "closure/generate.html", {"projects": projects, "packages": packages})


def download_package(request, pk):
    package = get_object_or_404(GeneratedPackage, pk=pk)
    response = HttpResponse(package.artifact, content_type="text/plain")
    response["Content-Disposition"] = f'attachment; filename="speclink_{package.project.slug}_{package.version}.sv"'
    return response


def evidence_upload(request):
    form = EvidenceUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        project = form.cleaned_data["project"]
        report = form.cleaned_data["evidence_file"]
        try:
            run, snapshot = ingest_evidence_report(project, report)
        except EvidenceIngestError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"Evidence uploaded. Closure is {snapshot.closure_percent}%.")
            return redirect(run)
    return render(request, "closure/evidence_upload.html", {"form": form})


def run_detail(request, pk):
    run = get_object_or_404(RegressionRun.objects.select_related("project"), pk=pk)
    return render(
        request,
        "closure/run_detail.html",
        {
            "run": run,
            "snapshot": getattr(run, "closure_snapshot", None),
            "requirement_evidence": run.requirement_evidence.select_related("requirement")[:200],
            "failed_checks": run.check_evidence.exclude(result=CheckEvidence.RESULT_PASS).select_related("requirement", "test_run")[:100],
        },
    )


def snapshot_detail(request, pk):
    snapshot = get_object_or_404(ClosureSnapshot.objects.select_related("project", "regression_run"), pk=pk)
    return render(request, "closure/snapshot_detail.html", {"snapshot": snapshot, "evidence": snapshot.regression_run.requirement_evidence.select_related("requirement")})


def export_requirements_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="speclink_requirements.csv"'
    writer = csv.writer(response)
    writer.writerow(["project", "requirement_id", "category", "title", "priority", "status", "owner", "mapped_tests", "mapped_checks"])
    for req in Requirement.objects.select_related("project", "category").prefetch_related("test_mappings__test", "check_mappings__verification_check"):
        writer.writerow(
            [
                req.project.slug,
                req.requirement_id,
                req.category.code,
                req.title,
                req.priority,
                req.status,
                req.owner,
                ";".join(mapping.test.test_id for mapping in req.test_mappings.all()),
                ";".join(mapping.verification_check.check_id for mapping in req.check_mappings.all()),
            ]
        )
    return response

# Create your views here.

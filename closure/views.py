import csv

from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

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
from closure.services import workbench as workbench_service
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


# ---------------------------------------------------------------------------
# Workbench
# ---------------------------------------------------------------------------

_NODE_KINDS = {"category", "requirement", "test", "check"}


def _wb_context(request):
    """Resolve project, mode, run, view from query string."""
    projects = list(Project.objects.order_by("name"))
    project = None
    project_slug = request.GET.get("project")
    if project_slug:
        project = next((p for p in projects if p.slug == project_slug), None)
    if project is None and projects:
        project = projects[0]

    mode = request.GET.get("mode", "def")
    if mode not in ("def", "evidence"):
        mode = "def"

    view = request.GET.get("view", "req")
    if view not in ("req", "test"):
        view = "req"

    run = None
    runs = []
    if project is not None:
        runs = list(project.regression_runs.order_by("-uploaded_at")[:50])
        run_id = request.GET.get("run")
        if mode == "evidence":
            if run_id:
                run = next((r for r in runs if str(r.pk) == run_id), None)
            if run is None and runs:
                run = runs[0]

    selected = request.GET.get("node") or ""
    return {
        "projects": projects,
        "project": project,
        "mode": mode,
        "view": view,
        "runs": runs,
        "run": run,
        "selected_node": selected,
    }


def _qs_for_links(ctx, **overrides):
    """Build query-string preserving project/mode/view/run, with overrides."""
    parts = {}
    if ctx.get("project"):
        parts["project"] = ctx["project"].slug
    parts["mode"] = ctx["mode"]
    parts["view"] = ctx["view"]
    if ctx.get("run"):
        parts["run"] = ctx["run"].pk
    for k, v in overrides.items():
        if v is None:
            parts.pop(k, None)
        else:
            parts[k] = v
    return "&".join(f"{k}={v}" for k, v in parts.items())


def workbench(request):
    ctx = _wb_context(request)
    ctx["link_qs"] = _qs_for_links(ctx)
    ctx["link_mode_def"] = _qs_for_links(ctx, mode="def")
    ctx["link_mode_evidence"] = _qs_for_links(ctx, mode="evidence")
    ctx["link_view_req"] = _qs_for_links(ctx, view="req")
    ctx["link_view_test"] = _qs_for_links(ctx, view="test")
    return render(request, "closure/workbench/shell.html", ctx)


def workbench_tree(request):
    ctx = _wb_context(request)
    overlay = workbench_service.get_overlay(ctx["run"])
    nodes = []
    if ctx["project"]:
        nodes = workbench_service.project_root_children(ctx["project"], ctx["view"], overlay)
    ctx["nodes"] = nodes
    ctx["link_qs"] = _qs_for_links(ctx)
    ctx["depth"] = 0
    return render(request, "closure/workbench/_tree.html", ctx)


def workbench_node_children(request, kind, pk):
    if kind not in _NODE_KINDS:
        return HttpResponseBadRequest("bad kind")
    ctx = _wb_context(request)
    overlay = workbench_service.get_overlay(ctx["run"])

    parent_req_id = request.GET.get("parent_req")
    parent_req = None
    if parent_req_id:
        parent_req = Requirement.objects.filter(pk=parent_req_id).first()

    if kind == "category":
        category = get_object_or_404(RequirementCategory, pk=pk)
        nodes = workbench_service.category_children(category, overlay)
    elif kind == "requirement":
        requirement = get_object_or_404(Requirement, pk=pk)
        nodes = workbench_service.requirement_children(requirement, overlay)
    elif kind == "test":
        test = get_object_or_404(Test, pk=pk)
        nodes = workbench_service.test_children(test, overlay, parent_requirement=parent_req)
    else:
        nodes = []

    ctx["nodes"] = nodes
    ctx["link_qs"] = _qs_for_links(ctx)
    ctx["depth"] = int(request.GET.get("depth", "1"))
    return render(request, "closure/workbench/_tree_children.html", ctx)


def workbench_node_detail(request, kind, pk):
    if kind not in _NODE_KINDS:
        return HttpResponseBadRequest("bad kind")
    ctx = _wb_context(request)
    overlay = workbench_service.get_overlay(ctx["run"])
    ctx["overlay_active"] = overlay.active
    ctx["link_qs"] = _qs_for_links(ctx)

    if kind == "category":
        obj = get_object_or_404(RequirementCategory.objects.select_related("project", "parent"), pk=pk)
        ctx["category"] = obj
        ctx["children_categories"] = list(obj.children.all())
        ctx["children_requirements"] = list(obj.requirements.all())
        template = "closure/workbench/detail_category.html"
    elif kind == "requirement":
        obj = get_object_or_404(
            Requirement.objects.select_related("project", "category"), pk=pk
        )
        ctx["requirement"] = obj
        ctx["test_mappings"] = list(obj.test_mappings.select_related("test"))
        ctx["check_mappings"] = list(
            obj.check_mappings.select_related("verification_check", "verification_check__test")
        )
        ctx["evidence_history"] = list(obj.evidence.select_related("regression_run")[:20])
        ctx["req_counts"] = overlay.requirement_counts(obj.pk)
        ctx["req_status"] = overlay.requirement_status(obj.pk)
        if overlay.active:
            ctx["run_check_evidence"] = list(
                CheckEvidence.objects.filter(
                    regression_run=overlay.run, requirement=obj
                ).select_related("verification_check", "test_run")
            )
        template = "closure/workbench/detail_requirement.html"
    elif kind == "test":
        obj = get_object_or_404(Test.objects.select_related("project"), pk=pk)
        ctx["test"] = obj
        ctx["checks"] = list(obj.checks.all())
        ctx["requirement_mappings"] = list(obj.requirement_mappings.select_related("requirement"))
        ctx["test_status"] = overlay.test_status(obj.pk)
        if overlay.active:
            ctx["run_test_runs"] = list(
                obj.runs.filter(regression_run=overlay.run).select_related("regression_run")
            )
        template = "closure/workbench/detail_test.html"
    else:  # check
        obj = get_object_or_404(Check.objects.select_related("project", "test"), pk=pk)
        ctx["check"] = obj
        ctx["check_mappings"] = list(obj.requirement_mappings.select_related("requirement"))
        ctx["check_status"] = overlay.check_aggregate_status(obj.pk)
        if overlay.active:
            ctx["run_evidence"] = list(
                obj.evidence.filter(regression_run=overlay.run).select_related("requirement", "test_run")
            )
        template = "closure/workbench/detail_check.html"

    return render(request, template, ctx)


# ---- drawer (inline create / link) ----------------------------------------

def _drawer_render(request, ctx, form, title, submit_label, action_url, success_redirect=None):
    return render(
        request,
        "closure/workbench/_drawer.html",
        {
            **ctx,
            "form": form,
            "title": title,
            "submit_label": submit_label,
            "action_url": action_url,
            "success_redirect": success_redirect,
        },
    )


def workbench_drawer(request, action):
    """One endpoint, multiple actions:

    - new_requirement?category=<id>
    - new_test
    - new_check?test=<id>
    - map_test?requirement=<id>
    - map_check?requirement=<id>
    """
    ctx = _wb_context(request)
    ctx["link_qs"] = _qs_for_links(ctx)
    action_url = request.get_full_path()

    if action == "new_requirement":
        initial = {"project": ctx["project"]}
        category_id = request.GET.get("category")
        if category_id:
            initial["category"] = category_id
        form = RequirementForm(request.POST or None, initial=initial)
        if request.method == "POST" and form.is_valid():
            req = form.save()
            return _drawer_success(request, ctx, node=f"requirement:{req.pk}")
        return _drawer_render(request, ctx, form, "Create Requirement", "Create", action_url)

    if action == "new_test":
        initial = {"project": ctx["project"]}
        form = TestForm(request.POST or None, initial=initial)
        if request.method == "POST" and form.is_valid():
            test = form.save()
            # If launched from a requirement, also map it.
            req_id = request.GET.get("requirement")
            if req_id:
                req = Requirement.objects.filter(pk=req_id).first()
                if req:
                    RequirementTestMapping.objects.get_or_create(requirement=req, test=test)
            return _drawer_success(request, ctx, node=f"test:{test.pk}")
        return _drawer_render(request, ctx, form, "Create Test", "Create", action_url)

    if action == "new_check":
        initial = {"project": ctx["project"]}
        test_id = request.GET.get("test")
        if test_id:
            initial["test"] = test_id
        form = CheckForm(request.POST or None, initial=initial)
        if request.method == "POST" and form.is_valid():
            check = form.save()
            req_id = request.GET.get("requirement")
            if req_id:
                req = Requirement.objects.filter(pk=req_id).first()
                if req:
                    RequirementCheckMapping.objects.get_or_create(
                        requirement=req, verification_check=check
                    )
            return _drawer_success(request, ctx, node=f"check:{check.pk}")
        return _drawer_render(request, ctx, form, "Create Check", "Create", action_url)

    if action == "map_test":
        req_id = request.GET.get("requirement")
        requirement = Requirement.objects.filter(pk=req_id).first() if req_id else None
        initial = {"requirement": requirement}
        form = RequirementTestMappingForm(request.POST or None, initial=initial)
        if requirement is not None:
            form.fields["test"].queryset = Test.objects.filter(project=requirement.project)
        if request.method == "POST" and form.is_valid():
            mapping = form.save()
            return _drawer_success(request, ctx, node=f"test:{mapping.test_id}")
        return _drawer_render(request, ctx, form, "Map Test to Requirement", "Map", action_url)

    if action == "map_check":
        req_id = request.GET.get("requirement")
        requirement = Requirement.objects.filter(pk=req_id).first() if req_id else None
        initial = {"requirement": requirement}
        form = RequirementCheckMappingForm(request.POST or None, initial=initial)
        if requirement is not None:
            form.fields["verification_check"].queryset = Check.objects.filter(
                project=requirement.project
            ).select_related("test")
        if request.method == "POST" and form.is_valid():
            mapping = form.save()
            return _drawer_success(request, ctx, node=f"check:{mapping.verification_check_id}")
        return _drawer_render(request, ctx, form, "Map Check to Requirement", "Map", action_url)

    return HttpResponseBadRequest("unknown action")


def _drawer_success(request, ctx, node: str = ""):
    """Empty response + HX-Trigger header to close drawer + refresh tree/detail.

    HX-Trigger fires a window-level CustomEvent that the shell listens for.
    """
    import json as _json
    response = HttpResponse("")
    response["HX-Trigger"] = _json.dumps({"wb-refresh": {"node": node}})
    return response


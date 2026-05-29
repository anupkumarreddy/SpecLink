from django.urls import path

from closure import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("projects/", views.project_list, name="project_list"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<slug:slug>/", views.project_detail, name="project_detail"),
    path("categories/", views.category_tree, name="category_tree"),
    path("requirements/", views.requirement_list, name="requirement_list"),
    path("requirements/new/", views.requirement_create, name="requirement_create"),
    path("requirements/<int:pk>/", views.requirement_detail, name="requirement_detail"),
    path("tests/", views.test_list, name="test_list"),
    path("tests/new/", views.test_create, name="test_create"),
    path("tests/<int:pk>/", views.test_detail, name="test_detail"),
    path("checks/", views.check_list, name="check_list"),
    path("checks/new/", views.check_create, name="check_create"),
    path("checks/<int:pk>/", views.check_detail, name="check_detail"),
    path("mappings/", views.mapping_page, name="mapping_page"),
    path("mappings/tests/new/", views.mapping_test_create, name="mapping_test_create"),
    path("mappings/checks/new/", views.mapping_check_create, name="mapping_check_create"),
    path("generate/", views.generate_package, name="generate_package"),
    path("packages/<int:pk>/download/", views.download_package, name="download_package"),
    path("evidence/upload/", views.evidence_upload, name="evidence_upload"),
    path("runs/<int:pk>/", views.run_detail, name="run_detail"),
    path("snapshots/<int:pk>/", views.snapshot_detail, name="snapshot_detail"),
    path("exports/requirements.csv", views.export_requirements_csv, name="export_requirements_csv"),
]

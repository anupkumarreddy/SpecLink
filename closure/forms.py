import json

from django import forms

from closure.models import (
    Check,
    Project,
    Requirement,
    RequirementCategory,
    RequirementCheckMapping,
    RequirementTestMapping,
    Test,
)


class TailwindFormMixin:
    field_class = (
        "block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 "
        "placeholder:text-slate-400 shadow-soft "
        "focus:border-accent-500 focus:outline-none focus:ring-2 focus:ring-accent-100 "
        "disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
    )
    checkbox_class = (
        "h-4 w-4 rounded border-slate-300 text-accent-600 "
        "focus:ring-2 focus:ring-accent-200 focus:ring-offset-0"
    )

    def _style_fields(self):
        for field in self.fields.values():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            if isinstance(widget, forms.CheckboxInput):
                new = self.checkbox_class
            else:
                new = self.field_class
            widget.attrs["class"] = f"{existing} {new}".strip()


class ProjectForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "slug", "description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class RequirementCategoryForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = RequirementCategory
        fields = ["project", "parent", "name", "code", "description", "display_order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class RequirementForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Requirement
        fields = ["project", "category", "requirement_id", "title", "description", "spec_section", "priority", "status", "owner", "rationale"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class TestForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Test
        fields = ["project", "test_id", "description", "test_type", "file_path", "enabled", "owner"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class CheckForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Check
        fields = ["project", "test", "check_id", "name", "description", "check_type", "source_path", "source_line", "required_by_default"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class RequirementTestMappingForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = RequirementTestMapping
        fields = ["requirement", "test", "required_for_closure", "role", "rationale"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class RequirementCheckMappingForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = RequirementCheckMapping
        fields = ["requirement", "verification_check", "required_for_closure", "expected_count", "closure_role", "rationale"]
        labels = {"verification_check": "Check"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class EvidenceUploadForm(TailwindFormMixin, forms.Form):
    project = forms.ModelChoiceField(queryset=Project.objects.all())
    evidence_file = forms.FileField(help_text="Upload JSON produced by parse_speclink_log.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_evidence_file(self):
        uploaded = self.cleaned_data["evidence_file"]
        try:
            return json.loads(uploaded.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise forms.ValidationError(f"Evidence file must be valid UTF-8 JSON: {exc}") from exc

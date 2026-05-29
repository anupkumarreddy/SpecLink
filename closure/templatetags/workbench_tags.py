from django import template

register = template.Library()


_STATUS_DOT = {
    "closed": "bg-green-500",
    "passed": "bg-green-500",
    "pass": "bg-green-500",
    "partial": "bg-yellow-500",
    "failed": "bg-red-500",
    "fail": "bg-red-500",
    "open": "bg-gray-300",
    "missing": "bg-gray-400",
    "skipped": "bg-gray-300",
    "unknown": "bg-gray-300",
    "": "bg-transparent",
}

_STATUS_PILL = {
    "closed": "bg-green-100 text-green-800",
    "passed": "bg-green-100 text-green-800",
    "pass": "bg-green-100 text-green-800",
    "active": "bg-green-100 text-green-800",
    "partial": "bg-yellow-100 text-yellow-800",
    "medium": "bg-yellow-100 text-yellow-800",
    "high": "bg-yellow-100 text-yellow-800",
    "failed": "bg-red-100 text-red-800",
    "fail": "bg-red-100 text-red-800",
    "critical": "bg-red-100 text-red-800",
    "open": "bg-gray-100 text-gray-700",
    "missing": "bg-gray-200 text-gray-700",
    "skipped": "bg-gray-100 text-gray-700",
    "unknown": "bg-gray-100 text-gray-700",
}


@register.filter
def status_dot(value):
    return _STATUS_DOT.get(value or "", "bg-gray-300")


@register.filter
def status_pill(value):
    return _STATUS_PILL.get(value or "", "bg-gray-100 text-gray-700")


_KIND_ICON = {
    "category": "📁",
    "requirement": "📋",
    "test": "🧪",
    "check": "✔",
}


@register.filter
def kind_icon(kind):
    return _KIND_ICON.get(kind, "•")

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


# Refined status palette — solid tints with subtle inner ring for definition.
_STATUS_DOT = {
    "closed": "bg-emerald-500 shadow-[0_0_0_2px_rgba(16,185,129,0.18)]",
    "passed": "bg-emerald-500 shadow-[0_0_0_2px_rgba(16,185,129,0.18)]",
    "pass": "bg-emerald-500 shadow-[0_0_0_2px_rgba(16,185,129,0.18)]",
    "partial": "bg-amber-500 shadow-[0_0_0_2px_rgba(245,158,11,0.18)]",
    "failed": "bg-rose-500 shadow-[0_0_0_2px_rgba(244,63,94,0.18)]",
    "fail": "bg-rose-500 shadow-[0_0_0_2px_rgba(244,63,94,0.18)]",
    "open": "bg-slate-300",
    "missing": "bg-slate-400",
    "skipped": "bg-slate-300",
    "unknown": "bg-slate-300",
    "": "bg-transparent",
}

_STATUS_PILL = {
    "closed": "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20",
    "passed": "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20",
    "pass": "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20",
    "active": "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20",
    "partial": "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20",
    "medium": "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20",
    "high": "bg-orange-50 text-orange-700 ring-1 ring-inset ring-orange-600/20",
    "failed": "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-600/20",
    "fail": "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-600/20",
    "critical": "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-600/20",
    "open": "bg-slate-50 text-slate-600 ring-1 ring-inset ring-slate-500/15",
    "missing": "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-500/20",
    "skipped": "bg-slate-50 text-slate-600 ring-1 ring-inset ring-slate-500/15",
    "unknown": "bg-slate-50 text-slate-500 ring-1 ring-inset ring-slate-500/15",
    "draft": "bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-600/20",
    "low": "bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-600/20",
    "deprecated": "bg-slate-100 text-slate-500 ring-1 ring-inset ring-slate-500/20",
    "proves": "bg-accent-50 text-accent-700 ring-1 ring-inset ring-accent-600/20",
    "covers": "bg-accent-50 text-accent-700 ring-1 ring-inset ring-accent-600/20",
    "observes": "bg-violet-50 text-violet-700 ring-1 ring-inset ring-violet-600/20",
    "guards": "bg-teal-50 text-teal-700 ring-1 ring-inset ring-teal-600/20",
    "stimulates": "bg-fuchsia-50 text-fuchsia-700 ring-1 ring-inset ring-fuchsia-600/20",
}


@register.filter
def status_dot(value):
    return _STATUS_DOT.get(value or "", "bg-slate-300")


@register.filter
def status_pill(value):
    return _STATUS_PILL.get(value or "", "bg-slate-50 text-slate-600 ring-1 ring-inset ring-slate-500/15")


# Inline Heroicons (24x24 outline) — small set covering tree, headers, buttons.
_ICONS = {
    "folder": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3.75 6.75A2.25 2.25 0 0 1 6 4.5h3.379a1.5 1.5 0 0 1 1.06.44l1.122 1.12a1.5 1.5 0 0 0 1.06.44H18a2.25 2.25 0 0 1 2.25 2.25v8.25A2.25 2.25 0 0 1 18 19.5H6a2.25 2.25 0 0 1-2.25-2.25v-10.5Z"/></svg>',
    "doc": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25M9 14.25h6m-6 3h3m3.75-13.5L18 7.5M9 12h.008v.008H9V12Z"/><path d="M5.625 1.5H9a3.375 3.375 0 0 1 3.375 3.375V8.25c0 .621.504 1.125 1.125 1.125h3.375a3.375 3.375 0 0 1 3.375 3.375v6.75a3.375 3.375 0 0 1-3.375 3.375H5.625A3.375 3.375 0 0 1 2.25 19.5V4.875A3.375 3.375 0 0 1 5.625 1.5Z"/></svg>',
    "beaker": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23-.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5"/></svg>',
    "check-circle": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="m9 12.75 2.25 2.25L15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/></svg>',
    "chevron-right": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 5 7 7-7 7"/></svg>',
    "chevron-down": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>',
    "plus": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4.5v15m7.5-7.5h-15"/></svg>',
    "x": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 18 18 6M6 6l12 12"/></svg>',
    "external": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"/></svg>',
    "link": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"/></svg>',
    "search": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"/></svg>',
    "tree": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6.75 3v11.25A2.25 2.25 0 0 0 9 16.5h2.25M6.75 3H4.5m2.25 0H9m12 0h-2.25m-3.75 0h3.75m-3.75 0H9m9.75 0v11.25a2.25 2.25 0 0 1-2.25 2.25H13.5"/></svg>',
    "sparkle": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.456-2.456L14.25 6l1.035-.259a3.375 3.375 0 0 0 2.456-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"/></svg>',
}


@register.simple_tag
def icon(name, css_class="h-4 w-4"):
    """Render an inline Heroicon SVG. Usage: {% icon 'folder' 'h-5 w-5 text-accent-600' %}"""
    svg = _ICONS.get(name, "")
    if not svg:
        return ""
    open_tag = '<svg viewBox="0 0 24 24"'
    new_open = f'<svg class="{css_class}" viewBox="0 0 24 24"'
    return mark_safe(svg.replace(open_tag, new_open, 1))


_KIND_ICON = {
    "category": "folder",
    "requirement": "doc",
    "test": "beaker",
    "check": "check-circle",
}


@register.simple_tag
def kind_icon(kind, css_class="h-4 w-4"):
    return icon(_KIND_ICON.get(kind, "doc"), css_class)


_KIND_COLOR = {
    "category": "text-amber-500",
    "requirement": "text-accent-600",
    "test": "text-violet-500",
    "check": "text-emerald-500",
}


@register.filter
def kind_color(kind):
    return _KIND_COLOR.get(kind, "text-slate-500")

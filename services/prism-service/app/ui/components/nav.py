from nicegui import ui, app


_GLOBAL_CSS = """
body, .q-page, .nicegui-content {
    background-color: #f8fafc !important;
    color: #1e293b !important;
}
.q-page-container {
    background-color: #f8fafc !important;
}
.q-card {
    color: #1e293b !important;
}
.q-table {
    color: #1e293b !important;
}
.q-tab__label {
    color: #1e293b !important;
}
"""


def resolve_active_project(
    qs_proj: str | None,
    stored: str | None,
    projects: list[str],
) -> str:
    """Pick the active project from a cascade of signals.

    Issue resolve-io/.prism#43: nav.py used to seed `app.storage.user['project']`
    to the literal `'default'` sentinel even when real projects existed,
    then pass that sentinel as `value=` to a `ui.select(options=projects)`
    where `'default'` was NOT in `options`. NiceGUI raised ValueError and
    every dashboard page 500'd. Resolve everything against the live
    `projects` list so the chosen value is guaranteed to be in options.

    Order:
      1. URL ?project= if it points at a real project
      2. Stored user value if it points at a real project
      3. First available project
      4. ``'default'`` sentinel only if `projects` is empty
         (matches the `or ['default']` fallback for the options list).
    """
    if qs_proj and qs_proj in projects:
        return qs_proj
    if stored and stored in projects:
        return stored
    if projects:
        return projects[0]
    return 'default'


def create_nav():
    """Shared navigation header with project selector and page links."""
    from app.project_context import get_all_projects

    # Force light background globally
    ui.add_head_html(f'<style>{_GLOBAL_CSS}</style>')

    # URL ?project= wins so deep-links render the right project on first paint
    try:
        from nicegui import context as _ctx
        _qs_proj = _ctx.client.request.query_params.get('project')
    except Exception:
        _qs_proj = None

    projects = get_all_projects() or ['default']
    stored = app.storage.user.get('project')
    current = resolve_active_project(_qs_proj, stored, projects)
    # Persist the resolved value so subsequent renders skip the cascade.
    app.storage.user['project'] = current

    with ui.header().classes('items-center justify-between bg-indigo-700 px-6 shadow-md'):
        with ui.row().classes('items-center gap-3'):
            ui.label('PRISM').classes('text-xl font-bold text-white tracking-wide')
            # Project selector
            project_select = ui.select(
                options=projects,
                value=current,
                on_change=lambda e: _switch_project(e.value),
            ).props('dense dark outlined color=white').classes(
                'text-white min-w-[140px]'
            ).style('color: white')

        with ui.row().classes('gap-1'):
            for label, href in [
                ('Dashboard', '/'),
                ('Brain', '/brain'),
                ('Graph', '/graph'),
                ('Memory', '/memory'),
                ('Tasks', '/tasks'),
                ('Conductor', '/conductor'),
                ('Sessions', '/sessions'),
                ('Retrievals', '/retrievals'),
                ('Learning', '/learning'),
                ('Consolidation', '/consolidation'),
            ]:
                ui.link(label, href).classes(
                    'text-white no-underline px-3 py-1 rounded '
                    'hover:bg-white/20 transition-colors text-sm font-medium'
                )


def _switch_project(project_id: str):
    """Switch the active project and reload the page."""
    app.storage.user['project'] = project_id
    ui.navigate.reload()


def page_container(wide: bool = False):
    """Wrap page content in a clean, readable container.

    Standard (default) caps at max-w-7xl (~1280px) for comfortable reading.
    `wide=True` removes the cap so graph-dominated pages can breathe on
    wide monitors.
    """
    if wide:
        return ui.column().classes('w-full mx-auto px-6 py-4 gap-4')
    return ui.column().classes('w-full max-w-7xl mx-auto px-6 py-6 gap-6')

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
    if _qs_proj:
        app.storage.user['project'] = _qs_proj
    elif 'project' not in app.storage.user:
        app.storage.user['project'] = 'default'

    current = app.storage.user['project']
    projects = get_all_projects() or ['default']

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

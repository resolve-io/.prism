"""Memory page — browse and manage mulch expertise entries."""

from nicegui import ui, app

from app.project_context import get_project


def _memory_svc():
    return get_project(app.storage.user.get('project', 'default')).memory_svc
from app.ui.components.nav import create_nav, page_container

# Pastel badge class maps for light-mode readability
TYPE_BADGE_CLASSES = {
    'pattern': 'bg-blue-100 text-blue-800',
    'convention': 'bg-green-100 text-green-800',
    'failure': 'bg-red-100 text-red-800',
    'decision': 'bg-purple-100 text-purple-800',
}

CLASSIFICATION_BADGE_CLASSES = {
    'tactical': 'bg-orange-100 text-orange-800',
    'foundational': 'bg-sky-100 text-sky-800',
    'strategic': 'bg-emerald-100 text-emerald-800',
}

STATUS_BADGE_CLASSES = {
    'active': 'bg-green-100 text-green-800',
    'archived': 'bg-gray-100 text-gray-600',
    'needs_review': 'bg-amber-100 text-amber-800',
}


def _badge(text: str, classes: str):
    """Render a small pastel badge chip."""
    ui.html(
        f'<span class="inline-flex items-center px-2.5 py-0.5 rounded-full '
        f'text-xs font-medium {classes}">{text}</span>'
    )


def _build_entry_card(entry, on_refresh=None):
    """Render a single expertise entry as a clean white card."""
    with ui.element('div').classes(
        'w-full bg-white rounded-lg shadow-sm border border-gray-100 p-5'
    ):
        # Top row: name + badges
        with ui.row().classes('w-full items-start justify-between gap-3'):
            ui.label(entry.name).classes('text-base font-semibold text-gray-900')
            with ui.row().classes('gap-2 flex-wrap items-center shrink-0'):
                if entry.type:
                    _badge(
                        entry.type,
                        TYPE_BADGE_CLASSES.get(entry.type, 'bg-gray-100 text-gray-700'),
                    )
                if entry.classification:
                    _badge(
                        entry.classification,
                        CLASSIFICATION_BADGE_CLASSES.get(
                            entry.classification, 'bg-gray-100 text-gray-700'
                        ),
                    )
                if entry.status and entry.status != 'active':
                    _badge(
                        entry.status.replace('_', ' '),
                        STATUS_BADGE_CLASSES.get(entry.status, 'bg-gray-100 text-gray-600'),
                    )

        # Truncated description
        desc = entry.description or ''
        short = desc[:200] + ('...' if len(desc) > 200 else '')
        if short:
            ui.label(short).classes('text-sm text-gray-600 mt-2 leading-relaxed')

        # Meta row
        with ui.row().classes('gap-4 text-xs text-gray-400 mt-3'):
            if entry.recorded_at:
                ui.label(f'Recorded: {entry.recorded_at[:10]}')
            ui.label(f'Recalls: {entry.recall_count}')
            if entry.id:
                ui.label(entry.id).classes('font-mono')

        # Expandable detail
        with ui.expansion('Details').classes('w-full text-sm mt-2'):
            if desc:
                ui.label(desc).classes('text-gray-700 whitespace-pre-wrap leading-relaxed')

            if entry.evidence:
                ui.separator().classes('my-3')
                ui.label('Evidence').classes('font-medium text-gray-900 mt-2')
                ui.code(
                    str(entry.evidence), language='json',
                ).classes('w-full max-h-48 overflow-auto')

            if entry.outcomes:
                ui.separator().classes('my-3')
                ui.label('Outcomes').classes('font-medium text-gray-900 mt-2')
                for outcome in entry.outcomes:
                    ui.label(f'  - {outcome}').classes('text-gray-600')

            with ui.row().classes('gap-2 mt-3 text-xs text-gray-400'):
                ui.label(f'Domain: {entry.domain}')
                if entry.last_recalled:
                    ui.label(f'Last recalled: {entry.last_recalled[:19]}')


@ui.page('/memory')
def memory_page():
    create_nav()

    # --- Filters state ---
    filters = {
        'domain': None,
        'type': None,
        'classification': None,
        'status': 'active',
        'search': '',
    }

    with page_container():
        # Page heading
        ui.label('Memory').classes('text-2xl font-bold text-gray-900')
        ui.label('Browse and manage expertise entries').classes(
            'text-sm text-gray-500 -mt-4'
        )

        # --- Top controls row ---
        with ui.element('div').classes(
            'w-full bg-white rounded-lg shadow-sm border border-gray-100 p-5'
        ):
            with ui.row().classes('w-full items-end gap-3 flex-wrap'):
                search_input = ui.input(
                    'Search entries...',
                ).classes('flex-grow').props('outlined dense clearable')

                add_btn = ui.button(
                    'Add Entry', icon='add',
                ).classes(
                    'bg-indigo-600 text-white hover:bg-indigo-700'
                ).props('no-caps')

            # --- Filter chips ---
            with ui.column().classes('gap-4 w-full mt-4'):
                # Type filter
                ui.label('Type').classes('text-xs text-gray-500 font-medium uppercase tracking-wide')
                type_options = ['all', 'pattern', 'convention', 'failure', 'decision']
                with ui.row().classes('gap-2 flex-wrap'):
                    type_chips: dict[str, ui.chip] = {}
                    for t in type_options:
                        c = ui.chip(
                            t,
                            selectable=True,
                            selected=(t == 'all'),
                        ).classes('cursor-pointer').props('outline')
                        type_chips[t] = c

                # Classification filter
                ui.label('Classification').classes(
                    'text-xs text-gray-500 font-medium uppercase tracking-wide'
                )
                cls_options = ['all', 'tactical', 'foundational', 'strategic']
                with ui.row().classes('gap-2 flex-wrap'):
                    cls_chips: dict[str, ui.chip] = {}
                    for cl in cls_options:
                        c = ui.chip(
                            cl,
                            selectable=True,
                            selected=(cl == 'all'),
                        ).classes('cursor-pointer').props('outline')
                        cls_chips[cl] = c

                # Status filter
                ui.label('Status').classes(
                    'text-xs text-gray-500 font-medium uppercase tracking-wide'
                )
                status_options = ['active', 'archived', 'needs_review', 'all']
                with ui.row().classes('gap-2 flex-wrap'):
                    status_chips: dict[str, ui.chip] = {}
                    for s in status_options:
                        c = ui.chip(
                            s.replace('_', ' '),
                            selectable=True,
                            selected=(s == 'active'),
                        ).classes('cursor-pointer').props('outline')
                        status_chips[s] = c

        # Chip click handlers
        def select_type(name):
            filters['type'] = None if name == 'all' else name
            for t, c in type_chips.items():
                c.set_selected(t == name)
            refresh_entries()

        def select_cls(name):
            filters['classification'] = None if name == 'all' else name
            for cl, c in cls_chips.items():
                c.set_selected(cl == name)
            refresh_entries()

        def select_status(name):
            filters['status'] = None if name == 'all' else name
            for s, c in status_chips.items():
                c.set_selected(s == name)
            refresh_entries()

        for t in type_options:
            type_chips[t].on('click', lambda _, t=t: select_type(t))
        for cl in cls_options:
            cls_chips[cl].on('click', lambda _, cl=cl: select_cls(cl))
        for s in status_options:
            status_chips[s].on('click', lambda _, s=s: select_status(s))

        # --- Main content: domain tabs + entries ---
        domains = _memory_svc().list_domains()
        entries_container = ui.column().classes('w-full gap-3')

        if domains:
            with ui.row().classes('w-full gap-6 items-start'):
                # Left: vertical domain tabs
                with ui.element('div').classes(
                    'shrink-0 bg-white rounded-lg shadow-sm border border-gray-100 p-4'
                ):
                    ui.label('Domains').classes(
                        'text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3'
                    )
                    domain_tabs = ui.tabs().props('vertical').classes(
                        'min-w-[160px]'
                    )
                    with domain_tabs:
                        all_tab = ui.tab('all', label='All')
                        tab_map = {'all': all_tab}
                        for d in domains:
                            # Get count for each domain
                            try:
                                count = len(_memory_svc().list_entries(domain=d))
                            except Exception:
                                count = 0
                            tab_map[d] = ui.tab(d, label=f'{d} ({count})')

                # Right: entries panel
                with ui.column().classes('flex-grow min-w-0'):
                    entries_container = ui.column().classes('w-full gap-3')

            def on_tab_change(e):
                val = e.value if hasattr(e, 'value') else e.args
                filters['domain'] = None if val == 'all' else val
                refresh_entries()

            domain_tabs.on('update:model-value', on_tab_change)
        else:
            with entries_container:
                ui.label(
                    'No domains found. Add an entry to create a domain.'
                ).classes('text-gray-500 italic py-8')

        # --- Entry rendering ---
        def refresh_entries():
            entries_container.clear()
            search_text = (filters.get('search') or '').strip().lower()

            try:
                if filters['domain']:
                    entries = _memory_svc().list_entries(
                        domain=filters['domain'],
                        type_filter=filters['type'],
                        classification_filter=filters['classification'],
                        status_filter=filters['status'] or '',
                    )
                else:
                    # Across all domains
                    all_entries = []
                    for d in _memory_svc().list_domains():
                        all_entries.extend(_memory_svc().list_entries(
                            domain=d,
                            type_filter=filters['type'],
                            classification_filter=filters['classification'],
                            status_filter=filters['status'] or '',
                        ))
                    entries = all_entries
            except Exception as exc:
                with entries_container:
                    ui.label(f'Error loading entries: {exc}').classes(
                        'text-red-600'
                    )
                return

            # Apply text search filter
            if search_text:
                entries = [
                    e for e in entries
                    if search_text in e.name.lower()
                    or search_text in e.description.lower()
                ]

            with entries_container:
                if not entries:
                    ui.label('No entries match the current filters.').classes(
                        'text-gray-500 italic py-8'
                    )
                    return

                ui.label(f'{len(entries)} entries').classes(
                    'text-sm text-gray-500'
                )
                for entry in entries:
                    _build_entry_card(entry, on_refresh=refresh_entries)

        def on_search_change(e):
            filters['search'] = search_input.value or ''
            refresh_entries()

        search_input.on('keydown.enter', on_search_change)
        search_input.on('clear', on_search_change)

        # --- Add Entry dialog ---
        with ui.dialog() as add_dialog, ui.card().classes(
            'w-full max-w-md bg-white'
        ):
            ui.label('Add Expertise Entry').classes(
                'text-lg font-semibold text-gray-900 mb-4'
            )

            existing_domains = _memory_svc().list_domains() or ['general']
            domain_input = ui.select(
                label='Domain',
                options=existing_domains,
                with_input=True,
                new_value_mode='add-unique',
            ).classes('w-full')

            name_input = ui.input('Name').classes('w-full').props('outlined')
            desc_input = ui.textarea('Description').classes('w-full').props(
                'outlined rows=4'
            )
            type_input = ui.select(
                label='Type',
                options=['pattern', 'convention', 'failure', 'decision'],
            ).classes('w-full')
            cls_input = ui.select(
                label='Classification',
                options=['tactical', 'foundational', 'strategic'],
            ).classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 mt-6'):
                ui.button('Cancel', on_click=add_dialog.close).props(
                    'flat no-caps'
                ).classes('text-gray-600')

                async def submit_entry():
                    d = domain_input.value
                    n = name_input.value
                    desc = desc_input.value
                    t = type_input.value
                    cl = cls_input.value

                    if not all([d, n, desc, t, cl]):
                        ui.notify('All fields are required', type='warning')
                        return

                    try:
                        _memory_svc().store(
                            domain=d,
                            name=n,
                            description=desc,
                            type=t,
                            classification=cl,
                        )
                        ui.notify(f'Entry "{n}" saved', type='positive')
                        add_dialog.close()
                        # Reset form
                        name_input.set_value('')
                        desc_input.set_value('')
                        type_input.set_value(None)
                        cls_input.set_value(None)
                        refresh_entries()
                    except Exception as exc:
                        ui.notify(f'Error saving entry: {exc}', type='negative')

                ui.button(
                    'Save', icon='save', on_click=submit_entry,
                ).classes(
                    'bg-indigo-600 text-white hover:bg-indigo-700'
                ).props('no-caps')

        add_btn.on('click', add_dialog.open)

        # --- Domain stats ---
        ui.label('Domain Statistics').classes(
            'text-lg font-semibold text-gray-900'
        )
        stats = _memory_svc().domain_stats()
        if stats:
            with ui.row().classes('gap-4 flex-wrap'):
                for domain_name, counts in stats.items():
                    with ui.element('div').classes(
                        'bg-white rounded-lg shadow-sm border border-gray-100 p-5 min-w-[180px]'
                    ):
                        ui.label(domain_name).classes(
                            'font-semibold text-gray-900 text-base'
                        )
                        with ui.row().classes('gap-4 text-sm text-gray-600 mt-2'):
                            ui.label(f"Active: {counts.get('active', 0)}")
                            ui.label(f"Archived: {counts.get('archived', 0)}")
                        ui.label(
                            f"Total: {counts.get('total', 0)}"
                        ).classes('text-xs text-gray-400 mt-1')
        else:
            ui.label('No domains yet.').classes('text-gray-500 italic')

        # Initial load
        refresh_entries()

"""Tasks board page -- kanban-style task management with What's Next."""

from nicegui import ui, app

from app.project_context import get_project


def _task_svc():
    return get_project(app.storage.user.get('project', 'default')).task_svc

from app.ui.components.nav import create_nav, page_container


# ── Constants ───────────────────────────────────────────────────────

_STATUS_COLUMNS = ["pending", "in_progress", "done", "blocked"]

_STATUS_LABELS = {
    "pending": "Pending",
    "in_progress": "In Progress",
    "done": "Done",
    "blocked": "Blocked",
}

_STATUS_ICONS = {
    "pending": "schedule",
    "in_progress": "play_circle",
    "done": "check_circle",
    "blocked": "block",
}

# Pastel badge classes for column headers
_STATUS_BADGE_CLASSES = {
    "pending": "bg-blue-100 text-blue-800",
    "in_progress": "bg-amber-100 text-amber-800",
    "done": "bg-green-100 text-green-800",
    "blocked": "bg-red-100 text-red-800",
}

_AGENT_OPTIONS = ["none", "sm", "qa", "dev", "po"]

_PRIORITY_BADGE_CLASSES = {
    0: "bg-gray-100 text-gray-600",
    1: "bg-blue-100 text-blue-800",
    2: "bg-amber-100 text-amber-800",
    3: "bg-orange-100 text-orange-800",
    4: "bg-red-100 text-red-800",
    5: "bg-red-200 text-red-900",
}


# ── Helpers ─────────────────────────────────────────────────────────

def _priority_classes(p: int) -> str:
    if p >= 5:
        return "bg-red-200 text-red-900"
    return _PRIORITY_BADGE_CLASSES.get(p, "bg-gray-100 text-gray-600")


def _priority_color(p: int) -> str:
    """Legacy color helper for Quasar badge components."""
    colors = {0: "gray", 1: "blue", 2: "amber", 3: "orange", 4: "red", 5: "red"}
    if p >= 5:
        return "red"
    return colors.get(p, "gray")


def _small_badge(text: str, classes: str):
    """Render a small pastel badge as inline HTML."""
    ui.html(
        f'<span class="inline-flex items-center px-2 py-0.5 rounded-full '
        f'text-xs font-medium {classes}">{text}</span>'
    )


def _format_ts(ts: str) -> str:
    """Format an ISO timestamp to a shorter display form."""
    if not ts:
        return "-"
    return ts[:19].replace("T", " ")


# ── Task Detail Dialog ──────────────────────────────────────────────

def _open_task_detail(task_id: str, on_change):
    """Open a dialog showing full task details with status transition buttons."""
    task_svc = _task_svc()

    task = task_svc.get(task_id)
    if task is None:
        ui.notify("Task not found", type="negative")
        return

    with ui.dialog() as dlg, ui.card().classes('w-full max-w-2xl bg-white p-6'):
        # Header
        with ui.row().classes('w-full items-start justify-between mb-5'):
            ui.label(task.title).classes('text-lg font-semibold text-gray-900')
            _small_badge(
                _STATUS_LABELS.get(task.status, task.status),
                _STATUS_BADGE_CLASSES.get(task.status, "bg-gray-100 text-gray-600"),
            )

        # Info grid
        with ui.element('div').classes(
            'w-full bg-gray-50 rounded-lg p-4 mb-5'
        ):
            with ui.grid(columns=2).classes('w-full gap-x-6 gap-y-3'):
                ui.label("ID").classes('text-xs text-gray-500 font-medium')
                ui.label(task.id).classes('text-xs font-mono text-gray-700 break-all')

                ui.label("Priority").classes('text-xs text-gray-500 font-medium')
                with ui.row().classes('items-center gap-1'):
                    _small_badge(
                        f"P{task.priority}",
                        _priority_classes(task.priority),
                    )

                ui.label("Agent").classes('text-xs text-gray-500 font-medium')
                ui.label(task.assigned_agent or "-").classes('text-xs text-gray-700')

                ui.label("Story").classes('text-xs text-gray-500 font-medium')
                ui.label(task.story_file or "-").classes(
                    'text-xs text-gray-700 break-all'
                )

                ui.label("Created").classes('text-xs text-gray-500 font-medium')
                ui.label(_format_ts(task.created_at)).classes('text-xs text-gray-700')

                ui.label("Updated").classes('text-xs text-gray-500 font-medium')
                ui.label(_format_ts(task.updated_at)).classes('text-xs text-gray-700')

                ui.label("Completed").classes('text-xs text-gray-500 font-medium')
                ui.label(_format_ts(task.completed_at)).classes('text-xs text-gray-700')

        # Description
        if task.description:
            ui.label("Description").classes(
                'text-xs text-gray-500 font-medium uppercase tracking-wide mb-2'
            )
            ui.label(task.description).classes(
                'text-sm text-gray-700 bg-gray-50 p-4 rounded-lg w-full '
                'whitespace-pre-wrap leading-relaxed mb-5'
            )

        # Tags
        if task.tags:
            ui.label("Tags").classes(
                'text-xs text-gray-500 font-medium uppercase tracking-wide mb-2'
            )
            with ui.row().classes('gap-2 mb-5 flex-wrap'):
                for tag in task.tags:
                    _small_badge(tag, 'bg-blue-100 text-blue-800')

        # Blocked reason
        if task.status == "blocked" and task.blocked_reason:
            ui.label("Blocked Reason").classes(
                'text-xs text-gray-500 font-medium uppercase tracking-wide mb-2'
            )
            ui.label(task.blocked_reason).classes(
                'text-sm text-red-800 bg-red-50 p-4 rounded-lg w-full mb-5'
            )

        # Dependencies
        if task.dependencies:
            ui.label("Dependencies").classes(
                'text-xs text-gray-500 font-medium uppercase tracking-wide mb-2'
            )
            with ui.column().classes('gap-2 mb-5'):
                for dep_id in task.dependencies:
                    dep = task_svc.get(dep_id)
                    dep_label = f"{dep.title} ({dep.status})" if dep else dep_id
                    with ui.row().classes('items-center gap-2'):
                        ui.icon("subdirectory_arrow_right").classes(
                            'text-sm text-gray-400'
                        )
                        ui.label(dep_label).classes('text-sm text-gray-700')

        # History timeline
        ui.label("History").classes(
            'text-xs text-gray-500 font-medium uppercase tracking-wide mb-2'
        )
        history = task_svc.history(task_id)
        if history:
            with ui.column().classes(
                'gap-2 mb-5 pl-4 border-l-2 border-gray-200'
            ):
                for entry in history:
                    with ui.row().classes('items-start gap-2'):
                        ui.icon("fiber_manual_record").classes(
                            'text-[8px] mt-1.5 text-indigo-400'
                        )
                        with ui.column().classes('gap-0'):
                            ui.label(
                                f"{entry.action}"
                                + (f" by {entry.actor}" if entry.actor else "")
                            ).classes('text-xs font-semibold text-gray-900')
                            if entry.details:
                                ui.label(entry.details).classes(
                                    'text-xs text-gray-500'
                                )
                            ui.label(_format_ts(entry.timestamp)).classes(
                                'text-[10px] text-gray-400'
                            )
        else:
            ui.label("No history yet").classes('text-xs text-gray-400 mb-5')

        ui.separator().classes('my-2')

        # Status transition buttons
        def _transition(new_status, reason=""):
            kwargs = {"status": new_status}
            if new_status == "blocked" and reason:
                kwargs["blocked_reason"] = reason
            if new_status != "blocked":
                kwargs["blocked_reason"] = ""
            task_svc.update(task_id, **kwargs)
            ui.notify(f"Task moved to {new_status}", type="positive")
            dlg.close()
            on_change()

        with ui.row().classes('w-full justify-between items-center mt-4'):
            with ui.row().classes('gap-2 items-center'):
                if task.status == "pending":
                    ui.button(
                        "Start", icon="play_arrow",
                        on_click=lambda: _transition("in_progress"),
                    ).classes(
                        'bg-amber-500 text-white hover:bg-amber-600'
                    ).props('no-caps')

                if task.status == "in_progress":
                    ui.button(
                        "Complete", icon="check",
                        on_click=lambda: _transition("done"),
                    ).classes(
                        'bg-green-600 text-white hover:bg-green-700'
                    ).props('no-caps')

                if task.status in ("pending", "in_progress"):
                    block_reason_input = ui.input(
                        "Block reason",
                    ).classes('w-48').props('dense outlined')
                    ui.button(
                        "Block", icon="block",
                        on_click=lambda: _transition(
                            "blocked", block_reason_input.value
                        ),
                    ).classes(
                        'bg-red-500 text-white hover:bg-red-600'
                    ).props('no-caps')

                if task.status in ("done", "blocked"):
                    ui.button(
                        "Reopen", icon="replay",
                        on_click=lambda: _transition("pending"),
                    ).classes(
                        'bg-blue-600 text-white hover:bg-blue-700'
                    ).props('no-caps')

            ui.button("Close", on_click=dlg.close).props('flat no-caps').classes(
                'text-gray-600'
            )

    dlg.open()


# ── Create Task Dialog ──────────────────────────────────────────────

def _open_create_dialog(on_change):
    """Open dialog to create a new task."""
    task_svc = _task_svc()

    with ui.dialog() as dlg, ui.card().classes('w-full max-w-lg bg-white p-6'):
        ui.label("Create Task").classes('text-lg font-semibold text-gray-900 mb-4')

        title_input = ui.input("Title").classes('w-full').props('outlined')
        desc_input = ui.textarea("Description").classes('w-full').props('outlined')
        with ui.row().classes('w-full gap-4'):
            priority_input = ui.number(
                "Priority", value=0, min=0, max=5,
            ).classes('w-24').props('outlined')
            agent_select = ui.select(
                _AGENT_OPTIONS, label="Agent", value="none",
            ).classes('w-32').props('outlined')
        story_input = ui.input("Story file").classes('w-full').props('outlined')
        tags_input = ui.input("Tags (comma-separated)").classes('w-full').props(
            'outlined'
        )

        def _submit():
            title = (title_input.value or "").strip()
            if not title:
                ui.notify("Title is required", type="warning")
                return
            agent = agent_select.value if agent_select.value != "none" else ""
            raw_tags = (tags_input.value or "").strip()
            tags = (
                [t.strip() for t in raw_tags.split(",") if t.strip()]
                if raw_tags
                else []
            )

            task_svc.create(
                title=title,
                description=(desc_input.value or "").strip(),
                priority=int(priority_input.value or 0),
                story_file=(story_input.value or "").strip(),
                assigned_agent=agent,
                tags=tags,
            )
            ui.notify("Task created", type="positive")
            dlg.close()
            on_change()

        with ui.row().classes('w-full justify-end gap-2 mt-6'):
            ui.button("Cancel", on_click=dlg.close).props('flat no-caps').classes(
                'text-gray-600'
            )
            ui.button("Create", icon="add", on_click=_submit).classes(
                'bg-indigo-600 text-white hover:bg-indigo-700'
            ).props('no-caps')

    dlg.open()


# ── Board Rendering ─────────────────────────────────────────────────

def _build_next_task_card(container):
    """Render the 'What's Next' card at the top of the page."""
    task_svc = _task_svc()

    container.clear()
    with container:
        result = task_svc.next_task()
        if result is None:
            with ui.element('div').classes(
                'w-full bg-white rounded-lg shadow-sm border border-gray-100 p-6 '
                'text-center'
            ):
                ui.icon("celebration").classes("text-4xl mb-2 text-green-500")
                ui.label("All caught up!").classes(
                    "text-xl font-semibold text-gray-900"
                )
                ui.label(
                    "No pending tasks ready to start. Create a new task "
                    "or unblock existing ones."
                ).classes("text-sm text-gray-500 mt-1")
        else:
            task = result["task"]
            reason = result["reason"]
            # White card with indigo left border accent
            with ui.element('div').classes(
                'w-full bg-white rounded-lg shadow-sm '
                'border border-gray-100 border-l-4 !border-l-indigo-600 p-6'
            ):
                with ui.row().classes('items-center gap-2 mb-3'):
                    ui.icon("auto_awesome").classes("text-xl text-indigo-600")
                    ui.label("What's Next").classes(
                        "text-lg font-semibold text-gray-900"
                    )

                ui.label(task.title).classes(
                    "text-base font-semibold text-gray-900 mb-1"
                )
                ui.label(reason).classes("text-sm text-gray-500 mb-3")

                with ui.row().classes('items-center gap-2 flex-wrap'):
                    if task.assigned_agent:
                        _small_badge(
                            task.assigned_agent.upper(),
                            'bg-purple-100 text-purple-800',
                        )
                    _small_badge(
                        f"Priority {task.priority}",
                        _priority_classes(task.priority),
                    )
                    for tag in task.tags:
                        _small_badge(tag, 'bg-blue-100 text-blue-800')

                def _start_task(tid=task.id):
                    task_svc.update(tid, status="in_progress")
                    ui.notify("Task started", type="positive")

                ui.button(
                    "Start", icon="play_arrow",
                    on_click=_start_task,
                ).classes(
                    'mt-4 bg-indigo-600 text-white hover:bg-indigo-700'
                ).props('no-caps')


def _build_board(container, on_change):
    """Render the four-column kanban board."""
    task_svc = _task_svc()

    container.clear()

    all_tasks = task_svc.list()
    by_status = {s: [] for s in _STATUS_COLUMNS}
    for t in all_tasks:
        if t.status in by_status:
            by_status[t.status].append(t)

    with container:
        with ui.row().classes('w-full gap-4 items-start'):
            for status in _STATUS_COLUMNS:
                tasks = by_status[status]
                label = _STATUS_LABELS[status]
                icon = _STATUS_ICONS[status]
                badge_cls = _STATUS_BADGE_CLASSES.get(
                    status, "bg-gray-100 text-gray-600"
                )

                # Column with light background
                with ui.column().classes(
                    'flex-1 min-w-[240px] bg-gray-50 rounded-lg p-4'
                ):
                    # Column header
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon(icon).classes('text-lg text-gray-500')
                        ui.label(label).classes(
                            'text-sm font-semibold text-gray-900'
                        )
                        ui.html(
                            f'<span class="inline-flex items-center justify-center '
                            f'w-6 h-6 rounded-full text-xs font-semibold '
                            f'{badge_cls}">{len(tasks)}</span>'
                        )

                    # Task cards
                    if not tasks:
                        ui.label("No tasks").classes(
                            'text-sm text-gray-400 italic py-6 text-center w-full'
                        )
                    else:
                        for task in tasks:
                            with ui.element('div').classes(
                                'w-full bg-white rounded-lg shadow-sm '
                                'border border-gray-100 p-4 cursor-pointer '
                                'hover:shadow-md transition-shadow'
                            ).on(
                                'click',
                                lambda e, tid=task.id: _open_task_detail(
                                    tid, on_change
                                ),
                            ):
                                ui.label(task.title).classes(
                                    'text-sm font-semibold text-gray-900 mb-2'
                                )
                                with ui.row().classes('gap-2 flex-wrap'):
                                    _small_badge(
                                        f"P{task.priority}",
                                        _priority_classes(task.priority),
                                    )
                                    if task.assigned_agent:
                                        _small_badge(
                                            task.assigned_agent.upper(),
                                            'bg-purple-100 text-purple-800',
                                        )
                                    for tag in task.tags[:3]:
                                        _small_badge(
                                            tag,
                                            'bg-blue-100 text-blue-800',
                                        )


# ── Page registration ───────────────────────────────────────────────

@ui.page('/tasks')
def tasks_page():
    """Tasks kanban board with What's Next and create/detail dialogs."""
    create_nav()

    with page_container():
        # Header row
        with ui.row().classes('w-full items-center justify-between'):
            with ui.column().classes('gap-0'):
                ui.label("Tasks Board").classes(
                    "text-2xl font-bold text-gray-900"
                )
                ui.label("Manage and track work items").classes(
                    "text-sm text-gray-500"
                )
            ui.button(
                "Create Task", icon="add",
                on_click=lambda: _open_create_dialog(refresh),
            ).classes(
                'bg-indigo-600 text-white hover:bg-indigo-700'
            ).props('no-caps')

        # What's Next card
        next_container = ui.column().classes('w-full')

        # Board columns
        board_container = ui.column().classes('w-full')

        # Refresh logic
        def refresh():
            _build_next_task_card(next_container)
            _build_board(board_container, refresh)

        refresh()
        ui.timer(3.0, refresh)

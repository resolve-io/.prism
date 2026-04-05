"""Dashboard page -- workflow pipeline, metrics, and governance health."""

from nicegui import ui, app

from app.ui.components.nav import create_nav, page_container
from app.models.workflow import WORKFLOW_STEPS


# -- Agent badge colours (soft pastels for light mode) --------------------
_AGENT_COLORS = {
    "sm": "purple",
    "qa": "teal",
    "dev": "indigo",
}

_AGENT_LABELS = {
    "sm": "SM",
    "qa": "QA",
    "dev": "DEV",
}


def _step_display_name(step_id: str) -> str:
    """Convert snake_case step id to Title Case label."""
    return step_id.replace("_", " ").title()


def _build_pipeline(container, steps: list[dict]):
    """Render the horizontal step-pipeline inside *container*."""
    container.clear()
    with container:
        with ui.row().classes("w-full flex-nowrap items-center gap-2 overflow-x-auto pb-2"):
            for i, step in enumerate(steps):
                status = step.get("status", "pending")
                step_type = step.get("type", "agent")
                agent = step.get("agent")

                # -- colours / icons per status & type --
                if status == "completed":
                    border_cls = "border-green-400"
                    icon_name = "check_circle"
                    icon_color = "green"
                    status_badge_cls = "bg-green-100 text-green-800"
                    status_label = "Done"
                elif status == "current":
                    border_cls = "border-blue-400"
                    icon_name = "play_circle"
                    icon_color = "#2563eb"
                    status_badge_cls = "bg-blue-100 text-blue-800"
                    status_label = "Active"
                elif step_type == "gate":
                    border_cls = "border-amber-400"
                    icon_name = "verified_user"
                    icon_color = "#d97706"
                    status_badge_cls = "bg-amber-100 text-amber-800"
                    status_label = "Gate"
                else:
                    border_cls = "border-gray-200"
                    icon_name = "radio_button_unchecked"
                    icon_color = "#9ca3af"
                    status_badge_cls = "bg-gray-100 text-gray-500"
                    status_label = "Pending"

                # -- card for each step --
                with ui.card().classes(
                    f"min-w-[140px] p-4 bg-white border {border_cls} "
                    "rounded-lg shadow-sm"
                ).style("border-width: 1.5px"):
                    # top row: icon + status chip
                    with ui.row().classes("items-center justify-between w-full mb-2"):
                        ui.icon(icon_name, color=icon_color).classes("text-xl")
                        ui.html(
                            f'<span class="text-[10px] font-medium px-2 py-0.5 '
                            f'rounded-full {status_badge_cls}">{status_label}</span>'
                        )

                    # step name
                    ui.label(_step_display_name(step["id"])).classes(
                        "text-sm font-semibold text-gray-900 leading-tight"
                    )

                    # agent badge
                    if agent:
                        agent_label = _AGENT_LABELS.get(agent, agent.upper())
                        color = _AGENT_COLORS.get(agent, "gray")
                        # Use soft pastel badge
                        ui.badge(agent_label, color=color).props("outline").classes("mt-2")

                # connector arrow between cards (skip after last)
                if i < len(steps) - 1:
                    ui.icon("chevron_right").classes(
                        "text-xl text-gray-300 self-center flex-shrink-0"
                    )


def _build_metrics(container, state):
    """Render metric cards inside *container*."""
    container.clear()
    with container:
        if state is None or not state.active:
            with ui.card().classes("w-full p-8 text-center bg-white shadow-sm rounded-lg"):
                ui.icon("info", color="#6b7280").classes("text-4xl")
                ui.label("No active workflow").classes(
                    "text-base text-gray-500 mt-3"
                )
            return

        accent_colors = {
            "blue": "border-blue-400",
            "purple": "border-purple-400",
            "teal": "border-teal-400",
            "indigo": "border-indigo-400",
        }

        cards = [
            ("Current Step", _step_display_name(state.current_step), "footsteps", "blue"),
            ("Agent", (state.current_step and _agent_for_step(state.current_step)) or "-", "person", "purple"),
            ("Model", state.model or "-", "smart_toy", "teal"),
            ("Tokens Used", f"{state.total_tokens:,}", "token", "indigo"),
        ]

        for title, value, icon_name, color in cards:
            left_border = accent_colors.get(color, "border-gray-300")
            with ui.card().classes(
                f"flex-1 min-w-[180px] p-5 bg-white shadow-sm rounded-lg "
                f"border-l-4 {left_border}"
            ):
                with ui.row().classes("items-center gap-2 mb-3"):
                    ui.icon(icon_name, color=color).classes("text-xl opacity-70")
                    ui.label(title).classes(
                        "text-xs text-gray-500 uppercase tracking-wide font-medium"
                    )
                ui.label(str(value)).classes("text-2xl font-bold text-gray-900")


def _agent_for_step(step_id: str) -> str:
    """Look up agent persona for a given step id."""
    for s in WORKFLOW_STEPS:
        if s["id"] == step_id:
            agent = s.get("agent")
            return _AGENT_LABELS.get(agent, "-") if agent else "Gate"
    return "-"


def _build_health(container, health):
    """Render governance health report inside *container*."""
    container.clear()
    with container:
        issues_found = False

        if health.flagged_conflicts > 0:
            issues_found = True
            with ui.row().classes("items-center gap-3 py-2"):
                ui.html(
                    f'<span class="text-xs font-medium px-2.5 py-1 rounded-full '
                    f'bg-red-100 text-red-800">'
                    f'{health.flagged_conflicts} conflict(s)</span>'
                )
                ui.label("Contradictory expertise entries detected").classes(
                    "text-sm text-gray-600"
                )

        if health.stuck_tasks > 0:
            issues_found = True
            with ui.row().classes("items-center gap-3 py-2"):
                ui.html(
                    f'<span class="text-xs font-medium px-2.5 py-1 rounded-full '
                    f'bg-amber-100 text-amber-800">'
                    f'{health.stuck_tasks} stuck task(s)</span>'
                )
                ui.label("Tasks in-progress beyond stale threshold").classes(
                    "text-sm text-gray-600"
                )

        if health.stale_brain_docs > 0:
            issues_found = True
            with ui.row().classes("items-center gap-3 py-2"):
                ui.html(
                    f'<span class="text-xs font-medium px-2.5 py-1 rounded-full '
                    f'bg-blue-100 text-blue-800">'
                    f'{health.stale_brain_docs} stale doc(s)</span>'
                )
                ui.label("Brain documents may need re-indexing").classes(
                    "text-sm text-gray-600"
                )

        if health.domains_near_cap:
            issues_found = True
            with ui.row().classes("items-center gap-3 py-2"):
                ui.html(
                    f'<span class="text-xs font-medium px-2.5 py-1 rounded-full '
                    f'bg-amber-100 text-amber-800">'
                    f'{len(health.domains_near_cap)} domain(s) near cap</span>'
                )
                ui.label(", ".join(health.domains_near_cap)).classes(
                    "text-sm text-gray-600"
                )

        if not issues_found:
            with ui.row().classes("items-center gap-3 py-2"):
                ui.html(
                    '<span class="text-xs font-medium px-2.5 py-1 rounded-full '
                    'bg-green-100 text-green-800">All clear</span>'
                )
                ui.label("No governance issues").classes(
                    "text-sm text-gray-600"
                )

        if health.last_governance_run:
            ui.label(
                f"Last run: {health.last_governance_run}"
            ).classes("text-xs text-gray-400 mt-3")


# -- Page registration ----------------------------------------------------

@ui.page("/")
def dashboard_page():
    """Main PRISM dashboard."""
    create_nav()

    with page_container():
        # -- Pipeline section --
        ui.label("Workflow Pipeline").classes("text-lg font-semibold text-gray-900")
        pipeline_container = ui.row().classes("w-full overflow-x-auto")

        # -- Metrics section --
        ui.label("Metrics").classes("text-lg font-semibold text-gray-900")
        metrics_container = ui.row().classes("w-full flex-wrap gap-4")

        # -- Governance health section --
        with ui.card().classes(
            "w-full bg-white shadow-sm rounded-lg p-5"
        ) as health_wrapper:
            ui.label("Governance Health").classes(
                "text-lg font-semibold text-gray-900 mb-3"
            )
            health_container = ui.column().classes("w-full gap-1")

    # -- Refresh logic -----------------------------------------------------

    def refresh():
        from app.project_context import get_project
        _ctx = get_project(app.storage.user.get('project', 'default'))
        workflow_svc = _ctx.workflow_svc
        governance = _ctx.governance

        steps = workflow_svc.get_steps()
        state = workflow_svc.get_state()
        health = governance.get_health_report()

        _build_pipeline(pipeline_container, steps)
        _build_metrics(metrics_container, state)
        _build_health(health_container, health)

    # Initial render + 2-second auto-refresh
    refresh()
    ui.timer(2.0, refresh)

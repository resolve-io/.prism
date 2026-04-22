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

def _build_pipeline_vertical(container, steps: list[dict]):
    """Compact vertical variant of the pipeline for the dashboard sidebar."""
    container.clear()
    with container:
        for step in steps:
            status = step.get("status", "pending")
            step_type = step.get("type", "agent")
            agent = step.get("agent")

            if status == "completed":
                dot_color = "#10b981"
                badge_cls = "bg-green-100 text-green-800"
                badge = "Done"
            elif status == "current":
                dot_color = "#2563eb"
                badge_cls = "bg-blue-100 text-blue-800"
                badge = "Active"
            elif step_type == "gate":
                dot_color = "#d97706"
                badge_cls = "bg-amber-100 text-amber-800"
                badge = "Gate"
            else:
                dot_color = "#cbd5e1"
                badge_cls = "bg-gray-100 text-gray-500"
                badge = "Pending"

            with ui.row().classes("w-full items-center gap-3 py-1.5"):
                ui.html(
                    f'<div style="width:10px;height:10px;border-radius:50%;'
                    f'background:{dot_color};flex-shrink:0"></div>'
                )
                with ui.column().classes("flex-1 gap-0"):
                    ui.label(_step_display_name(step["id"])).classes(
                        "text-sm font-medium text-gray-900 leading-tight"
                    )
                    if agent:
                        ui.label(_AGENT_LABELS.get(agent, agent.upper())).classes(
                            "text-[10px] text-gray-400 uppercase tracking-wide"
                        )
                ui.html(
                    f'<span class="text-[10px] font-medium px-2 py-0.5 '
                    f'rounded-full {badge_cls}">{badge}</span>'
                )


def _build_kpi_grid(container, kpis: list[dict]):
    """Render a 2-column small KPI grid."""
    container.clear()
    with container:
        with ui.row().classes("w-full flex-wrap gap-2"):
            for k in kpis:
                with ui.card().classes(
                    "flex-1 min-w-[130px] p-3 bg-white shadow-sm rounded-lg "
                    "border border-gray-200"
                ):
                    ui.label(k["label"]).classes(
                        "text-[10px] text-gray-500 uppercase tracking-wide"
                    )
                    ui.label(str(k["value"])).classes(
                        "text-xl font-bold text-gray-900 leading-none mt-1"
                    )
                    if k.get("hint"):
                        ui.label(k["hint"]).classes(
                            "text-[10px] text-gray-400 mt-1"
                        )


def _collect_kpis(proj: str) -> list[dict]:
    """Pull counts from brain/graph/memory/task DBs for the selected project."""
    import sqlite3
    from pathlib import Path as _P
    root = _P(f"/data/projects/{proj}")

    def _one(db: str, sql: str, default=0):
        p = root / db
        if not p.exists():
            return default
        try:
            c = sqlite3.connect(str(p))
            v = c.execute(sql).fetchone()
            c.close()
            return v[0] if v else default
        except Exception:
            return default

    brain_docs   = _one("brain.db", "SELECT COUNT(*) FROM docs")
    entities     = _one("graph.db", "SELECT COUNT(*) FROM entities")
    rels         = _one("graph.db", "SELECT COUNT(*) FROM relationships")
    communities  = _one("graph.db",
                        "SELECT COUNT(DISTINCT community) FROM entities "
                        "WHERE community IS NOT NULL")
    memories     = _one("mulch.db", "SELECT COUNT(*) FROM expertise")
    tasks_active = _one("tasks.db",
                        "SELECT COUNT(*) FROM tasks "
                        "WHERE status IN ('pending','in_progress')")

    return [
        {"label": "Brain docs",   "value": brain_docs},
        {"label": "Entities",     "value": entities},
        {"label": "Relationships","value": rels},
        {"label": "Communities",  "value": communities},
        {"label": "Memories",     "value": memories},
        {"label": "Open tasks",   "value": tasks_active},
    ]


@ui.page("/")
def dashboard_page():
    """Main PRISM dashboard — graph-centric layout."""
    create_nav()

    # Resolve active project (URL param > session > default)
    from nicegui import context as _ctx
    _qs_proj = None
    try:
        _qs_proj = _ctx.client.request.query_params.get('project')
    except Exception:
        pass
    _proj = _qs_proj or app.storage.user.get('project', 'default')
    if _qs_proj:
        app.storage.user['project'] = _qs_proj
    from pathlib import Path as _Path
    _html = _Path(f"/data/projects/{_proj}/graphify-src/graphify-out/graph.html")

    with page_container(wide=True):

        # --- Search bar -------------------------------------------------
        with ui.card().classes("w-full bg-white shadow-sm rounded-lg p-3"):
            with ui.row().classes("w-full items-center gap-3"):
                search_input = ui.input(
                    placeholder="Search concepts in this project (brain_search)…"
                ).props("outlined dense clearable").classes("flex-grow")
                search_btn = ui.button("Search", icon="search").props(
                    "color=primary no-caps"
                )
        search_results = ui.column().classes("w-full gap-2")

        async def do_search():
            query = (search_input.value or "").strip()
            search_results.clear()
            if not query:
                return
            from app.project_context import get_project
            svc = get_project(_proj).brain_svc
            try:
                results = svc.search(query, limit=8)
            except Exception as e:
                with search_results:
                    ui.label(f"error: {e}").classes("text-sm text-red-600")
                return
            with search_results:
                if not results:
                    ui.label("no matches").classes("text-sm text-gray-500")
                    return
                for r in results:
                    did = (r.get("doc_id") or "").removesuffix("::main")
                    score = r.get("rrf_score", r.get("score", 0)) or 0
                    snippet = (r.get("content") or "")[:220].replace("\n", " ")
                    with ui.card().classes(
                        "w-full bg-gray-50 rounded-lg p-3 "
                        "border-l-4 border-blue-400"
                    ):
                        with ui.row().classes("items-center justify-between w-full"):
                            ui.label(did).classes(
                                "text-sm font-mono text-gray-800"
                            )
                            ui.label(f"{float(score):.3f}").classes(
                                "text-xs text-gray-500"
                            )
                        if snippet:
                            ui.label(snippet).classes(
                                "text-xs text-gray-600 mt-1"
                            )

        search_btn.on("click", do_search)
        search_input.on("keydown.enter", do_search)

        # --- Main two-column layout -------------------------------------
        with ui.row().classes("w-full gap-4 items-stretch flex-nowrap"):

            # LEFT: the graph takes ~3/4 of the width
            with ui.column().classes("gap-2").style("flex: 3 1 0; min-width: 0;"):
                with ui.card().classes(
                    "w-full bg-white shadow-sm rounded-lg p-3 flex-grow"
                ).style("min-height: calc(100vh - 220px);"):
                    with ui.row().classes(
                        "w-full items-center justify-between mb-2"
                    ):
                        ui.label("Code Graph").classes(
                            "text-lg font-semibold text-gray-900"
                        )
                        with ui.row().classes("gap-3 items-center"):
                            ui.link("Full page →", f"/graph?project={_proj}").classes(
                                "text-sm text-indigo-600 hover:underline"
                            )
                            if _html.exists():
                                ui.link(
                                    "Open visual ↗",
                                    f"/graphify-visual/{_proj}/graph.html",
                                    new_tab=True,
                                ).classes("text-sm text-indigo-600 hover:underline")
                    if _html.exists():
                        ui.element("iframe").props(
                            f'src="/graphify-visual/{_proj}/graph.html"'
                        ).style(
                            # Header (~56px) + search (~70px) + padding = ~260px.
                            # Floor at 600px on short viewports so sidebar still
                            # has room to scroll.
                            "width: 100%; "
                            "height: max(600px, calc(100vh - 260px)); "
                            "border: 0; border-radius: 6px; "
                            "background: #0f0f1a; display: block;"
                        )
                    else:
                        with ui.column().classes(
                            "w-full h-64 items-center justify-center "
                            "bg-gray-50 rounded-lg border border-dashed border-gray-300"
                        ):
                            ui.icon("hub", size="xl").classes("text-gray-300")
                            ui.label(
                                "No graph yet for this project — "
                                "go to Graph → Rebuild."
                            ).classes("text-sm text-gray-400 mt-1")

            # RIGHT column: KPIs + pipeline + governance
            with ui.column().classes("gap-3").style("flex: 1 1 0; min-width: 260px;"):

                # KPIs
                ui.label("Metrics").classes(
                    "text-sm font-semibold text-gray-700 uppercase tracking-wide"
                )
                kpi_container = ui.column().classes("w-full gap-2")

                # Pipeline
                with ui.card().classes(
                    "w-full bg-white shadow-sm rounded-lg p-4"
                ):
                    with ui.row().classes(
                        "w-full items-center justify-between mb-2"
                    ):
                        ui.label("Workflow").classes(
                            "text-sm font-semibold text-gray-700 "
                            "uppercase tracking-wide"
                        )
                        workflow_status_badge = ui.html("")
                    pipeline_container = ui.column().classes("w-full gap-0")

                # Governance
                with ui.card().classes(
                    "w-full bg-white shadow-sm rounded-lg p-4"
                ):
                    ui.label("Governance").classes(
                        "text-sm font-semibold text-gray-700 "
                        "uppercase tracking-wide mb-2"
                    )
                    health_container = ui.column().classes("w-full gap-1")

    # -- Refresh logic -----------------------------------------------------
    def refresh():
        from app.project_context import get_project
        current_proj = app.storage.user.get('project', 'default')
        _ctx = get_project(current_proj)

        steps = _ctx.workflow_svc.get_steps()
        state = _ctx.workflow_svc.get_state()
        health = _ctx.governance.get_health_report()

        _build_pipeline_vertical(pipeline_container, steps)
        _build_health(health_container, health)
        _build_kpi_grid(kpi_container, _collect_kpis(current_proj))

        # Update workflow status badge
        if state and state.active:
            workflow_status_badge.content = (
                '<span class="text-[10px] font-medium px-2 py-0.5 '
                'rounded-full bg-blue-100 text-blue-800">in progress</span>'
            )
        else:
            workflow_status_badge.content = (
                '<span class="text-[10px] font-medium px-2 py-0.5 '
                'rounded-full bg-gray-100 text-gray-500">idle</span>'
            )

    refresh()
    ui.timer(3.0, refresh)

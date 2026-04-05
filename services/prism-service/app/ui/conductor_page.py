"""Conductor analytics page -- prompt variants, scores, and exploration."""

from nicegui import ui, app

from app.project_context import get_project
from app.ui.components.nav import create_nav, page_container


def _conductor_svc():
    return get_project(app.storage.user.get('project', 'default')).conductor_svc


# -- Helpers ---------------------------------------------------------------

def _format_ts(ts: str) -> str:
    """Format an ISO timestamp to a shorter display form."""
    if not ts:
        return "-"
    return ts[:19].replace("T", " ")


def _has_plotly() -> bool:
    """Check if plotly is available for charting."""
    try:
        import plotly  # noqa: F401
        return True
    except ImportError:
        return False


# -- Section Builders ------------------------------------------------------

def _build_exploration_rate(container):
    """Render the exploration rate display."""
    conductor_svc = _conductor_svc()

    container.clear()
    with container:
        epsilon = conductor_svc.exploration_rate()
        pct = epsilon * 100

        with ui.card().classes(
            'w-full max-w-sm bg-white shadow-sm rounded-lg p-5'
        ):
            ui.label("Exploration Rate").classes(
                'text-lg font-semibold text-gray-900 mb-3'
            )

            with ui.row().classes('items-baseline gap-2 mb-4'):
                ui.label(f"{pct:.1f}%").classes(
                    'text-4xl font-bold text-indigo-600'
                )

            # Progress bar
            with ui.row().classes('w-full items-center gap-3'):
                ui.label("Exploit").classes('text-xs text-gray-500')
                with ui.element('div').classes(
                    'flex-1 h-2.5 bg-gray-100 rounded-full overflow-hidden'
                ):
                    ui.element('div').classes(
                        'h-full bg-indigo-500 rounded-full'
                    ).style(f'width: {pct}%')
                ui.label("Explore").classes('text-xs text-gray-500')

            ui.label(
                "Higher values mean more experimentation with prompt variants"
            ).classes('text-sm text-gray-500 mt-3')


def _build_variants_table(container):
    """Render the prompt variants table with click-to-expand."""
    conductor_svc = _conductor_svc()

    container.clear()
    with container:
        variants = conductor_svc.get_variants()
        scores_list = conductor_svc.get_scores()

        if not variants:
            with ui.card().classes(
                'w-full bg-white shadow-sm rounded-lg p-8 text-center'
            ):
                ui.icon("tune", color="gray").classes("text-4xl mb-3")
                ui.label("No prompt variants yet").classes(
                    "text-base font-medium text-gray-500"
                )
                ui.label(
                    "Variants appear after the Conductor runs agent instructions."
                ).classes("text-sm text-gray-400 mt-1")
            return

        # Build a score lookup: prompt_id -> {avg_score, total_runs}
        score_map = {}
        for s in scores_list:
            pid = s.get("prompt_id", "")
            if pid:
                score_map[pid] = {
                    "avg_score": s.get("avg_score", 0),
                    "total_runs": s.get("total_runs", 0),
                }

        # Build table rows
        rows = []
        for v in variants:
            pid = v.get("prompt_id", v.get("id", ""))
            persona = v.get("persona", "-")
            sc = score_map.get(pid, {})
            rows.append({
                "prompt_id": pid,
                "persona": persona,
                "avg_score": round(sc.get("avg_score", 0), 3),
                "total_runs": sc.get("total_runs", 0),
                "status": v.get("status", "active"),
                "template": v.get("template", v.get("prompt_text", "")),
            })

        columns = [
            {"name": "prompt_id", "label": "Prompt ID", "field": "prompt_id",
             "align": "left", "sortable": True},
            {"name": "persona", "label": "Persona", "field": "persona",
             "align": "left", "sortable": True},
            {"name": "avg_score", "label": "Avg Score", "field": "avg_score",
             "align": "right", "sortable": True},
            {"name": "total_runs", "label": "Total Runs", "field": "total_runs",
             "align": "right", "sortable": True},
            {"name": "status", "label": "Status", "field": "status",
             "align": "center", "sortable": True},
        ]

        table = ui.table(
            columns=columns,
            rows=rows,
            row_key="prompt_id",
            selection="single",
        ).classes('w-full').style(
            'background: white; font-size: 0.875rem;'
        )

        # Detail expansion area
        detail_container = ui.column().classes('w-full mt-3')

        def _on_selection(e):
            detail_container.clear()
            selected = e.selection
            if not selected:
                return
            row = selected[0]
            template_text = row.get("template", "")
            with detail_container:
                with ui.card().classes(
                    'w-full bg-gray-50 shadow-sm rounded-lg p-5'
                ):
                    ui.label(
                        f"Prompt: {row['prompt_id']}"
                    ).classes('text-sm font-semibold text-gray-900 mb-3')
                    if template_text:
                        ui.code(template_text).classes('w-full')
                    else:
                        ui.label("No template text available").classes(
                            'text-sm text-gray-400 italic'
                        )

        table.on('selection', _on_selection)


def _build_score_trends(container):
    """Render score trends -- plotly chart if available, otherwise table."""
    conductor_svc = _conductor_svc()

    container.clear()
    with container:
        outcomes = conductor_svc.get_session_outcomes(limit=200)

        if not outcomes:
            with ui.card().classes(
                'w-full bg-white shadow-sm rounded-lg p-8 text-center'
            ):
                ui.icon("show_chart", color="gray").classes("text-4xl mb-3")
                ui.label("No score data yet").classes(
                    "text-base font-medium text-gray-500"
                )
                ui.label(
                    "Scores appear after agent sessions produce outcomes."
                ).classes("text-sm text-gray-400 mt-1")
            return

        if _has_plotly():
            _build_plotly_trends(outcomes)
        else:
            _build_table_trends(outcomes)


def _build_plotly_trends(outcomes: list[dict]):
    """Render a plotly line chart of scores over time, grouped by persona."""
    import plotly.graph_objects as go

    # Group by persona
    by_persona: dict[str, list] = {}
    for o in reversed(outcomes):  # oldest first
        persona = o.get("persona", "unknown")
        by_persona.setdefault(persona, []).append(o)

    fig = go.Figure()
    for persona, records in by_persona.items():
        dates = [r.get("recorded_at", "")[:10] for r in records]
        scores = [r.get("score", r.get("composite_score", 0)) for r in records]
        fig.add_trace(go.Scatter(
            x=dates, y=scores, mode="lines+markers", name=persona,
        ))

    fig.update_layout(
        template="plotly_white",
        title=dict(text="Score Trends by Persona", font=dict(size=16, color="#111827")),
        xaxis_title="Date",
        yaxis_title="Score",
        height=380,
        margin=dict(l=50, r=20, t=60, b=50),
        legend=dict(orientation="h", y=-0.2),
        font=dict(color="#374151", size=12),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    ui.plotly(fig).classes('w-full')


def _build_table_trends(outcomes: list[dict]):
    """Fallback: render score trends as a simple table."""
    rows = []
    for o in outcomes[:50]:
        rows.append({
            "date": _format_ts(o.get("recorded_at", "")),
            "persona": o.get("persona", "-"),
            "step": o.get("step_id", "-"),
            "score": round(o.get("score", o.get("composite_score", 0)), 3),
            "prompt_id": o.get("prompt_id", "-"),
        })

    columns = [
        {"name": "date", "label": "Date", "field": "date",
         "align": "left", "sortable": True},
        {"name": "persona", "label": "Persona", "field": "persona",
         "align": "left", "sortable": True},
        {"name": "step", "label": "Step", "field": "step",
         "align": "left", "sortable": True},
        {"name": "score", "label": "Score", "field": "score",
         "align": "right", "sortable": True},
        {"name": "prompt_id", "label": "Prompt ID", "field": "prompt_id",
         "align": "left"},
    ]

    ui.table(columns=columns, rows=rows, row_key="date").classes(
        'w-full'
    ).style('background: white; font-size: 0.875rem;')


def _build_retired_table(container):
    """Render the retired variants table."""
    conductor_svc = _conductor_svc()

    container.clear()
    with container:
        retired = conductor_svc.get_retired()

        if not retired:
            with ui.card().classes(
                'w-full bg-white shadow-sm rounded-lg p-6 text-center'
            ):
                ui.icon("delete_sweep", color="gray").classes("text-3xl mb-3")
                ui.label("No retired variants").classes(
                    "text-base font-medium text-gray-500"
                )
                ui.label(
                    "Low-performing variants will appear here after retirement."
                ).classes("text-sm text-gray-400 mt-1")
            return

        rows = []
        for r in retired:
            rows.append({
                "prompt_id": r.get("prompt_id", r.get("id", "-")),
                "persona": r.get("persona", "-"),
                "retired_at": _format_ts(r.get("retired_at", "")),
                "reason": r.get("reason", r.get("retire_reason", "-")),
            })

        columns = [
            {"name": "prompt_id", "label": "Prompt ID", "field": "prompt_id",
             "align": "left", "sortable": True},
            {"name": "persona", "label": "Persona", "field": "persona",
             "align": "left", "sortable": True},
            {"name": "retired_at", "label": "Retired At", "field": "retired_at",
             "align": "left", "sortable": True},
            {"name": "reason", "label": "Reason", "field": "reason",
             "align": "left"},
        ]

        ui.table(columns=columns, rows=rows, row_key="prompt_id").classes(
            'w-full'
        ).style('background: white; font-size: 0.875rem;')


# -- Page registration -----------------------------------------------------

@ui.page('/conductor')
def conductor_page():
    """Conductor analytics -- prompt variants, scores, exploration."""
    ui.colors(primary='#4f46e5')

    create_nav()

    with page_container():
        # Page heading
        ui.label("Conductor Analytics").classes(
            "text-2xl font-semibold text-gray-900"
        )

        # Exploration rate
        with ui.card().classes('w-full bg-white shadow-sm rounded-lg p-5'):
            ui.label("Exploration").classes(
                'text-lg font-semibold text-gray-900 mb-4'
            )
            exploration_container = ui.column().classes('w-full')

        # Prompt variants
        with ui.card().classes('w-full bg-white shadow-sm rounded-lg p-5'):
            ui.label("Prompt Variants").classes(
                'text-lg font-semibold text-gray-900 mb-4'
            )
            variants_container = ui.column().classes('w-full')

        # Score trends
        with ui.card().classes('w-full bg-white shadow-sm rounded-lg p-5'):
            ui.label("Score Trends").classes(
                'text-lg font-semibold text-gray-900 mb-4'
            )
            trends_container = ui.column().classes('w-full')

        # Retired variants
        with ui.card().classes('w-full bg-white shadow-sm rounded-lg p-5'):
            ui.label("Retired Variants").classes(
                'text-lg font-semibold text-gray-900 mb-4'
            )
            retired_container = ui.column().classes('w-full')

    # Refresh logic
    def refresh():
        _build_exploration_rate(exploration_container)
        _build_variants_table(variants_container)
        _build_score_trends(trends_container)
        _build_retired_table(retired_container)

    refresh()
    ui.timer(5.0, refresh)

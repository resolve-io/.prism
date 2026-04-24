"""Sessions history page -- session outcomes, skill usage, and summary stats."""

import json

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

def _build_summary_stats(container, outcomes: list[dict]):
    """Render summary statistic cards."""
    container.clear()
    with container:
        total = len(outcomes)

        # Extract numeric values safely
        tokens_list = []
        durations = []
        for o in outcomes:
            tok = o.get("tokens", o.get("total_tokens", 0))
            if tok:
                try:
                    tokens_list.append(int(tok))
                except (ValueError, TypeError):
                    pass
            dur = o.get("duration", o.get("duration_seconds", 0))
            if dur:
                try:
                    durations.append(float(dur))
                except (ValueError, TypeError):
                    pass

        avg_tokens = (sum(tokens_list) / len(tokens_list)) if tokens_list else 0
        avg_duration = (sum(durations) / len(durations)) if durations else 0

        cards = [
            ("Total Sessions", str(total), "history", "#4f46e5"),
            ("Avg Tokens", f"{avg_tokens:,.0f}", "token", "#7c3aed"),
            ("Avg Duration", f"{avg_duration:.1f}s", "timer", "#0d9488"),
        ]

        with ui.row().classes('w-full gap-5 flex-wrap'):
            for title, value, icon_name, color in cards:
                with ui.card().classes(
                    'flex-1 min-w-[200px] bg-white shadow-sm rounded-lg p-5'
                ):
                    with ui.row().classes('items-center gap-2 mb-3'):
                        ui.icon(icon_name, color=color).classes('text-2xl')
                        ui.label(title).classes(
                            'text-sm text-gray-500 uppercase tracking-wide font-medium'
                        )
                    ui.label(value).classes(
                        'text-2xl font-bold text-gray-900'
                    )


def _build_session_table(container, outcomes: list[dict]):
    """Render the sessions table."""
    container.clear()
    with container:
        if not outcomes:
            # Empty state is also our canary for a broken Stop hook — the
            # dogfood loop was silently dead for a month because this spot
            # just said "No sessions recorded yet." Say what's likely wrong
            # and where to look.
            with ui.card().classes(
                'w-full bg-amber-50 border border-amber-200 '
                'shadow-sm rounded-lg p-6'
            ):
                with ui.row().classes('items-start gap-3'):
                    ui.icon("warning", color="amber").classes("text-3xl")
                    with ui.column().classes('gap-1'):
                        ui.label(
                            "No session_outcomes rows for this project"
                        ).classes(
                            "text-base font-semibold text-amber-900"
                        )
                        ui.label(
                            "If you've been using Claude Code on this project, "
                            "the Stop hook is probably failing."
                        ).classes("text-sm text-amber-800")
                        ui.label("Quick checks:").classes(
                            "text-xs font-semibold text-amber-900 mt-2"
                        )
                        ui.html(
                            "<ul class='list-disc pl-5 text-xs "
                            "text-amber-800 space-y-0.5'>"
                            "<li>Confirm the right project is selected in "
                            "the header — outcomes are scoped per "
                            "<code>?project=</code>.</li>"
                            "<li>Tail <code>.prism/logs/hooks.log</code> "
                            "in your project root for recent hook "
                            "exceptions.</li>"
                            "<li>Make sure "
                            "<code>prism-devtools@prism</code> is on "
                            ">= 3.14.3 (<code>claude plugin update</code>). "
                            "Earlier versions wrote to a local DB that "
                            "nothing reads.</li>"
                            "<li>Smoke-test the MCP directly: "
                            "<code>POST /mcp/?project=&lt;id&gt;</code> "
                            "with <code>record_session_outcome</code> — "
                            "a row should appear here live via SSE.</li>"
                            "</ul>"
                        )
            return

        rows = []
        for o in outcomes:
            session_id = o.get("session_id", o.get("id", "-"))
            rows.append({
                "session_id": (
                    session_id[:12] + "..."
                    if len(str(session_id)) > 12
                    else str(session_id)
                ),
                "session_id_full": str(session_id),
                "date": _format_ts(o.get("recorded_at", o.get("date", ""))),
                "duration": str(
                    o.get("duration", o.get("duration_seconds", "-"))
                ),
                "tokens": str(
                    o.get("tokens", o.get("total_tokens", "-"))
                ),
                "files_modified": str(
                    o.get("files_modified", o.get("files_changed", "-"))
                ),
                "skills_invoked": str(
                    o.get("skills_invoked", o.get("skills_used", "-"))
                ),
            })

        columns = [
            {"name": "session_id", "label": "Session", "field": "session_id",
             "align": "left", "sortable": True},
            {"name": "date", "label": "Date", "field": "date",
             "align": "left", "sortable": True},
            {"name": "duration", "label": "Duration", "field": "duration",
             "align": "right", "sortable": True},
            {"name": "tokens", "label": "Tokens", "field": "tokens",
             "align": "right", "sortable": True},
            {"name": "files_modified", "label": "Files", "field": "files_modified",
             "align": "right", "sortable": True},
            {"name": "skills_invoked", "label": "Skills", "field": "skills_invoked",
             "align": "right", "sortable": True},
        ]

        ui.table(
            columns=columns,
            rows=rows,
            row_key="session_id_full",
        ).classes('w-full').style(
            'background: white; font-size: 0.875rem;'
        )


def _build_skill_usage(container):
    """Render skill usage summary."""
    conductor_svc = _conductor_svc()

    container.clear()
    with container:
        usage = conductor_svc.get_skill_usage()

        if not usage:
            with ui.card().classes(
                'w-full bg-white shadow-sm rounded-lg p-6 text-center'
            ):
                ui.icon("build", color="gray").classes("text-3xl mb-3")
                ui.label("No skill usage data yet").classes(
                    "text-base font-medium text-gray-500"
                )
                ui.label(
                    "Skill usage is tracked when agents invoke skills during sessions."
                ).classes("text-sm text-gray-400 mt-1")
            return

        # Aggregate by skill name
        skill_counts: dict[str, int] = {}
        for u in usage:
            name = u.get("skill_name", u.get("skill", "unknown"))
            skill_counts[name] = skill_counts.get(name, 0) + 1

        # Sort by count descending
        sorted_skills = sorted(
            skill_counts.items(), key=lambda x: x[1], reverse=True
        )

        rows = [
            {"skill": name, "count": count}
            for name, count in sorted_skills
        ]

        columns = [
            {"name": "skill", "label": "Skill", "field": "skill",
             "align": "left", "sortable": True},
            {"name": "count", "label": "Invocations", "field": "count",
             "align": "right", "sortable": True},
        ]

        ui.table(columns=columns, rows=rows, row_key="skill").classes(
            'w-full'
        ).style('background: white; font-size: 0.875rem;')


def _build_trend_chart(container, outcomes: list[dict]):
    """Render session trend chart if plotly is available."""
    container.clear()
    with container:
        if not outcomes:
            return

        if not _has_plotly():
            return

        import plotly.graph_objects as go

        # Group by date and compute daily averages
        daily: dict[str, list] = {}
        for o in reversed(outcomes):
            date_str = (o.get("recorded_at", o.get("date", "")))[:10]
            if not date_str:
                continue
            tok = o.get("tokens", o.get("total_tokens", 0))
            try:
                tok = int(tok)
            except (ValueError, TypeError):
                tok = 0
            daily.setdefault(date_str, []).append(tok)

        if not daily:
            return

        dates = sorted(daily.keys())
        avg_tokens = [sum(daily[d]) / len(daily[d]) for d in dates]
        session_counts = [len(daily[d]) for d in dates]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=dates, y=session_counts, name="Sessions",
            marker_color="rgba(79, 70, 229, 0.5)",
        ))
        fig.add_trace(go.Scatter(
            x=dates, y=avg_tokens, name="Avg Tokens",
            yaxis="y2", mode="lines+markers",
            line=dict(color="#7c3aed", width=2),
            marker=dict(size=6),
        ))

        fig.update_layout(
            template="plotly_white",
            title=dict(
                text="Session Trends",
                font=dict(size=16, color="#111827"),
            ),
            xaxis_title="Date",
            yaxis=dict(title="Sessions", side="left"),
            yaxis2=dict(title="Avg Tokens", side="right", overlaying="y"),
            height=340,
            margin=dict(l=50, r=50, t=60, b=50),
            legend=dict(orientation="h", y=-0.2),
            font=dict(color="#374151", size=12),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        ui.plotly(fig).classes('w-full')


# -- Page registration -----------------------------------------------------

@ui.page('/sessions')
def sessions_page():
    """Session history -- outcomes, skill usage, summary stats."""
    ui.colors(primary='#4f46e5')

    create_nav()

    # SSE push: refresh only when MCP writes a session_outcome / skill_usage
    # event for the active project. No polling, no visible redraws when idle.
    project_id = app.storage.user.get('project', 'default')
    ui.add_head_html(
        '<script>'
        'document.addEventListener("DOMContentLoaded", () => {'
        '  const p = ' + json.dumps(project_id) + ';'
        '  const es = new EventSource('
        '    "/sse/sessions?project=" + encodeURIComponent(p)'
        '  );'
        '  es.onmessage = (ev) => emitEvent("prism_data_changed", ev.data);'
        '});'
        '</script>'
    )

    with page_container():
        # Page heading
        ui.label("Session History").classes(
            "text-2xl font-semibold text-gray-900"
        )

        # Summary stats
        stats_container = ui.column().classes('w-full')

        # Trend chart
        with ui.card().classes('w-full bg-white shadow-sm rounded-lg p-5'):
            ui.label("Trends").classes(
                'text-lg font-semibold text-gray-900 mb-4'
            )
            trend_container = ui.column().classes('w-full')

        # Sessions table
        with ui.card().classes('w-full bg-white shadow-sm rounded-lg p-5'):
            ui.label("Recent Sessions").classes(
                'text-lg font-semibold text-gray-900 mb-4'
            )
            table_container = ui.column().classes('w-full')

        # Skill usage
        with ui.card().classes('w-full bg-white shadow-sm rounded-lg p-5'):
            ui.label("Skill Usage").classes(
                'text-lg font-semibold text-gray-900 mb-4'
            )
            skill_container = ui.column().classes('w-full')

    # Refresh logic — runs on page load and on every SSE event.
    # Signature-skip is belt-and-braces against duplicate event flurries.
    state: dict = {"sig": None}

    def _signature(outcomes: list[dict], skills: list[dict]) -> tuple:
        latest_outcome = outcomes[0].get("recorded_at", "") if outcomes else ""
        latest_skill = skills[0].get("timestamp", "") if skills else ""
        return (len(outcomes), latest_outcome, len(skills), latest_skill)

    def refresh():
        conductor_svc = _conductor_svc()
        outcomes = conductor_svc.get_session_outcomes(limit=50)
        skills = conductor_svc.get_skill_usage()

        sig = _signature(outcomes, skills)
        if sig == state["sig"]:
            return
        state["sig"] = sig

        _build_summary_stats(stats_container, outcomes)
        _build_trend_chart(trend_container, outcomes)
        _build_session_table(table_container, outcomes)
        _build_skill_usage(skill_container)

    refresh()
    ui.on('prism_data_changed', lambda _e: refresh())

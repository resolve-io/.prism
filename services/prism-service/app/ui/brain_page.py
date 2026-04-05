"""Brain search page -- hybrid search over the PRISM knowledge base."""

from nicegui import ui, app

from app.project_context import get_project


def _brain_svc():
    return get_project(app.storage.user.get('project', 'default')).brain_svc
from app.ui.components.nav import create_nav, page_container


@ui.page("/brain")
def brain_page():
    create_nav()

    # --- State ---
    selected_domain = {"value": None}

    with page_container():
        ui.label("Brain -- Knowledge Search").classes(
            "text-2xl font-semibold text-gray-900"
        )

        # --- Search bar ---
        with ui.card().classes("w-full bg-white shadow-sm rounded-lg p-5"):
            ui.label("Search").classes("text-sm font-medium text-gray-700 mb-2")
            with ui.row().classes("w-full items-end gap-3"):
                query_input = (
                    ui.input(placeholder="Search the knowledge base...")
                    .classes("flex-grow")
                    .props("outlined dense clearable")
                )
                search_btn = ui.button("Search", icon="search").props(
                    "color=primary no-caps"
                )

            # --- Domain filter chips ---
            ui.label("Domain filter").classes(
                "text-xs font-medium text-gray-500 uppercase tracking-wide mt-4 mb-1"
            )
            domain_options = ["all", "py", "ts", "js", "md", "expertise"]

            _CHIP_COLORS = {
                "all": ("bg-blue-100 text-blue-800", "bg-blue-50 text-blue-600"),
                "py": ("bg-green-100 text-green-800", "bg-green-50 text-green-600"),
                "ts": ("bg-sky-100 text-sky-800", "bg-sky-50 text-sky-600"),
                "js": ("bg-amber-100 text-amber-800", "bg-amber-50 text-amber-600"),
                "md": ("bg-purple-100 text-purple-800", "bg-purple-50 text-purple-600"),
                "expertise": ("bg-rose-100 text-rose-800", "bg-rose-50 text-rose-600"),
            }

            with ui.row().classes("gap-2 flex-wrap"):
                domain_chips: dict[str, ui.button] = {}
                for d in domain_options:
                    sel_cls, _ = _CHIP_COLORS.get(d, ("bg-gray-200 text-gray-800", "bg-gray-100 text-gray-500"))
                    btn = ui.button(d).props("no-caps unelevated size=sm").classes(
                        f"px-3 py-1 rounded-full text-xs font-medium {sel_cls if d == 'all' else 'bg-gray-100 text-gray-500'}"
                    )
                    domain_chips[d] = btn

            def on_domain_select(name: str):
                selected_domain["value"] = None if name == "all" else name
                for d, btn in domain_chips.items():
                    sel_cls, unsel_cls = _CHIP_COLORS.get(d, ("bg-gray-200 text-gray-800", "bg-gray-100 text-gray-500"))
                    if d == name:
                        btn.classes(replace=f"px-3 py-1 rounded-full text-xs font-medium {sel_cls}")
                    else:
                        btn.classes(replace=f"px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-500")

            for d in domain_options:
                domain_chips[d].on("click", lambda _, d=d: on_domain_select(d))

        # --- Results container ---
        results_container = ui.column().classes("w-full gap-4")

        # --- Search handler ---
        async def do_search():
            query = query_input.value
            if not query or not query.strip():
                ui.notify("Enter a search query", type="warning")
                return

            results_container.clear()
            with results_container:
                ui.spinner("dots", size="lg").classes("self-center my-6")

            try:
                domain = selected_domain["value"]
                results = _brain_svc().search(
                    query.strip(), domain=domain, limit=20
                )
            except Exception as exc:
                results_container.clear()
                with results_container:
                    with ui.card().classes("w-full bg-red-50 border border-red-200 rounded-lg p-4"):
                        ui.label(f"Search error: {exc}").classes("text-sm text-red-700")
                return

            results_container.clear()

            if not results:
                with results_container:
                    with ui.card().classes("w-full bg-gray-50 rounded-lg p-8 text-center"):
                        ui.icon("search_off", color="#9ca3af").classes("text-4xl")
                        ui.label("No results found.").classes(
                            "text-gray-500 mt-2"
                        )
                return

            # Build results table
            columns = [
                {
                    "name": "rank",
                    "label": "#",
                    "field": "rank",
                    "align": "center",
                    "sortable": True,
                    "style": "width: 50px",
                },
                {
                    "name": "score",
                    "label": "Score",
                    "field": "score",
                    "align": "center",
                    "sortable": True,
                    "style": "width: 80px",
                },
                {
                    "name": "entity_name",
                    "label": "Entity",
                    "field": "entity_name",
                    "sortable": True,
                },
                {
                    "name": "entity_kind",
                    "label": "Kind",
                    "field": "entity_kind",
                    "sortable": True,
                    "style": "width: 100px",
                },
                {
                    "name": "domain",
                    "label": "Domain",
                    "field": "domain",
                    "sortable": True,
                    "style": "width: 90px",
                },
                {
                    "name": "file",
                    "label": "File",
                    "field": "file",
                    "sortable": True,
                },
            ]

            rows = []
            for i, r in enumerate(results, 1):
                score_val = r.get("rrf_score", r.get("score", 0))
                rows.append(
                    {
                        "rank": i,
                        "score": f"{float(score_val):.3f}" if score_val else "\u2014",
                        "entity_name": r.get("entity_name", r.get("name", "\u2014")),
                        "entity_kind": r.get("entity_kind", r.get("kind", "\u2014")),
                        "domain": r.get("domain", "\u2014"),
                        "file": r.get("file", r.get("source", "\u2014")),
                        "_raw": r,
                    }
                )

            with results_container:
                ui.label(f"{len(results)} results").classes(
                    "text-sm text-gray-500"
                )

                with ui.card().classes("w-full bg-white shadow-sm rounded-lg overflow-hidden"):
                    table = ui.table(
                        columns=columns,
                        rows=rows,
                        row_key="rank",
                        pagination={"rowsPerPage": 10},
                    ).classes("w-full")
                    table.props("flat dense separator=horizontal")
                    # Alternating row colours via slot override
                    table.add_slot(
                        "body",
                        r'''
                        <q-tr :props="props"
                              :class="props.rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'"
                              @click="$parent.$emit('rowClick', $event, props.row, props.rowIndex)"
                              class="cursor-pointer hover:bg-blue-50 transition-colors">
                            <q-td v-for="col in props.cols" :key="col.name" :props="props"
                                  class="text-sm text-gray-700">
                                {{ col.value }}
                            </q-td>
                        </q-tr>
                        ''',
                    )

                # --- Expandable detail on row click ---
                detail_container = ui.column().classes("w-full")

                def show_detail(e):
                    detail_container.clear()
                    row = e.args if isinstance(e.args, dict) else {}
                    raw = row.get("_raw", row)
                    with detail_container:
                        with ui.card().classes(
                            "w-full bg-white shadow-sm rounded-lg border-l-4 border-blue-400 p-5"
                        ):
                            ui.label(
                                raw.get("entity_name", raw.get("name", "Detail"))
                            ).classes("text-lg font-semibold text-gray-900")

                            with ui.row().classes("gap-6 mt-2"):
                                for lbl, val in [
                                    ("Kind", raw.get("entity_kind", raw.get("kind", "\u2014"))),
                                    ("Domain", raw.get("domain", "\u2014")),
                                    ("File", raw.get("file", raw.get("source", "\u2014"))),
                                ]:
                                    with ui.column().classes("gap-0"):
                                        ui.label(lbl).classes(
                                            "text-xs text-gray-400 uppercase tracking-wide"
                                        )
                                        ui.label(str(val)).classes("text-sm text-gray-700")

                            content = raw.get("content", raw.get("description", ""))
                            if content:
                                ui.separator().classes("my-3")
                                ui.label("Content").classes(
                                    "text-sm font-medium text-gray-700 mb-1"
                                )
                                ui.code(str(content)).classes(
                                    "w-full max-h-64 overflow-auto"
                                )

                table.on("rowClick", show_detail)

        search_btn.on("click", do_search)
        query_input.on("keydown.enter", do_search)

        # --- Status card ---
        with ui.card().classes("w-full bg-white shadow-sm rounded-lg p-5"):
            ui.label("Brain Status").classes(
                "text-lg font-semibold text-gray-900 mb-4"
            )

            status = _brain_svc().status()
            with ui.row().classes("gap-8 flex-wrap"):
                # Documents
                with ui.column().classes("items-center gap-1"):
                    ui.label(str(status.get("doc_count", 0))).classes(
                        "text-3xl font-bold text-gray-900"
                    )
                    ui.label("Documents").classes("text-xs text-gray-500 uppercase tracking-wide")

                # Entities
                with ui.column().classes("items-center gap-1"):
                    ui.label(str(status.get("entity_count", 0))).classes(
                        "text-3xl font-bold text-gray-900"
                    )
                    ui.label("Entities").classes("text-xs text-gray-500 uppercase tracking-wide")

                # Vectors
                with ui.column().classes("items-center gap-1"):
                    vec = status.get("vector_enabled", False)
                    if vec:
                        ui.html(
                            '<span class="text-xs font-medium px-2.5 py-1 rounded-full '
                            'bg-green-100 text-green-800">Enabled</span>'
                        )
                    else:
                        ui.html(
                            '<span class="text-xs font-medium px-2.5 py-1 rounded-full '
                            'bg-red-100 text-red-800">Disabled</span>'
                        )
                    ui.label("Vectors").classes("text-xs text-gray-500 uppercase tracking-wide")

                # Last Reindex
                with ui.column().classes("items-center gap-1"):
                    last = status.get("last_reindex", "\u2014") or "\u2014"
                    ui.label(str(last)[:19]).classes(
                        "text-sm font-mono text-gray-700"
                    )
                    ui.label("Last Reindex").classes("text-xs text-gray-500 uppercase tracking-wide")

            ui.separator().classes("my-4")

            async def do_reindex():
                reindex_btn.disable()
                ui.notify("Reindexing...", type="info")
                try:
                    count = _brain_svc().incremental_reindex()
                    ui.notify(
                        f"Reindex complete: {count} documents updated",
                        type="positive",
                    )
                except Exception as exc:
                    ui.notify(f"Reindex failed: {exc}", type="negative")
                finally:
                    reindex_btn.enable()

            reindex_btn = ui.button("Reindex", icon="refresh").props(
                "color=primary no-caps"
            )
            reindex_btn.on("click", do_reindex)

        # --- Entity graph placeholder ---
        with ui.card().classes(
            "w-full bg-white shadow-sm rounded-lg p-5"
        ):
            ui.label("Entity Graph").classes(
                "text-lg font-semibold text-gray-900 mb-4"
            )
            with ui.column().classes(
                "w-full h-40 items-center justify-center bg-gray-50 rounded-lg border border-dashed border-gray-300"
            ):
                ui.icon("hub", size="xl").classes("text-gray-300")
                ui.label("Entity graph coming soon").classes(
                    "text-sm text-gray-400 mt-1"
                )

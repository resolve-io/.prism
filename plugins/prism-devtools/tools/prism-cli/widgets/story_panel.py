"""StoryPanel — AC list, plan coverage summary."""

from __future__ import annotations

from textual.widgets import Static

from models import StoryInfo


class StoryPanel(Static):
    """Displays story file info: path, ACs, plan coverage."""

    DEFAULT_CSS = """
    StoryPanel {
        height: auto;
        min-height: 6;
        padding: 1;
        border: round $primary;
    }
    """

    def on_mount(self) -> None:
        self._refresh_content(None)

    def update_story(self, story: StoryInfo | None) -> None:
        self._refresh_content(story)

    @staticmethod
    def _render_bar(passing: int, total: int, width: int = 20) -> str:
        """Render a unicode fill bar: [████████░░░░] 6/10"""
        if total == 0:
            empty_bar = "\u2591" * width
            return f"[dim][[/][dim]{empty_bar}[/][dim]][/] [dim]no tests[/]"
        filled = round((passing / total) * width)
        filled = max(0, min(filled, width))
        empty = width - filled
        bar_filled = "\u2588" * filled
        bar_empty = "\u2591" * empty
        pct = int((passing / total) * 100)
        if passing == total:
            color = "green"
        elif passing > 0:
            color = "yellow"
        else:
            color = "red"
        return (
            f"[dim][[/][{color}]{bar_filled}[/][dim]{bar_empty}[/][dim]][/] "
            f"[{color}]{passing}/{total}[/] [dim]({pct}%)[/]"
        )

    def _refresh_content(self, story: StoryInfo | None) -> None:
        if not story or not story.exists:
            self.update("[bold]Story File[/]\n[dim]No story file[/]")
            return

        lines = ["[bold]Story File[/]"]
        lines.append(f"[dim]{story.path}[/]")

        # Green test progress bar
        progress_bar = self._render_bar(story.green_tests_passing, story.green_tests_total)
        lines.append(f"[bold]Green[/] {progress_bar}")

        # ACs
        ac_count = len(story.acceptance_criteria)
        lines.append(f"ACs: {ac_count} found")
        for ac in story.acceptance_criteria[:8]:
            display = ac if len(ac) <= 50 else ac[:47] + "..."
            lines.append(f"  {display}")
        if ac_count > 8:
            lines.append(f"  [dim]... and {ac_count - 8} more[/]")

        # Plan coverage
        if story.has_plan_coverage:
            covered = story.covered_count
            missing = story.missing_count
            if missing > 0:
                cov_str = f"[green]{covered} covered[/], [red]{missing} missing[/]"
            else:
                cov_str = f"[green]{covered} covered[/], 0 missing"
            lines.append(f"Coverage: {cov_str}")
        else:
            lines.append("[dim]No plan coverage section[/]")

        self.update("\n".join(lines))

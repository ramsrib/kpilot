from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static, Input
from textual.message import Message as TextualMessage

RESOURCE_TYPES = ["Pods", "Services", "Deployments", "Namespaces", "Nodes"]


class ResourceTypeChanged(TextualMessage):
    """Posted when the resource type tab changes."""

    def __init__(self, index: int, name: str) -> None:
        super().__init__()
        self.index = index
        self.name = name


class ResourcePanel(Vertical):
    """Left panel: resource type tabs + data table + filter."""

    def __init__(self) -> None:
        super().__init__(id="resource-panel")
        self.border_title = "Resources"
        self._current_type = 0
        self._filter = ""

    def compose(self) -> ComposeResult:
        yield Static("", id="resource-tabs")
        yield DataTable(id="resource-table")
        yield Input(placeholder="/filter...", id="filter-input")

    def on_mount(self) -> None:
        table = self.query_one("#resource-table", DataTable)
        table.cursor_type = "row"
        self._render_tabs()

    def set_resource_type(self, index: int) -> None:
        if 0 <= index < len(RESOURCE_TYPES):
            self._current_type = index
            self._render_tabs()
            self.post_message(
                ResourceTypeChanged(index, RESOURCE_TYPES[index])
            )

    @property
    def current_type(self) -> int:
        return self._current_type

    @property
    def current_type_name(self) -> str:
        return RESOURCE_TYPES[self._current_type]

    def set_filter(self, f: str) -> None:
        self._filter = f.lower()

    def update_data(
        self, headers: list[str], rows: list[list[str]]
    ) -> None:
        table = self.query_one("#resource-table", DataTable)
        table.clear(columns=True)
        for h in headers:
            table.add_column(h, key=h)
        for row in rows:
            if self._filter:
                if not any(self._filter in cell.lower() for cell in row):
                    continue
            table.add_row(*row)

    def _render_tabs(self) -> None:
        tabs = self.query_one("#resource-tabs", Static)
        parts = []
        for i, name in enumerate(RESOURCE_TYPES):
            if i == self._current_type:
                parts.append(f"[rgb(127,255,212) bold]<{name}>[/]")
            else:
                parts.append(f"[white]{name}[/]")
        tabs.update(" " + " | ".join(parts))

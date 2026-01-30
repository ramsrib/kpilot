from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable
from textual.message import Message as TextualMessage

# k9s-style resource aliases
RESOURCE_TYPES = {
    0: "Pods",
    1: "Services",
    2: "Deployments",
    3: "Namespaces",
    4: "Nodes",
    5: "ConfigMaps",
    6: "Secrets",
    7: "PersistentVolumeClaims",
    8: "Events",
}


class ResourceTypeChanged(TextualMessage):
    """Posted when the resource type changes."""

    def __init__(self, index: int, name: str) -> None:
        super().__init__()
        self.index = index
        self.name = name


class ResourcePanel(Vertical):
    """Main resource table panel — full-width like k9s."""

    def __init__(self) -> None:
        super().__init__(id="resource-panel")
        self._current_type = 0
        self._filter = ""

    def compose(self) -> ComposeResult:
        yield DataTable(id="resource-table")

    def on_mount(self) -> None:
        table = self.query_one("#resource-table", DataTable)
        table.cursor_type = "row"

    def set_resource_type(self, index: int) -> None:
        if index in RESOURCE_TYPES:
            self._current_type = index
            self.post_message(
                ResourceTypeChanged(index, RESOURCE_TYPES[index])
            )

    @property
    def current_type(self) -> int:
        return self._current_type

    @property
    def current_type_name(self) -> str:
        return RESOURCE_TYPES.get(self._current_type, "Unknown")

    def set_filter(self, f: str) -> None:
        self._filter = f.lower()

    def clear_filter(self) -> None:
        self._filter = ""

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

    def get_selected_row(self) -> list[str] | None:
        """Return the currently highlighted row data."""
        table = self.query_one("#resource-table", DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            row = table.get_row(row_key)
            return [str(cell) for cell in row]
        except Exception:
            return None

    def get_selected_name(self) -> str | None:
        """Return the name (first column) of the selected resource."""
        row = self.get_selected_row()
        return row[0] if row else None

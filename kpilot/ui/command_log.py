from __future__ import annotations

from datetime import datetime

from textual.widgets import RichLog


class CommandLog(RichLog):
    """Bottom panel: timestamped command/action log."""

    def __init__(self) -> None:
        super().__init__(id="command-log", markup=True, wrap=True, max_lines=200)
        self.border_title = "Command Log"

    def log_tool(self, name: str, detail: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.write(
            f"[dim]{ts}[/] [rgb(255,165,0)]\\[TOOL][/] {name} {detail}"
        )

    def log_ok(self, name: str, detail: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.write(f"[dim]{ts}[/] [green]\\[OK  ][/] {name} -> {detail}")

    def log_error(self, name: str, detail: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.write(f"[dim]{ts}[/] [red]\\[ERR ][/] {name} -> {detail}")

    def log_info(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.write(f"[dim]{ts}[/] [white]\\[INFO][/] {msg}")

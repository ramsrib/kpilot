from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import RichLog, Input
from textual.message import Message as TextualMessage


class CopilotSubmitted(TextualMessage):
    """Posted when user submits a copilot prompt."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


class CopilotPanel(Vertical):
    """Toggleable copilot panel — k8s AI assistant."""

    def __init__(self) -> None:
        super().__init__(id="copilot-panel")
        self.border_title = "Copilot"

    def compose(self) -> ComposeResult:
        yield RichLog(id="copilot-log", markup=True, wrap=True)
        yield Input(placeholder="Ask about your cluster...", id="copilot-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "copilot-input" and event.value.strip():
            text = event.value.strip()
            event.input.value = ""
            self.post_message(CopilotSubmitted(text))

    def add_user_message(self, text: str) -> None:
        log = self.query_one("#copilot-log", RichLog)
        log.write(f"[bold #d7af00]>[/] {text}")
        log.write("")

    def add_assistant_text(self, text: str) -> None:
        log = self.query_one("#copilot-log", RichLog)
        log.write(f"[#00d7af]{text}[/]")

    def add_tool_call(self, tool_name: str, tool_input: str) -> None:
        log = self.query_one("#copilot-log", RichLog)
        log.write(f"  [bold #ff8700]$ {tool_name}[/]")
        lines = tool_input.strip().split("\n")
        preview = lines[0][:120] if lines else ""
        if len(lines) > 1 or (lines and len(preview) < len(lines[0])):
            preview += "..."
        if preview:
            log.write(f"    [dim]{preview}[/]")

    def add_tool_result(self, text: str, is_error: bool = False) -> None:
        log = self.query_one("#copilot-log", RichLog)
        if is_error:
            log.write(f"  [bold red]err:[/] [red]{_truncate(text, 200)}[/]")
        else:
            truncated = _truncate(text, 300)
            log.write(f"  [dim]{truncated}[/]")

    def add_error(self, text: str) -> None:
        log = self.query_one("#copilot-log", RichLog)
        log.write(f"[bold red]error:[/] [red]{text}[/]")

    def add_separator(self) -> None:
        log = self.query_one("#copilot-log", RichLog)
        log.write("[dim]" + "─" * 40 + "[/]")

    def add_status(self, text: str) -> None:
        log = self.query_one("#copilot-log", RichLog)
        log.write(f"[dim italic]{text}[/]")

    def focus_input(self) -> None:
        self.query_one("#copilot-input", Input).focus()


def _truncate(text: str, max_len: int) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text

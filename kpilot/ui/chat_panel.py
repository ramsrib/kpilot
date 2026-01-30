from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import RichLog, Input
from textual.message import Message as TextualMessage


class ChatSubmitted(TextualMessage):
    """Posted when user submits a chat message."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


class ChatPanel(Vertical):
    """Right panel: chat history + input field."""

    def __init__(self) -> None:
        super().__init__(id="chat-panel")
        self.border_title = "Claude Chat"

    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-log", markup=True, wrap=True)
        yield Input(placeholder="Ask Claude...", id="chat-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input" and event.value.strip():
            text = event.value.strip()
            event.input.value = ""
            self.post_message(ChatSubmitted(text))

    def add_user_message(self, text: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[bold rgb(173,255,47)]You:[/] {text}")
        log.write("")

    def add_assistant_text(self, text: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[rgb(127,255,212)]{text}[/]")

    def add_tool_call(self, tool_name: str, tool_input: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write(f"  [bold rgb(255,165,0)]> Tool:[/] [rgb(255,165,0)]{tool_name}[/]")
        # Show a compact version of the input
        lines = tool_input.strip().split("\n")
        preview = lines[0][:120] if lines else ""
        if len(lines) > 1 or len(preview) < len(lines[0]) if lines else False:
            preview += "..."
        if preview:
            log.write(f"    [dim]{preview}[/]")

    def add_tool_result(self, text: str, is_error: bool = False) -> None:
        log = self.query_one("#chat-log", RichLog)
        if is_error:
            log.write(f"  [bold red]> Error:[/] [red]{_truncate(text, 200)}[/]")
        else:
            truncated = _truncate(text, 300)
            log.write(f"  [dim]> Result: {truncated}[/]")

    def add_error(self, text: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[bold red]Error:[/] [red]{text}[/]")

    def add_separator(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write("[dim]" + "─" * 40 + "[/]")

    def add_status(self, text: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[dim italic]{text}[/]")

    def focus_input(self) -> None:
        self.query_one("#chat-input", Input).focus()


def _truncate(text: str, max_len: int) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text

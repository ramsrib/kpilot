from __future__ import annotations

from textual.widgets import Static


class Header(Static):
    """Top bar showing cluster info and keybinding hints."""

    def __init__(
        self,
        cluster: str = "",
        context: str = "",
        namespace: str = "default",
    ) -> None:
        self.cluster = cluster
        self.context = context
        self.namespace = namespace
        super().__init__("", id="header")

    def render(self) -> str:
        return (
            f" [bold]kpilot[/]  |  "
            f"cluster: [rgb(127,255,212)]{self.cluster}[/]  |  "
            f"ctx: [rgb(127,255,212)]{self.context}[/]  |  "
            f"ns: [rgb(127,255,212)]{self.namespace}[/]  |  "
            f"[dim]1-5=resource  c=chat  :=cmd  /=filter  ?=help  q=quit[/]"
        )

    def set_namespace(self, ns: str) -> None:
        self.namespace = ns
        self.refresh()

    def refresh_header(self) -> None:
        self.refresh()

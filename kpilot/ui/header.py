from __future__ import annotations

from textual.widgets import Static


class HeaderBar(Static):
    """Top bar: k9s-style cluster/context info."""

    def __init__(
        self,
        cluster: str = "",
        context: str = "",
        namespace: str = "default",
        k8s_version: str = "",
    ) -> None:
        self.cluster = cluster
        self.context = context
        self.namespace = namespace
        self.k8s_version = k8s_version
        super().__init__("", id="header-bar")

    def render(self) -> str:
        parts = [" [bold #00d7af]kpilot[/]"]
        if self.context:
            parts.append(f"ctx: [#d7af00]{self.context}[/]")
        if self.cluster:
            parts.append(f"cluster: [#d7af00]{self.cluster}[/]")
        if self.k8s_version:
            parts.append(f"k8s: [#d7af00]{self.k8s_version}[/]")
        return "  ".join(parts)

    def refresh_header(self) -> None:
        self.refresh()


class CrumbBar(Static):
    """Breadcrumb bar: shows current resource view like k9s."""

    def __init__(self) -> None:
        self._resource = "Pods"
        self._namespace = "default"
        self._filter = ""
        self._copilot_active = False
        super().__init__("", id="crumb-bar")

    def render(self) -> str:
        crumb = f" [bold #00d7af]{self._resource}[/][dim]({self._namespace})[/]"
        hints = []
        if self._filter:
            crumb += f"  [dim italic]/[/][#d7af00]{self._filter}[/]"
        if self._copilot_active:
            hints.append("[#00d7af]c[/]:copilot")
        hints.extend([
            "[dim]?[/]:help",
            "[dim]:[/]:cmd",
            "[dim]/[/]:filter",
            "[dim]<esc>[/]:back",
        ])
        right = "  ".join(hints)
        return crumb + "  " + right

    def set_view(self, resource: str, namespace: str) -> None:
        self._resource = resource
        self._namespace = namespace
        self.refresh()

    def set_filter(self, f: str) -> None:
        self._filter = f
        self.refresh()

    def set_copilot_active(self, active: bool) -> None:
        self._copilot_active = active
        self.refresh()

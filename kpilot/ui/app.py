from __future__ import annotations

import subprocess
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Static, Input, DataTable

from kpilot.config import Config
from kpilot.kube.client import KubeClient
from kpilot.agent.loop import AgentLoop, AgentEvent
from kpilot.ui.theme import APP_CSS
from kpilot.ui.header import HeaderBar, CrumbBar
from kpilot.ui.resource_panel import ResourcePanel, ResourceTypeChanged
from kpilot.ui.chat_panel import CopilotPanel, CopilotSubmitted
from kpilot.ui.command_log import CommandLog

# Maps resource panel index -> kube client method
RESOURCE_FETCH = {
    0: "list_pods",
    1: "list_services",
    2: "list_deployments",
    3: "list_namespaces",
    4: "list_nodes",
    5: "list_configmaps",
    6: "list_secrets",
    7: "list_pvcs",
    8: "list_events",
}

# k9s-style command aliases -> resource index
COMMAND_ALIASES: dict[str, int] = {
    "pod": 0, "pods": 0, "po": 0,
    "svc": 1, "service": 1, "services": 1,
    "deploy": 2, "deployment": 2, "deployments": 2, "dp": 2,
    "namespace": 3, "namespaces": 3,
    "node": 4, "nodes": 4, "no": 4,
    "cm": 5, "configmap": 5, "configmaps": 5,
    "sec": 6, "secret": 6, "secrets": 6,
    "pvc": 7, "persistentvolumeclaim": 7, "persistentvolumeclaims": 7,
    "ev": 8, "event": 8, "events": 8,
}


class KPilotApp(App):
    """Kubernetes TUI with AI Copilot — k9s-style interface."""

    CSS = APP_CSS

    BINDINGS: ClassVar[list[Binding]] = [
        # k9s-style navigation
        Binding("colon", "command_mode", "Command", show=False),
        Binding("slash", "filter_mode", "Filter", show=False),
        Binding("question_mark", "toggle_help", "Help", show=False),
        Binding("escape", "go_back", "Back", show=False),
        # Copilot toggle
        Binding("c", "toggle_copilot", "Copilot", show=False),
        # Resource actions (k9s-style)
        Binding("d", "describe", "Describe", show=False),
        Binding("y", "yaml", "YAML", show=False),
        Binding("l", "logs", "Logs", show=False),
        Binding("s", "shell", "Shell", show=False),
        # Quit
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.kube = KubeClient(config.kubeconfig, config.namespace)
        self.agent = AgentLoop(model=config.model if config.model else None)
        self._agent_running = False
        self._current_tool_name = ""
        self._copilot_visible = False

    def compose(self) -> ComposeResult:
        yield HeaderBar()
        yield CrumbBar()
        with Horizontal(id="main-container"):
            yield ResourcePanel()
            yield CopilotPanel()
        yield CommandLog()
        yield Input(placeholder="", id="filter-bar")
        yield Input(placeholder="", id="command-bar")
        yield Static("", id="help-modal")

    def on_mount(self) -> None:
        self.kube.connect()

        # Update header with real cluster info
        header = self.query_one(HeaderBar)
        header.cluster = self.kube.info.cluster_name
        header.context = self.kube.info.context_name
        header.k8s_version = self._get_k8s_version()
        header.refresh_header()

        # Configure agent
        self.agent.cluster_name = self.kube.info.cluster_name
        self.agent.context_name = self.kube.info.context_name
        self.agent.namespace = self.kube.namespace

        # Update breadcrumb
        crumb = self.query_one(CrumbBar)
        crumb.set_view("Pods", self.kube.namespace)

        # Log startup
        cmd_log = self.query_one(CommandLog)
        if self.kube.connected:
            cmd_log.log_info(
                f"Connected: {self.kube.info.context_name}"
                f" ({self.kube.info.cluster_name})"
            )
        else:
            cmd_log.log_error("kube", "Not connected to any cluster")

        # Initial data + periodic refresh
        self._refresh_resources()
        self.set_interval(5.0, self._refresh_resources)
        self._focus_table()

    # ── Actions (k9s-style) ─────────────────────────────────────

    def action_command_mode(self) -> None:
        cmd_bar = self.query_one("#command-bar", Input)
        cmd_bar.add_class("visible")
        cmd_bar.value = ":"
        cmd_bar.placeholder = ""
        cmd_bar.focus()

    def action_filter_mode(self) -> None:
        filter_bar = self.query_one("#filter-bar", Input)
        filter_bar.add_class("visible")
        filter_bar.value = "/"
        filter_bar.placeholder = ""
        filter_bar.focus()

    def action_go_back(self) -> None:
        """Esc: close overlays, clear filter, or unfocus copilot."""
        # Close filter/command bars
        self.query_one("#filter-bar", Input).remove_class("visible")
        self.query_one("#command-bar", Input).remove_class("visible")
        self.query_one("#help-modal", Static).remove_class("visible")

        # Clear filter
        panel = self.query_one(ResourcePanel)
        if panel._filter:
            panel.clear_filter()
            self.query_one(CrumbBar).set_filter("")
            self._refresh_resources()

        self._focus_table()

    def action_toggle_copilot(self) -> None:
        copilot = self.query_one(CopilotPanel)
        self._copilot_visible = not self._copilot_visible
        if self._copilot_visible:
            copilot.add_class("visible")
            copilot.focus_input()
            self.query_one(CrumbBar).set_copilot_active(True)
        else:
            copilot.remove_class("visible")
            self.query_one(CrumbBar).set_copilot_active(False)
            self._focus_table()

    def action_toggle_help(self) -> None:
        modal = self.query_one("#help-modal", Static)
        if modal.has_class("visible"):
            modal.remove_class("visible")
            self._focus_table()
        else:
            modal.update(self._build_help_text())
            modal.add_class("visible")
            modal.focus()

    def action_describe(self) -> None:
        """d: describe selected resource via copilot."""
        self._ask_copilot_about_selected("describe")

    def action_yaml(self) -> None:
        """y: show YAML of selected resource via copilot."""
        self._ask_copilot_about_selected("yaml")

    def action_logs(self) -> None:
        """l: show logs of selected pod via copilot."""
        self._ask_copilot_about_selected("logs")

    def action_shell(self) -> None:
        """s: exec into selected pod via copilot."""
        self._ask_copilot_about_selected("shell")

    def action_quit(self) -> None:
        self.agent.cancel()
        self.exit()

    # ── Event handlers ──────────────────────────────────────────

    def on_resource_type_changed(self, event: ResourceTypeChanged) -> None:
        crumb = self.query_one(CrumbBar)
        crumb.set_view(event.name, self.kube.namespace)
        self._refresh_resources()

    def on_copilot_submitted(self, event: CopilotSubmitted) -> None:
        if self._agent_running:
            return
        self._run_agent(event.text)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "command-bar":
            event.input.remove_class("visible")
            cmd = event.value.strip().lstrip(":")
            self._handle_command(cmd)
            self._focus_table()
        elif event.input.id == "filter-bar":
            event.input.remove_class("visible")
            filt = event.value.strip().lstrip("/")
            panel = self.query_one(ResourcePanel)
            panel.set_filter(filt)
            self.query_one(CrumbBar).set_filter(filt)
            self._refresh_resources()
            self._focus_table()

    # ── Internal ────────────────────────────────────────────────

    def _focus_table(self) -> None:
        try:
            self.query_one("#resource-table", DataTable).focus()
        except Exception:
            pass

    def _get_k8s_version(self) -> str:
        if not self.kube.connected:
            return ""
        try:
            v = self.kube._core.api_client.call_api(
                "/version", "GET", response_type="object"
            )
            return v[0].get("gitVersion", "") if isinstance(v[0], dict) else ""
        except Exception:
            return ""

    def _refresh_resources(self) -> None:
        panel = self.query_one(ResourcePanel)
        rt = panel.current_type
        method_name = RESOURCE_FETCH.get(rt)
        if not method_name or not self.kube.connected:
            return
        try:
            method = getattr(self.kube, method_name)
            headers, rows = method()
            panel.update_data(headers, rows)
        except Exception as e:
            panel.update_data(["ERROR"], [[str(e)]])

    def _handle_command(self, cmd: str) -> None:
        """Process k9s-style : commands."""
        if not cmd:
            return
        cmd_log = self.query_one(CommandLog)
        panel = self.query_one(ResourcePanel)

        parts = cmd.split(None, 1)
        verb = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        # :q / :quit
        if verb in ("q", "quit"):
            self.action_quit()
            return

        # :ns <name> — switch namespace
        if verb in ("ns", "namespace") and arg:
            self.kube.set_namespace(arg)
            self.agent.namespace = arg
            self.query_one(CrumbBar).set_view(
                panel.current_type_name, arg
            )
            cmd_log.log_info(f"Namespace: {arg}")
            self._refresh_resources()
            return

        # :ctx / :context — list or switch context
        if verb in ("ctx", "context"):
            if arg:
                ok = self.kube.switch_context(arg)
                if ok:
                    self.agent.cluster_name = self.kube.info.cluster_name
                    self.agent.context_name = self.kube.info.context_name
                    self.agent.namespace = self.kube.namespace
                    header = self.query_one(HeaderBar)
                    header.cluster = self.kube.info.cluster_name
                    header.context = self.kube.info.context_name
                    header.refresh_header()
                    self.query_one(CrumbBar).set_view(
                        panel.current_type_name, self.kube.namespace
                    )
                    cmd_log.log_ok("ctx", f"Switched to {arg}")
                    self._refresh_resources()
                else:
                    cmd_log.log_error("ctx", f"Failed to switch to {arg}")
            else:
                contexts = self.kube.list_contexts()
                if contexts:
                    for name, active in contexts:
                        marker = " *" if active else ""
                        cmd_log.log_info(f"  {name}{marker}")
                else:
                    cmd_log.log_error("ctx", "No contexts found")
            return

        # Resource navigation aliases
        if verb in COMMAND_ALIASES:
            idx = COMMAND_ALIASES[verb]
            panel.set_resource_type(idx)
            return

        # :xray, :pulses — not implemented
        if verb in ("xray", "pulses", "pu"):
            cmd_log.log_info(f":{verb} not yet supported")
            return

        # Fallback: try as kubectl
        cmd_log.log_tool("kubectl", cmd)
        try:
            result = subprocess.run(
                ["kubectl"] + cmd.split(),
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout or result.stderr
            cmd_log.log_ok("kubectl", output.strip()[:200])
        except Exception as e:
            cmd_log.log_error("kubectl", str(e))

    def _ask_copilot_about_selected(self, action: str) -> None:
        """Use copilot to perform an action on the selected resource."""
        panel = self.query_one(ResourcePanel)
        name = panel.get_selected_name()
        if not name:
            return

        resource_type = panel.current_type_name.lower().rstrip("s")
        ns = self.kube.namespace

        prompts = {
            "describe": f"kubectl describe {resource_type} {name} -n {ns}",
            "yaml": f"kubectl get {resource_type} {name} -n {ns} -o yaml",
            "logs": f"kubectl logs {name} -n {ns} --tail=100",
            "shell": f"Explain how to exec into pod {name} in namespace {ns}. Do NOT actually exec.",
        }
        prompt = prompts.get(action, f"kubectl describe {resource_type} {name} -n {ns}")

        # Show copilot if hidden
        if not self._copilot_visible:
            self.action_toggle_copilot()

        if not self._agent_running:
            self._run_agent(prompt)

    def _run_agent(self, prompt: str) -> None:
        copilot = self.query_one(CopilotPanel)
        cmd_log = self.query_one(CommandLog)

        copilot.add_user_message(prompt)
        copilot.add_status("thinking...")
        cmd_log.log_info(f"copilot: {prompt[:80]}")

        self._agent_running = True
        self._current_tool_name = ""

        self.run_worker(
            self._agent_worker(prompt),
            name="copilot_agent",
            exclusive=True,
        )

    async def _agent_worker(self, prompt: str) -> None:
        try:
            await self.agent.run(prompt, on_event=self._on_agent_event)
        finally:
            self._agent_running = False
            self.query_one(CopilotPanel).add_separator()

    def _on_agent_event(self, event: AgentEvent) -> None:
        copilot = self.query_one(CopilotPanel)
        cmd_log = self.query_one(CommandLog)

        if event.kind == "text":
            copilot.add_assistant_text(event.text)
        elif event.kind == "thinking":
            copilot.add_status(f"thinking: {event.text[:80]}...")
        elif event.kind == "tool_use":
            self._current_tool_name = event.tool_name
            copilot.add_tool_call(event.tool_name, event.tool_input)
            cmd_log.log_tool(event.tool_name, event.tool_input[:100])
        elif event.kind == "tool_result":
            name = self._current_tool_name or "tool"
            if event.is_error:
                copilot.add_tool_result(event.text, True)
                cmd_log.log_error(name, event.text[:100])
            else:
                copilot.add_tool_result(event.text, False)
                cmd_log.log_ok(name, event.text[:100])
            self._refresh_resources()
        elif event.kind == "error":
            copilot.add_error(event.text)
            cmd_log.log_error("copilot", event.text)
        elif event.kind == "done":
            self._agent_running = False

    def _build_help_text(self) -> str:
        return (
            "[bold #00d7af]kpilot — Keyboard Shortcuts[/]\n"
            "\n"
            "[bold #d7af00]Navigation[/]\n"
            "  [bold]:[/]          Command mode\n"
            "  [bold]/[/]          Filter resources\n"
            "  [bold]Esc[/]        Go back / clear filter\n"
            "  [bold]?[/]          Toggle this help\n"
            "  [bold]Ctrl-c[/]     Quit\n"
            "\n"
            "[bold #d7af00]Resource Actions[/]\n"
            "  [bold]d[/]          Describe selected resource\n"
            "  [bold]y[/]          Show YAML of selected resource\n"
            "  [bold]l[/]          View logs (pods)\n"
            "  [bold]s[/]          Shell info (pods)\n"
            "  [bold]Enter[/]      Select\n"
            "\n"
            "[bold #d7af00]Copilot[/]\n"
            "  [bold]c[/]          Toggle copilot panel\n"
            "  Type a question and press Enter\n"
            "\n"
            "[bold #d7af00]Commands[/]  (press : first)\n"
            "  :po :pods          Pods\n"
            "  :svc :service      Services\n"
            "  :dp :deploy        Deployments\n"
            "  :ns                Namespaces\n"
            "  :ns <name>         Switch namespace\n"
            "  :no :nodes         Nodes\n"
            "  :cm                ConfigMaps\n"
            "  :sec               Secrets\n"
            "  :pvc               PersistentVolumeClaims\n"
            "  :ev                Events\n"
            "  :ctx               List contexts\n"
            "  :ctx <name>        Switch context\n"
            "  :q :quit           Quit\n"
        )

from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Static, Input, DataTable

from kpilot.config import Config
from kpilot.kube.client import KubeClient
from kpilot.agent.loop import AgentLoop, AgentEvent
from kpilot.ui.theme import APP_CSS
from kpilot.ui.header import Header
from kpilot.ui.resource_panel import ResourcePanel, ResourceTypeChanged
from kpilot.ui.chat_panel import ChatPanel, ChatSubmitted
from kpilot.ui.command_log import CommandLog

RESOURCE_FETCH = {
    0: "list_pods",
    1: "list_services",
    2: "list_deployments",
    3: "list_namespaces",
    4: "list_nodes",
}


class KPilotApp(App):
    """Kubernetes TUI with Claude AI Copilot."""

    CSS = APP_CSS

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit", show=False),
        Binding("1", "resource(0)", "Pods", show=False),
        Binding("2", "resource(1)", "Services", show=False),
        Binding("3", "resource(2)", "Deployments", show=False),
        Binding("4", "resource(3)", "Namespaces", show=False),
        Binding("5", "resource(4)", "Nodes", show=False),
        Binding("c", "focus_chat", "Chat", show=False),
        Binding("escape", "focus_resources", "Resources", show=False),
        Binding("question_mark", "toggle_help", "Help", show=False),
        Binding("colon", "command_mode", "Command", show=False),
        Binding("slash", "filter_mode", "Filter", show=False),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.kube = KubeClient(config.kubeconfig, config.namespace)
        self.agent = AgentLoop(model=config.model if config.model else None)
        self._agent_running = False
        self._current_tool_name = ""

    def compose(self) -> ComposeResult:
        yield Header(
            cluster=self.kube.info.cluster_name,
            context=self.kube.info.context_name,
            namespace=self.kube.namespace,
        )
        with Horizontal(id="main-container"):
            yield ResourcePanel()
            yield ChatPanel()
        yield CommandLog()
        yield Input(placeholder=":command...", id="command-input")
        yield Static("", id="help-modal")

    def on_mount(self) -> None:
        self.kube.connect()

        header = self.query_one(Header)
        header.cluster = self.kube.info.cluster_name
        header.context = self.kube.info.context_name
        header.namespace = self.kube.namespace
        header.refresh_header()

        self.agent.cluster_name = self.kube.info.cluster_name
        self.agent.context_name = self.kube.info.context_name
        self.agent.namespace = self.kube.namespace

        cmd_log = self.query_one(CommandLog)
        if self.kube.connected:
            cmd_log.log_info(
                f"Connected to cluster: {self.kube.info.cluster_name} "
                f"(ctx: {self.kube.info.context_name})"
            )
        else:
            cmd_log.log_error("kube", "Not connected to any cluster")

        if not self.config.anthropic_key:
            cmd_log.log_info(
                "ANTHROPIC_API_KEY not set -- Claude chat requires it"
            )

        self._refresh_resources()
        self.set_interval(5.0, self._refresh_resources)
        self._focus_table()

    # ── Actions ─────────────────────────────────────────────────

    def action_resource(self, index: int) -> None:
        panel = self.query_one(ResourcePanel)
        panel.set_resource_type(index)
        self._focus_table()

    def action_focus_chat(self) -> None:
        self.query_one(ChatPanel).focus_input()

    def action_focus_resources(self) -> None:
        self.query_one("#filter-input", Input).remove_class("visible")
        self.query_one("#command-input", Input).remove_class("visible")
        self.query_one("#help-modal", Static).remove_class("visible")
        self._focus_table()

    def action_toggle_help(self) -> None:
        modal = self.query_one("#help-modal", Static)
        if modal.has_class("visible"):
            modal.remove_class("visible")
            self._focus_table()
        else:
            modal.update(
                "[bold rgb(127,255,212)]Keybindings[/]\n\n"
                "  [bold]1-5[/]    Switch resource type\n"
                "  [bold]c[/]      Focus Claude chat input\n"
                "  [bold]:[/]      Command mode\n"
                "  [bold]/[/]      Filter resources\n"
                "  [bold]?[/]      Toggle this help\n"
                "  [bold]Esc[/]    Return to resource panel\n"
                "  [bold]q[/]      Quit\n\n"
                "[bold]Commands:[/]\n"
                "  :pods, :svc, :deploy, :ns, :nodes\n"
                "  :ns <name>       Switch namespace\n"
                "  :kubectl <cmd>   Run kubectl command\n"
            )
            modal.add_class("visible")
            modal.focus()

    def action_command_mode(self) -> None:
        cmd_input = self.query_one("#command-input", Input)
        cmd_input.add_class("visible")
        cmd_input.value = ""
        cmd_input.focus()

    def action_filter_mode(self) -> None:
        filter_input = self.query_one("#filter-input", Input)
        filter_input.add_class("visible")
        filter_input.value = ""
        filter_input.focus()

    def action_quit(self) -> None:
        self.agent.cancel()
        self.exit()

    # ── Event handlers ──────────────────────────────────────────

    def on_resource_type_changed(self, event: ResourceTypeChanged) -> None:
        self._refresh_resources()

    def on_chat_submitted(self, event: ChatSubmitted) -> None:
        if self._agent_running:
            return
        self._run_agent(event.text)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "command-input":
            event.input.remove_class("visible")
            self._handle_command(event.value.strip())
            self._focus_table()
        elif event.input.id == "filter-input":
            event.input.remove_class("visible")
            panel = self.query_one(ResourcePanel)
            panel.set_filter(event.value.strip())
            self._refresh_resources()
            self._focus_table()

    # ── Internal ────────────────────────────────────────────────

    def _focus_table(self) -> None:
        try:
            table = self.query_one("#resource-table", DataTable)
            table.focus()
        except Exception:
            pass

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
        if not cmd:
            return
        cmd_log = self.query_one(CommandLog)
        panel = self.query_one(ResourcePanel)

        cmd_lower = cmd.lower()
        if cmd_lower in ("pods", "pod"):
            panel.set_resource_type(0)
        elif cmd_lower in ("svc", "services", "service"):
            panel.set_resource_type(1)
        elif cmd_lower in ("deploy", "deployments", "deployment"):
            panel.set_resource_type(2)
        elif cmd_lower in ("ns", "namespaces", "namespace"):
            panel.set_resource_type(3)
        elif cmd_lower in ("nodes", "node"):
            panel.set_resource_type(4)
        elif cmd_lower.startswith("ns "):
            new_ns = cmd[3:].strip()
            if new_ns:
                self.kube.set_namespace(new_ns)
                self.agent.namespace = new_ns
                self.query_one(Header).set_namespace(new_ns)
                cmd_log.log_info(f"Switched namespace to: {new_ns}")
                self._refresh_resources()
        elif cmd_lower.startswith("kubectl "):
            kubectl_cmd = cmd[8:].strip()
            cmd_log.log_tool("kubectl", kubectl_cmd)
            try:
                import subprocess

                result = subprocess.run(
                    ["kubectl"] + kubectl_cmd.split(),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                output = result.stdout or result.stderr
                cmd_log.log_ok("kubectl", output.strip()[:200])
            except Exception as e:
                cmd_log.log_error("kubectl", str(e))
        else:
            cmd_log.log_error("cmd", f"Unknown command: {cmd}")

    def _run_agent(self, prompt: str) -> None:
        chat = self.query_one(ChatPanel)
        cmd_log = self.query_one(CommandLog)

        chat.add_user_message(prompt)
        chat.add_status("Claude is thinking...")
        cmd_log.log_info(f"Claude query: {prompt[:80]}")

        self._agent_running = True
        self._current_tool_name = ""

        self.run_worker(
            self._agent_worker(prompt),
            name="claude_agent",
            exclusive=True,
        )

    async def _agent_worker(self, prompt: str) -> None:
        """Worker coroutine that runs the agent loop."""
        try:
            await self.agent.run(prompt, on_event=self._on_agent_event)
        finally:
            self._agent_running = False
            chat = self.query_one(ChatPanel)
            chat.add_separator()

    def _on_agent_event(self, event: AgentEvent) -> None:
        """Called from the agent async worker for each event."""
        chat = self.query_one(ChatPanel)
        cmd_log = self.query_one(CommandLog)

        if event.kind == "text":
            chat.add_assistant_text(event.text)
        elif event.kind == "thinking":
            chat.add_status(f"[thinking] {event.text[:100]}...")
        elif event.kind == "tool_use":
            self._current_tool_name = event.tool_name
            chat.add_tool_call(event.tool_name, event.tool_input)
            cmd_log.log_tool(event.tool_name, event.tool_input[:100])
        elif event.kind == "tool_result":
            name = self._current_tool_name or "tool"
            if event.is_error:
                chat.add_tool_result(event.text, True)
                cmd_log.log_error(name, event.text[:100])
            else:
                chat.add_tool_result(event.text, False)
                cmd_log.log_ok(name, event.text[:100])
            self._refresh_resources()
        elif event.kind == "error":
            chat.add_error(event.text)
            cmd_log.log_error("claude", event.text)
        elif event.kind == "done":
            self._agent_running = False

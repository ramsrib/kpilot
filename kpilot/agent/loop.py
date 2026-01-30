from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from claude_code_sdk import (
    query,
    ClaudeCodeOptions,
    AssistantMessage,
    UserMessage,
    SystemMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
)


@dataclass
class AgentEvent:
    """A single event emitted by the agent loop."""

    kind: str  # "text", "thinking", "tool_use", "tool_result", "error", "done"
    text: str = ""
    tool_name: str = ""
    tool_input: str = ""
    tool_id: str = ""
    is_error: bool = False


class AgentLoop:
    """Runs Claude via claude-code-sdk, yielding AgentEvents."""

    def __init__(
        self,
        cluster_name: str = "",
        context_name: str = "",
        namespace: str = "default",
        model: str | None = None,
    ) -> None:
        self.cluster_name = cluster_name
        self.context_name = context_name
        self.namespace = namespace
        self.model = model
        self._cancelled = False

    def _system_prompt(self) -> str:
        return f"""You are a Kubernetes cluster assistant embedded in a terminal UI (similar to k9s).
You have access to bash to run kubectl commands against the cluster.

Current cluster context:
- Cluster: {self.cluster_name}
- Context: {self.context_name}
- Default namespace: {self.namespace}

Guidelines:
- Use kubectl commands to query real cluster data -- do not guess.
- Be concise -- your output is displayed in a narrow terminal panel.
- Format output for readability in a monospace terminal.
- When listing resources, prefer tabular kubectl output.
- If a command fails, explain the error clearly.
- You can chain multiple kubectl calls to gather information before answering."""

    async def run(
        self,
        prompt: str,
        on_event: Callable[[AgentEvent], None] | None = None,
    ) -> None:
        """Run the agentic loop for a single user prompt."""
        self._cancelled = False

        options = ClaudeCodeOptions(
            system_prompt=self._system_prompt(),
            allowed_tools=["Bash"],
            permission_mode="bypassPermissions",
            max_turns=30,
        )
        if self.model:
            options.model = self.model

        try:
            async for msg in query(prompt=prompt, options=options):
                if self._cancelled:
                    break
                self._process_message(msg, on_event)
        except Exception as e:
            if on_event:
                on_event(AgentEvent(kind="error", text=str(e), is_error=True))

        if on_event:
            on_event(AgentEvent(kind="done"))

    def cancel(self) -> None:
        self._cancelled = True

    def _process_message(
        self, msg: object, on_event: Callable[[AgentEvent], None] | None
    ) -> None:
        if on_event is None:
            return

        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                self._process_block(block, on_event)
        elif isinstance(msg, UserMessage):
            # User messages from the SDK contain tool results
            content = msg.content
            if isinstance(content, list):
                for block in content:
                    self._process_block(block, on_event)
        elif isinstance(msg, ResultMessage):
            if msg.is_error:
                on_event(AgentEvent(
                    kind="error",
                    text=msg.result or "Unknown error",
                    is_error=True,
                ))
        elif isinstance(msg, SystemMessage):
            pass  # Internal system messages, ignore

    def _process_block(
        self, block: object, on_event: Callable[[AgentEvent], None]
    ) -> None:
        if isinstance(block, TextBlock):
            on_event(AgentEvent(kind="text", text=block.text))
        elif isinstance(block, ThinkingBlock):
            on_event(AgentEvent(kind="thinking", text=block.thinking))
        elif isinstance(block, ToolUseBlock):
            input_str = json.dumps(block.input, indent=2) if block.input else ""
            on_event(AgentEvent(
                kind="tool_use",
                tool_name=block.name,
                tool_input=input_str,
                tool_id=block.id,
            ))
        elif isinstance(block, ToolResultBlock):
            content = block.content
            if isinstance(content, list):
                parts = []
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        parts.append(c.get("text", ""))
                    else:
                        parts.append(str(c))
                content = "\n".join(parts)
            on_event(AgentEvent(
                kind="tool_result",
                text=str(content or ""),
                tool_id=block.tool_use_id,
                is_error=bool(block.is_error),
            ))

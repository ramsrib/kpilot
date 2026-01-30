# kpilot

A Kubernetes TUI with an AI copilot. Browse your cluster like [k9s](https://k9scli.io/) and ask questions in natural language — the copilot runs `kubectl` commands for you and explains the results.

Built with [Textual](https://textual.textualize.io/) and [Claude Code SDK](https://docs.anthropic.com/en/docs/claude-code-sdk).

```
┌──────────────────────────────────────────────────────────────────────┐
│  kpilot  ctx: my-context  cluster: my-cluster  k8s: v1.30.2        │
│  Pods(default)  ?:help  ::cmd  /:filter  <esc>:back                 │
├──────────────────────────────┬───────────────────────────────────────┤
│  NAME    READY STATUS   AGE  │ Copilot                              │
│  nginx   1/1   Running  2d   │ > why is my pod crashlooping?        │
│  redis   1/1   Running  1d   │                                      │
│▶ api     0/1   Error    5m   │ $ kubectl describe pod api -n default│
│                              │ $ kubectl logs api -n default         │
│                              │                                      │
│                              │ The pod `api` is crash-looping        │
│                              │ because the readiness probe is ...    │
├──────────────────────────────┴───────────────────────────────────────┤
│  Command Log                                                         │
│  12:01:05 [TOOL] Bash kubectl describe pod api -n default            │
│  12:01:06 [OK  ] Bash -> ...                                         │
└──────────────────────────────────────────────────────────────────────┘
```

## Features

- **k9s-style resource browser** — Pods, Services, Deployments, Namespaces, Nodes with live auto-refresh
- **AI copilot panel** — ask anything about your cluster in plain English
- **Agentic tool use** — the copilot runs real `kubectl` commands, reads the output, and reasons about it
- **k9s keybindings** — `:` commands, `/` filter, `d` describe, `y` yaml, `l` logs, and more
- **Command log** — every tool call and result is logged with timestamps

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`npm install -g @anthropic-ai/claude-code`)
- `kubectl` configured and on your `PATH`
- Access to a Kubernetes cluster (via `~/.kube/config` or `KUBECONFIG`)
- **One of:**
  - A [Claude Code subscription](https://claude.ai) (Pro or Max plan) — just be logged in via `claude`
  - An `ANTHROPIC_API_KEY` environment variable

## Install

```bash
git clone https://github.com/ramsrib/kpilot.git
cd kpilot
uv sync
```

Or with pip:

```bash
pip install -e .
```

## Configuration

kpilot is configured via environment variables:

| Variable | Description | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key (not needed with Claude Code subscription) | — |
| `KUBECONFIG` | Path to kubeconfig file | `~/.kube/config` |
| `KPILOT_NAMESPACE` | Default namespace | `default` |
| `KPILOT_MODEL` | Claude model to use | `claude-sonnet-4-20250514` |

The copilot works in two modes:

1. **Claude Code subscription** — if `claude` is installed and you're logged in, it just works. No API key needed.
2. **API key** — set `ANTHROPIC_API_KEY` for direct API access.

```bash
# Option 1: subscription — nothing to set, just have `claude` logged in

# Option 2: API key
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Usage

```bash
# With uv
uv run kpilot

# Or as a module
uv run python -m kpilot.main

# Or if installed with pip
kpilot
```

The TUI launches immediately. The resource browser works without any auth — the copilot panel requires either a Claude Code subscription or an API key.

## Keybindings

### Navigation

| Key | Action |
|---|---|
| `:` | Command mode |
| `/` | Filter resources |
| `Esc` | Go back / clear filter / close overlays |
| `?` | Toggle help |
| `Ctrl-c` | Quit |

### Resource Actions

| Key | Action |
|---|---|
| `d` | Describe selected resource (via copilot) |
| `y` | Show YAML of selected resource (via copilot) |
| `l` | View logs of selected pod (via copilot) |
| `s` | Shell info for selected pod (via copilot) |

### Copilot

| Key | Action |
|---|---|
| `c` | Toggle copilot panel |
| `Enter` | Submit question (when copilot input is focused) |

## Commands

Press `:` to enter command mode, then type a command and press `Enter`.

| Command | Action |
|---|---|
| `:po` `:pods` | Switch to Pods view |
| `:svc` `:service` | Switch to Services view |
| `:dp` `:deploy` | Switch to Deployments view |
| `:ns` | Switch to Namespaces view |
| `:ns <name>` | Switch to a specific namespace |
| `:no` `:nodes` | Switch to Nodes view |
| `:q` `:quit` | Quit |

Any unrecognized command is passed to `kubectl` as-is. For example, `:get configmaps` runs `kubectl get configmaps`.

## How the Copilot Works

The copilot uses the [Claude Code SDK](https://docs.anthropic.com/en/docs/claude-code-sdk) to run an agentic loop. When you ask a question:

1. Your question is sent to Claude with context about your cluster (cluster name, context, namespace)
2. Claude decides what `kubectl` commands to run to answer your question
3. Each command runs via the Bash tool — input and output are shown in the copilot panel and command log
4. Claude reads the results, reasons about them, and may run follow-up commands
5. The final answer appears in the copilot panel

You can also trigger the copilot with resource action keys (`d`, `y`, `l`, `s`) — these auto-open the copilot panel and send the appropriate kubectl command.

## Project Structure

```
kpilot/
├── main.py              # Entry point
├── config.py            # Configuration from environment variables
├── kube/
│   └── client.py        # Kubernetes API client (resource listing)
├── agent/
│   └── loop.py          # Claude Code SDK agentic loop
└── ui/
    ├── app.py           # Main TUI application, keybindings, event handling
    ├── theme.py         # CSS theme (k9s-inspired dark theme)
    ├── header.py        # Header bar + breadcrumb bar
    ├── resource_panel.py # Resource data table
    ├── chat_panel.py    # Copilot panel (chat log + input)
    └── command_log.py   # Timestamped command/action log
```

## License

MIT

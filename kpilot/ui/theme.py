"""CSS theme for kpilot — k9s-inspired dark theme."""

APP_CSS = """
Screen {
    background: #111111;
}

/* ── Header ──────────────────────────────────────── */

#header-bar {
    dock: top;
    height: 1;
    background: #0a2351;
    color: #ffffff;
    padding: 0 1;
}

#crumb-bar {
    dock: top;
    height: 1;
    background: #1a1a2e;
    color: #aaaaaa;
    padding: 0 1;
}

/* ── Main layout ─────────────────────────────────── */

#main-container {
    height: 1fr;
}

#resource-panel {
    width: 1fr;
    border: solid #444466;
}

#copilot-panel {
    width: 2fr;
    border: solid #444466;
    border-title-color: #00d7af;
    display: none;
}

#copilot-panel.visible {
    display: block;
}

#copilot-log {
    height: 1fr;
    scrollbar-size: 1 1;
    padding: 0 1;
}

#copilot-input {
    dock: bottom;
    height: 3;
    padding: 0 1;
    border-top: solid #444466;
}

#copilot-input:focus {
    border-top: solid #00d7af;
}

/* ── Resource table ──────────────────────────────── */

#resource-table {
    height: 1fr;
}

DataTable > .datatable--header {
    color: #d7af00;
    text-style: bold;
    background: #1a1a2e;
}

DataTable > .datatable--cursor {
    background: #00d7af;
    color: #000000;
}

DataTable > .datatable--even-row {
    background: #111111;
}

DataTable > .datatable--odd-row {
    background: #151520;
}

/* ── Command log ─────────────────────────────────── */

#command-log {
    dock: bottom;
    height: 7;
    border: solid #444466;
    border-title-color: #00d7af;
    scrollbar-size: 1 1;
    padding: 0 1;
}

/* ── Filter & command inputs ─────────────────────── */

#filter-bar {
    dock: bottom;
    height: 1;
    display: none;
    border: none;
    padding: 0 1;
    background: #1a1a2e;
    color: #ffffff;
}

#filter-bar.visible {
    display: block;
}

#filter-bar:focus {
    border: none;
}

#command-bar {
    dock: bottom;
    height: 1;
    display: none;
    border: none;
    padding: 0 1;
    background: #1a1a2e;
    color: #ffffff;
}

#command-bar.visible {
    display: block;
}

#command-bar:focus {
    border: none;
}

/* ── Help modal ──────────────────────────────────── */

#help-modal {
    align: center middle;
    width: 70;
    height: 30;
    border: solid #00d7af;
    background: #0a0a1a;
    padding: 1 2;
    layer: modal;
    display: none;
}

#help-modal.visible {
    display: block;
}
"""

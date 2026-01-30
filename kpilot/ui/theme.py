"""CSS theme for the kpilot TUI."""

APP_CSS = """
Screen {
    background: $surface;
}

#header {
    dock: top;
    height: 1;
    background: rgb(20, 60, 120);
    color: white;
    padding: 0 1;
}

#main-container {
    height: 1fr;
}

#resource-panel {
    width: 3fr;
    border: solid rgb(0, 135, 135);
    border-title-color: rgb(127, 255, 212);
}

#chat-panel {
    width: 2fr;
    border: solid rgb(0, 135, 135);
    border-title-color: rgb(127, 255, 212);
}

#chat-log {
    height: 1fr;
    scrollbar-size: 1 1;
    padding: 0 1;
}

#chat-input {
    dock: bottom;
    height: 3;
    padding: 0 1;
    border-top: solid rgb(0, 135, 135);
}

#chat-input:focus {
    border-top: solid rgb(127, 255, 212);
}

#command-log {
    dock: bottom;
    height: 7;
    border: solid rgb(0, 135, 135);
    border-title-color: rgb(127, 255, 212);
    scrollbar-size: 1 1;
    padding: 0 1;
}

#resource-tabs {
    height: 1;
    padding: 0 1;
    background: rgb(30, 40, 50);
}

#resource-table {
    height: 1fr;
}

#filter-input {
    dock: bottom;
    height: 1;
    display: none;
    padding: 0 1;
}

#filter-input.visible {
    display: block;
}

#command-input {
    dock: bottom;
    height: 1;
    display: none;
    padding: 0 1;
}

#command-input.visible {
    display: block;
}

#help-modal {
    align: center middle;
    width: 60;
    height: 20;
    border: solid rgb(127, 255, 212);
    background: rgb(20, 30, 40);
    padding: 1 2;
    layer: modal;
    display: none;
}

#help-modal.visible {
    display: block;
}

DataTable > .datatable--header {
    color: rgb(255, 255, 0);
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: rgb(127, 255, 212);
    color: rgb(0, 0, 0);
}
"""

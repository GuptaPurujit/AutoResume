from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Label, Static


class AgentPanel(Widget):
    DEFAULT_CSS = """
    AgentPanel {
        layout: vertical;
        height: 100%;
    }
    AgentPanel > Label {
        width: 100%;
        text-align: center;
        background: $success-darken-2;
        color: $text;
        padding: 0 1;
    }
    AgentPanel > VerticalScroll {
        height: 1fr;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._buffer: list[str] = []

    def compose(self) -> ComposeResult:
        yield Label("Agent Output  (streaming)")
        with VerticalScroll(id="agent-scroll"):
            yield Static("", id="agent-text", markup=False)

    def append_chunk(self, chunk: str) -> None:
        self._buffer.append(chunk)
        self.query_one("#agent-text", Static).update("".join(self._buffer))
        self.query_one("#agent-scroll", VerticalScroll).scroll_end(animate=False)

    def clear(self) -> None:
        self._buffer = []
        self.query_one("#agent-text", Static).update("")

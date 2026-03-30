from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, TextArea


class ResumePanel(Widget):
    DEFAULT_CSS = """
    ResumePanel {
        layout: vertical;
        height: 100%;
    }
    ResumePanel > Label {
        width: 100%;
        text-align: center;
        background: $primary-darken-2;
        color: $text;
        padding: 0 1;
    }
    ResumePanel > TextArea {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Current Resume  [base]", id="resume-label")
        yield TextArea(
            "No resume loaded.\n\nUsage:  autoresume path/to/resume.md",
            id="resume-text",
            read_only=True,
        )

    def update_content(self, content: str, version: int | None = None) -> None:
        self.query_one("#resume-text", TextArea).load_text(content)
        label = self.query_one("#resume-label", Label)
        if version is not None:
            label.update(f"Current Resume  [v{version}]")
        else:
            label.update("Current Resume  [base]")

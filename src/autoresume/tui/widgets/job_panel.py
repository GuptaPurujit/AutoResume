from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, TextArea


class JobPanel(Widget):
    """Right-top panel: job description input, feedback/chat, action buttons."""

    # ── Messages (bubble up to MainScreen) ──────────────────────────────────

    class TailorRequested(Message):
        """User clicked Tailor."""

    class RefineRequested(Message):
        """User clicked Refine."""
        def __init__(self, feedback: str) -> None:
            super().__init__()
            self.feedback = feedback

    class AcceptRequested(Message):
        """User clicked Accept & Save."""

    class AgentChunk(Message):
        """A streaming text chunk from the LLM."""
        def __init__(self, chunk: str) -> None:
            super().__init__()
            self.chunk = chunk

    class AgentComplete(Message):
        """The LLM has finished streaming; carries the full response."""
        def __init__(self, full_response: str) -> None:
            super().__init__()
            self.full_response = full_response

    class AgentError(Message):
        """An error occurred during LLM streaming."""
        def __init__(self, error: str) -> None:
            super().__init__()
            self.error = error

    # ── Layout ───────────────────────────────────────────────────────────────

    DEFAULT_CSS = """
    JobPanel {
        layout: vertical;
        height: 100%;
    }
    JobPanel > Label {
        width: 100%;
        text-align: center;
        background: $accent-darken-2;
        color: $text;
        padding: 0 1;
    }
    #jd-input {
        height: 1fr;
        min-height: 4;
    }
    #feedback-input {
        height: 5;
        min-height: 3;
    }
    #btn-row {
        height: 3;
    }
    #btn-row Button {
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Job Description")
        yield TextArea("", id="jd-input")
        yield Label("Feedback / Chat")
        yield TextArea("", id="feedback-input")
        with Horizontal(id="btn-row"):
            yield Button("Tailor", id="btn-tailor", variant="primary")
            yield Button("Refine", id="btn-refine", variant="default")
            yield Button("Accept & Save", id="btn-accept", variant="success")

    # ── User actions ─────────────────────────────────────────────────────────

    def get_jd(self) -> str:
        return self.query_one("#jd-input", TextArea).text

    def get_feedback(self) -> str:
        return self.query_one("#feedback-input", TextArea).text

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-tailor":
            self.post_message(self.TailorRequested())
        elif event.button.id == "btn-refine":
            feedback = self.get_feedback()
            self.post_message(self.RefineRequested(feedback))
        elif event.button.id == "btn-accept":
            self.post_message(self.AcceptRequested())

    # ── Called by MainScreen to start agent workers ───────────────────────────

    def run_tailor(self) -> None:
        self._run_agent_tailor()

    def run_refine(self, feedback: str) -> None:
        self._run_agent_refine(feedback)

    # ── Thread workers (blocking Ollama streaming off the event loop) ─────────

    @work(exclusive=True, thread=True)
    def _run_agent_tailor(self) -> None:
        agent = self.app.agent  # type: ignore[attr-defined]
        full: list[str] = []
        try:
            for chunk in agent.tailor():
                full.append(chunk)
                self.post_message(self.AgentChunk(chunk))
            self.post_message(self.AgentComplete("".join(full)))
        except Exception as exc:
            self.post_message(self.AgentError(str(exc)))

    @work(exclusive=True, thread=True)
    def _run_agent_refine(self, feedback: str) -> None:
        agent = self.app.agent  # type: ignore[attr-defined]
        full: list[str] = []
        try:
            for chunk in agent.refine(feedback):
                full.append(chunk)
                self.post_message(self.AgentChunk(chunk))
            self.post_message(self.AgentComplete("".join(full)))
        except Exception as exc:
            self.post_message(self.AgentError(str(exc)))

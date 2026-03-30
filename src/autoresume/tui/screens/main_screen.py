from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Header

from ...renderer.ats_checker import ATSIssue
from ..widgets.agent_panel import AgentPanel
from ..widgets.job_panel import JobPanel
from ..widgets.resume_panel import ResumePanel


class MainScreen(Screen):
    BINDINGS = [
        Binding("ctrl+r", "render_pdf", "Render PDF"),
        Binding("ctrl+s", "save_version", "Save Version"),
        Binding("q", "app.quit", "Quit"),
    ]

    DEFAULT_CSS = """
    MainScreen {
        layout: vertical;
    }
    #main-container {
        height: 1fr;
    }
    #resume-panel {
        width: 1fr;
        border: round $primary;
    }
    #right-panel {
        width: 1fr;
        layout: vertical;
    }
    #job-panel {
        height: 1fr;
        border: round $accent;
    }
    #agent-panel {
        height: 1fr;
        border: round $success;
    }
    """

    # ── Internal messages for the async render worker ─────────────────────────

    class RenderComplete(Message):
        def __init__(self, pdf_path: Path, issues: list[ATSIssue], pages: int) -> None:
            super().__init__()
            self.pdf_path = pdf_path
            self.issues = issues
            self.pages = pages

    class RenderError(Message):
        def __init__(self, error: str) -> None:
            super().__init__()
            self.error = error

    # ── Init / Compose / Mount ────────────────────────────────────────────────

    def __init__(self, resume_path: Path | None = None) -> None:
        super().__init__()
        self._resume_path = resume_path
        self._current_version_path: Path | None = None
        self._has_pending_response: bool = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-container"):
            yield ResumePanel(id="resume-panel")
            with Vertical(id="right-panel"):
                yield JobPanel(id="job-panel")
                yield AgentPanel(id="agent-panel")
        yield Footer()

    def on_mount(self) -> None:
        if self._resume_path and self._resume_path.exists():
            content = self._resume_path.read_text(encoding="utf-8")
            self.app.agent.load_resume(content)  # type: ignore[attr-defined]
            self.query_one("#resume-panel", ResumePanel).update_content(content)
        self._check_ollama_health()

    def _check_ollama_health(self) -> None:
        if not self.app.ollama.health_check():  # type: ignore[attr-defined]
            self.notify(
                "Ollama is not reachable at localhost:11434.\n"
                "Start it with: ollama serve",
                title="Ollama Offline",
                severity="error",
                timeout=8,
            )

    # ── Agent message handlers ────────────────────────────────────────────────

    def on_job_panel_tailor_requested(self, _message: JobPanel.TailorRequested) -> None:
        agent = self.app.agent  # type: ignore[attr-defined]
        if not agent.state.base_resume:
            self.notify(
                "No resume loaded. Run: autoresume path/to/resume.md",
                title="No Resume",
                severity="error",
            )
            return
        jd = self.query_one("#job-panel", JobPanel).get_jd()
        if not jd.strip():
            self.notify(
                "Paste a job description into the Job Description box first.",
                title="No Job Description",
                severity="warning",
            )
            return
        tokens = agent.estimate_context_tokens()
        if tokens > 28_000:
            self.notify(
                f"Context is large (~{tokens} tokens). Response may be truncated.",
                title="Context Warning",
                severity="warning",
                timeout=5,
            )
        agent.set_job_description(jd)
        self.query_one("#agent-panel", AgentPanel).clear()
        self._has_pending_response = False
        self.query_one("#job-panel", JobPanel).run_tailor()

    def on_job_panel_refine_requested(self, message: JobPanel.RefineRequested) -> None:
        agent = self.app.agent  # type: ignore[attr-defined]
        if not agent.state.working_resume:
            self.notify("No resume to refine.", title="No Resume", severity="error")
            return
        if not message.feedback.strip():
            self.notify(
                "Enter feedback in the Feedback / Chat box first.",
                title="No Feedback",
                severity="warning",
            )
            return
        self.query_one("#agent-panel", AgentPanel).clear()
        self._has_pending_response = False
        self.query_one("#job-panel", JobPanel).run_refine(message.feedback)

    def on_job_panel_accept_requested(self, _message: JobPanel.AcceptRequested) -> None:
        agent = self.app.agent  # type: ignore[attr-defined]
        if not self._has_pending_response and not agent.has_pending_changes:
            self.notify(
                "Run Tailor or Refine first, then Accept & Save.",
                title="Nothing to Accept",
                severity="warning",
            )
            return
        accepted = agent.accept_working_resume()
        versioner = self.app.versioner  # type: ignore[attr-defined]
        path = versioner.save_version(accepted)
        self._current_version_path = path
        self._has_pending_response = False
        self.query_one("#resume-panel", ResumePanel).update_content(
            accepted, version=agent.state.version
        )
        self.notify(
            f"Saved {path.name}  (version {agent.state.version})",
            title="Version Saved",
            severity="information",
        )

    def on_job_panel_agent_chunk(self, message: JobPanel.AgentChunk) -> None:
        self.query_one("#agent-panel", AgentPanel).append_chunk(message.chunk)

    def on_job_panel_agent_complete(self, _message: JobPanel.AgentComplete) -> None:
        self._has_pending_response = True

    def on_job_panel_agent_error(self, message: JobPanel.AgentError) -> None:
        self.query_one("#agent-panel", AgentPanel).append_chunk(
            f"\n\n[ERROR] {message.error}"
        )
        self.notify(message.error, title="Agent Error", severity="error")

    # ── Render worker messages ────────────────────────────────────────────────

    def on_main_screen_render_complete(self, msg: RenderComplete) -> None:
        checker = self.app.renderer._checker  # type: ignore[attr-defined]
        ats_summary = checker.summary(msg.issues)

        if msg.pages > 1:
            # Renderer tried its best but the resume is still > 1 page
            self.notify(
                f"PDF saved ({msg.pages} pages — resume is too long to fit on one page).\n"
                f"{ats_summary}",
                title="Rendered",
                severity="warning",
                timeout=8,
            )
        elif msg.issues:
            self.notify(
                f"PDF saved: {msg.pdf_path.name}\n{ats_summary}\n"
                "(formatting was auto-corrected before rendering)",
                title="Rendered with fixes",
                severity="warning",
                timeout=8,
            )
        else:
            self.notify(
                f"PDF saved: {msg.pdf_path.name}  ✓ ATS-friendly, 1 page",
                title="Rendered",
                severity="information",
            )

    def on_main_screen_render_error(self, msg: RenderError) -> None:
        self.notify(msg.error, title="Render Error", severity="error")

    # ── Key-bound actions ─────────────────────────────────────────────────────

    def action_render_pdf(self) -> None:
        agent = self.app.agent  # type: ignore[attr-defined]
        versioner = self.app.versioner  # type: ignore[attr-defined]

        if not self._current_version_path:
            if not agent.state.current_resume:
                self.notify("No resume to render.", severity="warning")
                return
            path = versioner.save_version(agent.state.current_resume)
            self._current_version_path = path

        # Show a status toast while the worker runs (may take time if LLM formats)
        self.notify(
            "Checking ATS compatibility and rendering PDF…",
            title="Rendering",
            severity="information",
            timeout=60,
        )
        self._run_render(self._current_version_path)

    @work(exclusive=True, thread=True)
    def _run_render(self, md_path: Path) -> None:
        renderer = self.app.renderer  # type: ignore[attr-defined]
        pdf_path = md_path.with_suffix(".pdf")
        try:
            issues = renderer.render(md_path, pdf_path)
            # Re-render to get page count (document was already written; read it back)
            # We infer pages from the CSS fitting: if issues exist and were fixed,
            # count pages from the written PDF via a lightweight check.
            pages = _count_pdf_pages(pdf_path)
            self.post_message(self.RenderComplete(pdf_path, issues, pages))
        except Exception as exc:
            self.post_message(self.RenderError(str(exc)))

    def action_save_version(self) -> None:
        agent = self.app.agent  # type: ignore[attr-defined]
        if not agent.state.current_resume:
            self.notify("No resume to save.", severity="warning")
            return
        versioner = self.app.versioner  # type: ignore[attr-defined]
        path = versioner.save_version(agent.state.current_resume)
        self._current_version_path = path
        self.notify(f"Saved {path.name}", title="Version Saved")


# ── PDF page counter ──────────────────────────────────────────────────────────

def _count_pdf_pages(pdf_path: Path) -> int:
    """
    Count pages in the rendered PDF without a heavy dependency.
    Reads the raw PDF bytes and counts /Page dictionary objects.
    Falls back to 1 if parsing fails.
    """
    try:
        data = pdf_path.read_bytes()
        # PDF page count is stored as /Count N in the Pages dictionary
        import re as _re
        matches = _re.findall(rb"/Count\s+(\d+)", data)
        if matches:
            return int(matches[-1])
    except Exception:
        pass
    return 1

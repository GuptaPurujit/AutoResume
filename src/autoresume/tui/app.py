from pathlib import Path

from textual.app import App, ComposeResult

from ..agent.llm_client import OllamaClient
from ..agent.resume_agent import ResumeAgent
from ..renderer.engine import ResumeRenderer
from ..versioning import VersionManager
from .screens.main_screen import MainScreen


class AutoResumeApp(App):
    TITLE = "AutoResume"
    CSS_PATH = "app.tcss"

    def __init__(self, resume_path: Path | None = None) -> None:
        super().__init__()
        self.resume_path = resume_path
        # Shared services — accessible by all screens/widgets via self.app.*
        self.ollama = OllamaClient()
        self.agent = ResumeAgent(self.ollama)
        self.versioner = VersionManager(Path("resumes"))
        self.renderer = ResumeRenderer(ollama_client=self.ollama)

    def on_mount(self) -> None:
        self.push_screen(MainScreen(resume_path=self.resume_path))

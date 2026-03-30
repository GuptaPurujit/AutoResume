"""
Resume Rendering Engine
Pipeline: Markdown → ATS check → LLM format fix → HTML → single-page PDF
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import markdown
from jinja2 import Environment, FileSystemLoader
from weasyprint import CSS, HTML

from .ats_checker import ATSChecker, ATSIssue
from .formatter import MarkdownFormatter

if TYPE_CHECKING:
    from ..agent.llm_client import OllamaClient


class ResumeRenderer:
    """
    Converts a markdown resume to an ATS-friendly, single-page PDF.

    Pipeline
    --------
    1. ATS check  — detect formatting issues
    2. LLM fix    — structural-only reformat if issues found (requires ollama_client)
    3. HTML build — markdown → HTML via Jinja2 template
    4. Page fit   — try progressively tighter CSS until the resume fits on 1 page
                    (single-column layout is NEVER compromised; only fonts/margins shrink)
    5. PDF write  — WeasyPrint writes the final PDF
    """

    # Each tuple: (page_margin_in, body_font_pt, line_height)
    # Tried in order; first attempt that produces ≤1 page wins.
    # All attempts preserve single-column block-flow layout.
    _FITTING_STEPS: list[tuple[float, float, float]] = [
        (0.75, 11.0, 1.45),   # default — full quality
        (0.65, 10.5, 1.35),   # slight reduction
        (0.55, 10.0, 1.25),   # moderate reduction
        (0.50,  9.5, 1.20),   # aggressive reduction (last resort)
    ]

    def __init__(self, ollama_client: OllamaClient | None = None) -> None:
        template_dir = Path(__file__).parent / "templates"
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,
        )
        self._css_path = template_dir / "resume.css"
        self._checker = ATSChecker()
        self._formatter = MarkdownFormatter(ollama_client) if ollama_client else None

    # ── Public API ────────────────────────────────────────────────────────────

    def check_ats(self, md_text: str) -> list[ATSIssue]:
        """Run ATS validation only — no rendering."""
        return self._checker.check(md_text)

    def preprocess(self, md_text: str) -> tuple[str, list[ATSIssue]]:
        """
        Run ATS check; use LLM to fix any structural issues (content unchanged).
        Returns (clean_markdown, issues_found).
        """
        issues = self._checker.check(md_text)
        if issues and self._formatter:
            fixed = self._formatter.format(md_text, issues)
            return fixed, issues
        return md_text, issues

    def render(self, md_path: Path, output_pdf: Path) -> list[ATSIssue]:
        """Render a markdown FILE to a PDF. Returns any ATS issues found."""
        md_text = md_path.read_text(encoding="utf-8")
        return self._render(md_text, output_pdf)

    def render_string(self, md_text: str, output_pdf: Path) -> list[ATSIssue]:
        """Render a markdown STRING to a PDF. Returns any ATS issues found."""
        return self._render(md_text, output_pdf)

    # ── Internal pipeline ─────────────────────────────────────────────────────

    def _render(self, md_text: str, output_pdf: Path) -> list[ATSIssue]:
        clean_md, issues = self.preprocess(md_text)
        html_str = self._build_html(clean_md)
        self._write_single_page_pdf(html_str, output_pdf)
        return issues

    def _write_single_page_pdf(self, html_str: str, output_path: Path) -> None:
        """
        Try progressively tighter typographic settings until the resume fits on
        one page. Single-column layout is never touched — only @page margins,
        font-size, and line-height are adjusted via a CSS override layer.
        """
        main_css = CSS(filename=str(self._css_path))
        last_doc = None

        for margin, font_size, line_height in self._FITTING_STEPS:
            override = _make_override_css(margin, font_size, line_height)
            doc = HTML(string=html_str).render(
                stylesheets=[main_css, CSS(string=override)]
            )
            last_doc = doc
            if len(doc.pages) <= 1:
                doc.write_pdf(str(output_path))
                return

        # All attempts exhausted — write the most compact version
        assert last_doc is not None
        last_doc.write_pdf(str(output_path))

    def _build_html(self, md_text: str) -> str:
        html_body = markdown.markdown(
            md_text,
            extensions=["extra", "nl2br"],
            output_format="html",
        )
        template = self._jinja_env.get_template("resume.html.jinja2")
        return template.render(body=html_body)


# ── CSS override helper ───────────────────────────────────────────────────────

def _make_override_css(margin: float, font_size: float, line_height: float) -> str:
    """
    Generate a CSS override string that adjusts only typographic properties.
    Applied as a second stylesheet so it cascades over resume.css defaults.
    """
    contact_size = font_size - 0.5
    date_size    = font_size - 1.0
    h1_size      = font_size + 9.0
    h2_size      = font_size + 0.5
    h2_mt        = max(6, round(font_size * 0.9))
    h2_mb        = max(3, round(font_size * 0.4))
    h3_mt        = max(4, round(font_size * 0.55))

    return f"""\
@page {{
    margin: {margin}in;
}}
body {{
    font-size: {font_size}pt;
    line-height: {line_height};
}}
h1 {{
    font-size: {h1_size:.1f}pt;
    margin-bottom: 3pt;
}}
h1 + p {{
    font-size: {contact_size:.1f}pt;
    margin-bottom: 8pt;
}}
h2 {{
    font-size: {h2_size:.1f}pt;
    margin-top: {h2_mt}pt;
    margin-bottom: {h2_mb}pt;
}}
h3 {{
    font-size: {font_size:.1f}pt;
    margin-top: {h3_mt}pt;
    margin-bottom: 1pt;
}}
h3 + p {{
    font-size: {date_size:.1f}pt;
    margin-bottom: 3pt;
}}
li {{
    font-size: {font_size:.1f}pt;
    margin-bottom: 1pt;
}}
ul {{
    margin-bottom: 2pt;
    margin-left: 14pt;
}}
p {{
    margin-bottom: 3pt;
}}
"""

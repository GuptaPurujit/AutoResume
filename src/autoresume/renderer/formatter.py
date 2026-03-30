"""
LLM-based Markdown Formatter
Fixes ATS formatting issues in resume markdown WITHOUT changing any content.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..agent.llm_client import OllamaClient

from .ats_checker import ATSIssue


_SYSTEM_PROMPT = """\
You are a resume markdown formatter. Your ONLY job is to fix structural formatting issues.

ABSOLUTE RULES:
1. DO NOT change any content — same words, same experiences, same dates, same metrics.
2. DO NOT add or remove any jobs, skills, or achievements.
3. ONLY fix the structural issues listed in the prompt.
4. Output the corrected resume inside <formatted_resume>...</formatted_resume> tags.
5. Do not add explanations, comments, or a "Changes Made" section.
"""

_FORMAT_PROMPT = """\
Fix the following ATS formatting issues in this resume.

Issues to fix:
{issues_list}

Resume:
<resume>
{resume_content}
</resume>

Formatting rules to follow after fixing:
- One H1 line at the top: "# Full Name"
- H2 headings for sections: ## Summary, ## Experience, ## Education, ## Skills, ## Certifications
- H3 headings for each job/degree: "### Job Title — Company"
- Italic paragraph immediately after each H3 for date/location: "*Month YYYY – Month YYYY | City*"
- Flat bullet points (no nested lists) for achievements
- No tables — convert any tables to bullet lists
- No images
- No raw HTML

Output the corrected resume inside <formatted_resume>...</formatted_resume> tags now:"""


class MarkdownFormatter:
    """Uses a local LLM to fix ATS formatting issues in resume markdown."""

    def __init__(self, client: OllamaClient) -> None:
        self._client = client

    def format(self, md_text: str, issues: list[ATSIssue]) -> str:
        """
        Fix ATS formatting issues using the LLM.
        Returns the original text unchanged if LLM is unreachable or fails.
        Only issues fixable without content knowledge are sent.
        """
        fixable = self._fixable_issues(issues)
        if not fixable:
            return md_text

        issues_list = "\n".join(f"- {issue}" for issue in fixable)
        prompt = _FORMAT_PROMPT.format(
            issues_list=issues_list,
            resume_content=md_text,
        )

        try:
            raw = "".join(
                self._client.stream_chat(
                    [{"role": "user", "content": prompt}],
                    system=_SYSTEM_PROMPT,
                )
            )
            extracted = self._extract(raw)
            # Sanity check: result must be non-empty and start with # (H1)
            if extracted and re.match(r"^#\s", extracted):
                return extracted
        except Exception:
            pass  # graceful fallback

        return md_text

    @staticmethod
    def _fixable_issues(issues: list[ATSIssue]) -> list[ATSIssue]:
        """Filter to only issues the LLM can fix without inventing content."""
        # "missing_name" can't be fixed without knowing the name — skip it.
        unfixable = {"missing_name"}
        return [i for i in issues if i.kind not in unfixable]

    @staticmethod
    def _extract(raw: str) -> str:
        match = re.search(r"<formatted_resume>(.*?)</formatted_resume>", raw, re.DOTALL)
        if match:
            return match.group(1).strip()
        return raw.strip()

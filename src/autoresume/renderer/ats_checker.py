"""
ATS Friendliness Checker
Validates resume markdown against rules that affect ATS (Applicant Tracking System) parsing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# Standard H2 section headings ATS systems recognise
_STANDARD_SECTIONS: frozenset[str] = frozenset({
    "summary", "professional summary", "executive summary", "objective",
    "experience", "work experience", "professional experience", "employment",
    "education", "academic background", "academic history",
    "skills", "technical skills", "core competencies", "competencies", "key skills",
    "certifications", "licenses", "certificates", "credentials",
    "projects", "key projects", "notable projects",
    "awards", "achievements", "accomplishments", "honors",
    "publications", "research", "papers",
    "volunteer", "volunteering", "community", "community involvement",
    "languages",
    "interests", "hobbies", "activities",
    "references",
})


@dataclass
class ATSIssue:
    kind: str          # machine-readable tag e.g. "table", "nested_bullets"
    description: str   # human-readable explanation
    severity: str      # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.description}"


class ATSChecker:
    """Checks a markdown resume for ATS-hostile formatting."""

    def check(self, md_text: str) -> list[ATSIssue]:
        issues: list[ATSIssue] = []

        # ── H1 (name) ─────────────────────────────────────────────────────
        h1s = re.findall(r"^# .+", md_text, re.MULTILINE)
        if not h1s:
            issues.append(ATSIssue(
                "missing_name",
                "No H1 heading found — the candidate's name must be on a '# Name' line",
                "error",
            ))
        elif len(h1s) > 1:
            issues.append(ATSIssue(
                "multiple_h1",
                f"{len(h1s)} H1 headings found — only the first line (name) should use H1",
                "error",
            ))

        # ── Tables ────────────────────────────────────────────────────────
        if re.search(r"^\|.+\|", md_text, re.MULTILINE):
            issues.append(ATSIssue(
                "table",
                "Markdown table detected — ATS parsers cannot read tables; convert to bullet lists",
                "error",
            ))

        # ── Images ────────────────────────────────────────────────────────
        if re.search(r"!\[", md_text):
            issues.append(ATSIssue(
                "image",
                "Image syntax detected — ATS systems ignore images; remove them",
                "error",
            ))

        # ── H4+ headings (too deep) ───────────────────────────────────────
        if re.search(r"^#{4,} ", md_text, re.MULTILINE):
            issues.append(ATSIssue(
                "deep_heading",
                "H4+ headings found — use only H2 for sections and H3 for job titles",
                "warning",
            ))

        # ── Non-standard H2 section names ────────────────────────────────
        for h2 in re.findall(r"^## (.+)", md_text, re.MULTILINE):
            if h2.strip().lower() not in _STANDARD_SECTIONS:
                issues.append(ATSIssue(
                    "nonstandard_section",
                    f'Section "## {h2.strip()}" is non-standard — ATS may not categorise it; '
                    f"rename to one of: Summary, Experience, Education, Skills, Certifications",
                    "warning",
                ))

        # ── Nested bullet points ──────────────────────────────────────────
        if re.search(r"^[ \t]{4,}[-*+]", md_text, re.MULTILINE):
            issues.append(ATSIssue(
                "nested_bullets",
                "Nested bullet points detected — ATS expects flat lists; remove indented sub-bullets",
                "warning",
            ))

        # ── Raw HTML tags ─────────────────────────────────────────────────
        if re.search(
            r"<(div|span|table|td|th|tr|center|font|br|hr|p|b|i|u)\b",
            md_text,
            re.IGNORECASE,
        ):
            issues.append(ATSIssue(
                "html_tags",
                "Raw HTML tags detected — convert to plain markdown for maximum ATS compatibility",
                "warning",
            ))

        return issues

    @staticmethod
    def has_errors(issues: list[ATSIssue]) -> bool:
        return any(i.severity == "error" for i in issues)

    @staticmethod
    def summary(issues: list[ATSIssue]) -> str:
        if not issues:
            return "ATS check passed — no issues found"
        errors = sum(1 for i in issues if i.severity == "error")
        warnings = sum(1 for i in issues if i.severity == "warning")
        parts: list[str] = []
        if errors:
            parts.append(f"{errors} error{'s' if errors > 1 else ''}")
        if warnings:
            parts.append(f"{warnings} warning{'s' if warnings > 1 else ''}")
        return f"ATS issues: {', '.join(parts)}"

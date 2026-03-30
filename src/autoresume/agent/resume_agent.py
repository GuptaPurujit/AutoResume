import re
from collections.abc import Iterator
from dataclasses import dataclass, field

from .llm_client import OllamaClient
from .prompts import REFINE_PROMPT, SYSTEM_PROMPT, TAILOR_PROMPT


@dataclass
class AgentState:
    base_resume: str = ""        # original, never modified
    current_resume: str = ""     # last accepted/saved version
    working_resume: str = ""     # latest LLM output — may not be accepted yet
    job_description: str = ""
    conversation: list[dict] = field(default_factory=list)
    version: int = 0


class ResumeAgent:
    MAX_HISTORY_TURNS = 2

    def __init__(self, client: OllamaClient) -> None:
        self._client = client
        self.state = AgentState()

    def load_resume(self, content: str) -> None:
        self.state = AgentState(
            base_resume=content,
            current_resume=content,
            working_resume=content,
        )

    def set_job_description(self, jd: str) -> None:
        self.state.job_description = jd

    def tailor(self) -> Iterator[str]:
        """
        Initial tailoring pass against the last accepted version.
        Resets conversation history. Streams response chunks.
        After the stream ends, working_resume is automatically updated.
        """
        self.state.conversation = []
        prompt = TAILOR_PROMPT.format(
            resume_content=self.state.current_resume,
            job_description=self.state.job_description,
        )
        messages = [{"role": "user", "content": prompt}]
        return self._stream_and_record(messages)

    def refine(self, user_feedback: str) -> Iterator[str]:
        """
        Refinement pass against working_resume — the latest LLM output,
        regardless of whether it has been accepted yet. This allows the
        Tailor → Feedback → Refine → Feedback → Refine → Accept loop.
        Streams response chunks. After the stream ends, working_resume is updated.
        """
        prompt = REFINE_PROMPT.format(
            resume_content=self.state.working_resume,
            user_feedback=user_feedback,
        )
        self.state.conversation.append({"role": "user", "content": prompt})
        max_messages = self.MAX_HISTORY_TURNS * 2
        if len(self.state.conversation) > max_messages:
            self.state.conversation = self.state.conversation[-max_messages:]
        return self._stream_and_record(self.state.conversation)

    def accept_working_resume(self) -> str:
        """
        Promote working_resume → current_resume and bump the version counter.
        Returns the accepted resume content.
        """
        self.state.current_resume = self.state.working_resume
        self.state.version += 1
        return self.state.current_resume

    @property
    def has_pending_changes(self) -> bool:
        """True when working_resume differs from current_resume (un-accepted LLM output)."""
        return self.state.working_resume != self.state.current_resume

    def estimate_context_tokens(self) -> int:
        text = (
            self.state.working_resume
            + self.state.job_description
            + "".join(m["content"] for m in self.state.conversation)
        )
        return len(text) // 4

    @staticmethod
    def _extract_resume(raw: str) -> str:
        """Extract clean resume markdown from a raw LLM response."""
        # Strategy 1: XML tags — matches the output format instruction
        match = re.search(r"<tailored_resume>(.*?)</tailored_resume>", raw, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Strategy 2: Everything before "Changes Made:" header
        cm = re.search(r"\n\s*(?:#+\s*)?Changes\s+Made\s*:", raw, re.IGNORECASE)
        if cm:
            candidate = raw[: cm.start()].strip()
            candidate = re.sub(r"\n---+\s*$", "", candidate).strip()
            if candidate:
                return candidate

        # Strategy 3: Fallback — use the whole response
        return raw.strip()

    def _stream_and_record(self, messages: list[dict]) -> Iterator[str]:
        accumulated: list[str] = []
        for chunk in self._client.stream_chat(messages, system=SYSTEM_PROMPT):
            accumulated.append(chunk)
            yield chunk
        assistant_text = "".join(accumulated)
        # Auto-extract and store as working_resume so refine() can immediately
        # iterate on it without requiring an explicit Accept first.
        self.state.working_resume = self._extract_resume(assistant_text)
        # Record conversation history
        if messages is self.state.conversation:
            self.state.conversation.append(
                {"role": "assistant", "content": assistant_text}
            )
        else:
            # tailor() uses a local messages list; seed conversation for refine()
            self.state.conversation = [
                {"role": "assistant", "content": assistant_text}
            ]

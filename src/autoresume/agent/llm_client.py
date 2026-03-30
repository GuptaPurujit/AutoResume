import os
from collections.abc import Iterator

import ollama


class OllamaClient:
    MODEL = "qwen2.5:7b-instruct"
    CONTEXT_TOKENS = 32768

    def __init__(self, host: str | None = None) -> None:
        # Precedence: explicit arg → OLLAMA_HOST env var → localhost default
        resolved = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self._client = ollama.Client(host=resolved)

    def stream_chat(
        self,
        messages: list[dict],
        system: str | None = None,
    ) -> Iterator[str]:
        """Yield text chunks as they stream from the model."""
        full_messages: list[dict] = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        stream = self._client.chat(
            model=self.MODEL,
            messages=full_messages,
            stream=True,
            options={"num_ctx": self.CONTEXT_TOKENS},
        )
        for chunk in stream:
            delta = chunk["message"]["content"]
            if delta:
                yield delta

    def health_check(self) -> bool:
        try:
            self._client.list()
            return True
        except Exception:
            return False

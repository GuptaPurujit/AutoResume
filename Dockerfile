FROM python:3.12-slim

# ── System dependencies for WeasyPrint (PDF rendering) ───────────────────────
# On Linux these are installed via apt; on macOS they come from Homebrew.
# No DYLD_LIBRARY_PATH needed here — the libraries are on the standard path.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    fontconfig \
    shared-mime-info \
    # ATS-safe fonts: Liberation (Arial/Helvetica/Times equivalents) + FreeFont (serif/sans)
    fonts-liberation \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# ── uv (fast Python package manager) ─────────────────────────────────────────
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# ── Install Python dependencies (cached layer — only re-runs when deps change) ─
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ── Copy source and install the package ──────────────────────────────────────
COPY src/ src/
RUN uv sync --frozen --no-dev

# ── Output volume for versioned markdowns and rendered PDFs ──────────────────
RUN mkdir -p /app/resumes
VOLUME /app/resumes

# ── Ollama connection (override for Docker networking) ───────────────────────
# docker-compose sets this to http://ollama:11434
# When running standalone: -e OLLAMA_HOST=http://host.docker.internal:11434
ENV OLLAMA_HOST=http://host.docker.internal:11434

ENTRYPOINT ["uv", "run", "autoresume"]
CMD ["--help"]

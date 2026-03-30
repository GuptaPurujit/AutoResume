# AutoResume

A terminal-based resume builder powered by a **local LLM** (Qwen-2.5:7B via Ollama). Tailors your resume to any job description through an iterative chat loop — no cloud APIs, no data leaving your machine.

```
┌──────────────────────────┬───────────────────────────────────┐
│                          │  Job Description                  │
│  Current Resume  [v1]    │  ─────────────────────────────    │
│                          │  Feedback / Chat                  │
│  # Alex Johnson          │  [Tailor]  [Refine]  [Accept]     │
│  alex@email.com | ...    ├───────────────────────────────────┤
│                          │  Agent Output  (streaming)        │
│  ## Summary              │                                   │
│  Results-driven SWE...   │  <tailored_resume>                │
│                          │  # Alex Johnson                   │
│  ## Experience           │  ...                              │
│  ### Senior Engineer     │  </tailored_resume>               │
│  *2021–Present*          │  Changes Made:                    │
│  - Built scalable...     │  - Rewrote Summary...             │
└──────────────────────────┴───────────────────────────────────┘
  v1 | qwen2.5:7b-instruct          Ctrl+R=PDF  Ctrl+S=Save  Q=Quit
```

## Features

- **Iterative refinement loop** — Tailor → Refine (multiple times) → Accept; every feedback round builds on the previous LLM output, not the original
- **Fabrication prevention** — the agent is strictly constrained to only rearrange and reword existing content; it cannot invent experience
- **ATS-friendly PDF rendering** — Markdown → HTML → single-column PDF (Georgia/Arial, standard sections, no tables or images)
- **ATS validator** — checks your markdown for table syntax, non-standard headings, nested bullets, raw HTML, and more before rendering
- **LLM formatting fix** — if ATS issues are found, the LLM reformats structure only (never changes content) before generating the PDF
- **Single-page fitting** — automatically tries progressively tighter typography (font/margins) until the resume fits on one page; single-column layout is never compromised
- **Versioned output** — every accepted change saves a timestamped `resume_vN.md` alongside its `resume_vN.pdf`
- **Fully local** — runs on Ollama with Qwen-2.5:7B; no API keys, no internet required after setup

---

## Prerequisites

### 1. Ollama

AutoResume uses [Ollama](https://ollama.com) to run the LLM locally.

**Install Ollama**

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS via Homebrew
brew install ollama
```

For Windows, download the installer from [ollama.com/download](https://ollama.com/download).

**Pull the model**

```bash
ollama pull qwen2.5:7b-instruct
```

> The model is ~4.7 GB. Pull it once and it is cached locally.

**Start the Ollama server** (if not running as a service)

```bash
ollama serve
```

Ollama listens on `http://localhost:11434` by default.

### 2. Runtime — choose one

| Method | Requires |
|--------|----------|
| **Docker** (recommended) | Docker Desktop or Docker Engine |
| **Local Python** | Python 3.11+, [uv](https://docs.astral.sh/uv/), Homebrew (macOS) |

---

## Quick Start

### Option A — Docker Compose (easiest)

Docker Compose starts both Ollama and AutoResume together.

```bash
git clone https://github.com/your-username/autoresume.git
cd autoresume

# Start Ollama and build AutoResume
docker compose up -d ollama
docker compose build autoresume

# Pull the model inside the Ollama container
docker compose exec ollama ollama pull qwen2.5:7b-instruct

# Run the TUI with your resume.
# The current directory is mounted as /workspace inside the container,
# so pass the path relative to /workspace:
docker compose run --rm autoresume /workspace/my_resume.md
```

Rendered PDFs and versioned markdowns are saved to `./resumes/` on your host.

### Option B — Docker (standalone, Ollama on host)

If Ollama is already running on your machine:

```bash
git clone https://github.com/your-username/autoresume.git
cd autoresume
docker build -t autoresume .

# macOS / Windows (Docker Desktop)
# Mount the directory containing your resume as /workspace (read-only)
docker run -it --rm \
  -v "$(pwd)/resumes:/app/resumes" \
  -v "/path/to/resume/dir:/workspace:ro" \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  autoresume /workspace/my_resume.md

# Linux (Docker Engine)
docker run -it --rm \
  -v "$(pwd)/resumes:/app/resumes" \
  -v "/path/to/resume/dir:/workspace:ro" \
  -e OLLAMA_HOST=http://172.17.0.1:11434 \
  autoresume /workspace/my_resume.md
```

### Option C — Local Python (macOS)

**Install system dependencies** (WeasyPrint needs Pango/Cairo for PDF rendering):

```bash
brew install pango cairo glib
```

**Install uv** (if not already installed):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Clone and install:**

```bash
git clone https://github.com/your-username/autoresume.git
cd autoresume
uv sync
```

**Run via the wrapper script** (sets `DYLD_LIBRARY_PATH` for WeasyPrint):

```bash
chmod +x run.sh
./run.sh examples/base_resume.md
```

Or set the library path manually:

```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run autoresume examples/base_resume.md
```

---

## Usage

### Workflow

1. **Load** — start the app with your base resume markdown file as the argument
2. **Paste job description** — paste the full job posting into the *Job Description* box
3. **Tailor** — click **Tailor** (or `Ctrl+T`) to generate a tailored version; the agent streams output to the right panel
4. **Refine** — type feedback in the *Feedback / Chat* box and click **Refine**; the agent builds on its previous output, not the original
5. **Iterate** — repeat step 4 as many times as needed before committing
6. **Accept & Save** — click **Accept & Save** to promote the working version to `resume_v1.md`; the left panel updates to show it
7. **Render PDF** — press `Ctrl+R` to ATS-check, auto-fix formatting issues, fit to one page, and export to `resume_v1.pdf`

> **Tip:** You can do multiple Refine rounds between each Accept. Each accepted version gets its own version number. Tailoring always starts fresh from the last accepted version.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+T` | Tailor resume to job description |
| `Ctrl+R` | Render current version to PDF |
| `Ctrl+S` | Save current version (without PDF) |
| `Q` | Quit |

---

## Resume Markdown Format

AutoResume expects a specific markdown structure. Use `examples/base_resume.md` as a starting point.

### Required structure

```markdown
# Full Name
email@example.com | (555) 123-4567 | linkedin.com/in/yourname | City, State

## Summary
One or two sentences describing your background and target role.

## Experience

### Job Title — Company Name
*Month YYYY – Month YYYY | City, State*

- Achievement with quantified result (e.g., "Reduced latency by 40%")
- Another bullet point

### Earlier Job — Previous Company
*Month YYYY – Month YYYY | Remote*

- Bullet point

## Education

### Degree — University Name
*Graduated Month YYYY*

## Skills

**Languages:** Python, Go, TypeScript
**Frameworks:** FastAPI, React, gRPC
**Tools:** Docker, Kubernetes, AWS

## Certifications

- AWS Certified Solutions Architect (2023)
```

### Rules

| Element | Markdown | Notes |
|---------|----------|-------|
| Name | `# Name` | Exactly one H1 at the top |
| Contact | Plain paragraph after H1 | Pipe-separated on one line |
| Section | `## Section` | Use standard names (see below) |
| Job title | `### Title — Company` | H3 under `## Experience` |
| Date/location | `*Month YYYY – Month YYYY \| City*` | Italic line immediately after H3 |
| Achievements | `- bullet` | Flat list, no nested bullets |
| Skills | `**Category:** item, item` | Bold label in a paragraph |

**Standard section names** (ATS-recognised): `Summary`, `Experience`, `Education`, `Skills`, `Certifications`, `Projects`, `Awards`, `Publications`, `Volunteer`, `Languages`

---

## Rendering Pipeline

Every `Ctrl+R` runs the full pipeline:

```
Markdown
   │
   ▼
ATS Checker ──────────────────────────────────────────────────────────┐
   │ issues?                                                           │
   ▼ yes                                                              no
LLM Formatter (structure only, content unchanged)                      │
   │                                                                   │
   └───────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                            HTML generation
                         (Jinja2 + python-markdown)
                                    │
                                    ▼
                      Single-page CSS fitting loop
                  ┌────────────────────────────────┐
                  │  Try: 0.75in / 11pt / 1.45 lh  │ ◄── default, best quality
                  │  Try: 0.65in / 10.5pt / 1.35 lh│
                  │  Try: 0.55in / 10pt / 1.25 lh  │
                  │  Try: 0.50in / 9.5pt / 1.20 lh │ ◄── last resort
                  └────────────────────────────────┘
                   (single-column layout never changes)
                                    │
                                    ▼
                               PDF output
```

---

## Configuration

| Environment variable | Default | Description |
|---------------------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API endpoint. Override when running in Docker or using a remote Ollama instance. |

---

## Project Structure

```
autoresume/
├── src/autoresume/
│   ├── __main__.py              # CLI entry point
│   ├── versioning.py            # resume_vN.md auto-increment
│   ├── renderer/
│   │   ├── engine.py            # Full MD → PDF pipeline
│   │   ├── ats_checker.py       # ATS validation rules
│   │   ├── formatter.py         # LLM-based formatting fix
│   │   └── templates/
│   │       ├── resume.html.jinja2
│   │       └── resume.css       # ATS-safe CSS (single-column)
│   ├── agent/
│   │   ├── llm_client.py        # Ollama streaming wrapper
│   │   ├── resume_agent.py      # Tailor / refine / accept state machine
│   │   └── prompts.py           # System + task prompts
│   └── tui/
│       ├── app.py               # Textual App
│       ├── screens/main_screen.py
│       └── widgets/
│           ├── resume_panel.py  # Left: current version preview
│           ├── job_panel.py     # Right-top: JD input + chat
│           └── agent_panel.py   # Right-bottom: streaming output
├── examples/
│   └── base_resume.md           # Sample resume (Alex Johnson)
├── resumes/                     # Output directory (gitignored)
├── Dockerfile
├── docker-compose.yml
└── run.sh                       # macOS convenience wrapper
```

---

## Troubleshooting

**`Ollama Offline` notification at startup**

Make sure Ollama is running:
```bash
ollama serve          # start the server
ollama list           # verify qwen2.5:7b-instruct is pulled
```

**`cannot load library 'libgobject-2.0-0'` (macOS)**

WeasyPrint needs Homebrew's Pango libraries on the dynamic linker path. Use `run.sh` instead of calling `uv run autoresume` directly, or set:
```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
```

**PDF is more than one page**

AutoResume will try four levels of typographic compression. If your resume still exceeds one page, trim content: aim for ≤6 bullet points per job and keep each bullet under two lines.

**Docker: TUI does not render / looks broken**

Run with `-it`:
```bash
docker run -it --rm ...autoresume
```
Or with Compose:
```bash
docker compose run --rm autoresume your_resume.md
```

---

## License

MIT — see [LICENSE](LICENSE).

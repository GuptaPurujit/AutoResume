import sys
from pathlib import Path


def main() -> None:
    from .tui.app import AutoResumeApp

    resume_path: Path | None = None
    if len(sys.argv) > 1:
        resume_path = Path(sys.argv[1])
        if not resume_path.exists():
            print(f"Error: file not found: {resume_path}", file=sys.stderr)
            sys.exit(1)

    app = AutoResumeApp(resume_path=resume_path)
    app.run()


if __name__ == "__main__":
    main()

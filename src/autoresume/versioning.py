from pathlib import Path


class VersionManager:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_version(self, content: str, stem: str = "resume") -> Path:
        """Save content as the next versioned file (e.g. resume_v1.md)."""
        version = self._next_version(stem)
        path = self.output_dir / f"{stem}_v{version}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def _next_version(self, stem: str) -> int:
        existing = list(self.output_dir.glob(f"{stem}_v*.md"))
        if not existing:
            return 1
        nums: list[int] = []
        for p in existing:
            try:
                n = int(p.stem.split("_v")[-1])
                nums.append(n)
            except ValueError:
                pass
        return max(nums, default=0) + 1

    def list_versions(self, stem: str = "resume") -> list[Path]:
        return sorted(self.output_dir.glob(f"{stem}_v*.md"))

    def latest_version_path(self, stem: str = "resume") -> Path | None:
        versions = self.list_versions(stem)
        return versions[-1] if versions else None

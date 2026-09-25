"""
The image has to hold every package the app imports. `ui/` was added to the code and not to
the Dockerfile (2026-09-23), so the built image would have started — the imports that need it
are inside functions — and then failed on every recommendation.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Directories that are not the running app: tests, tooling, the frontend source, the docs.
NOT_SHIPPED = {
    "tests",
    "scripts",
    "frontend",
    "docs",
    "design",
    "data",
    "data_review",
    "handoff_output",
    "uploads",
    "web_ui_legacy",
}


def copied_paths() -> set[str]:
    lines = (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
    copied = set()
    for line in lines:
        match = re.match(r"\s*COPY\s+(?!--from)(.+?)\s+\./?", line)
        if match:
            copied.update(part.rstrip("/") for part in match.group(1).split())
    return copied


def app_packages() -> set[str]:
    return {
        path.name
        for path in ROOT.iterdir()
        if path.is_dir()
        and (path / "__init__.py").exists()
        and not path.name.startswith(".")
        and path.name not in NOT_SHIPPED
    }


def test_every_package_the_app_imports_is_in_the_image():
    missing = app_packages() - copied_paths()
    assert not missing, f"the Dockerfile doesn't copy {sorted(missing)}"


def test_the_entry_points_are_in_the_image():
    assert {"orchestrator.py", "config.py"} <= copied_paths()

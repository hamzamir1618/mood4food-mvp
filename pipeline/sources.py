"""Readers for the Phase 1 inputs: the handoff CSV and the data-sourcing project."""

import csv
import hashlib
import json

from pipeline import paths


def norm(text: str | None) -> str:
    """Lower-case and collapse whitespace, for matching names across files."""
    return " ".join((text or "").split()).lower()


def dish_uid(restaurant: str, dish: str) -> str:
    """
    Stable identifier for a dish, derived from its original restaurant and name.

    Neo4j's internal ids change on every re-seed, so anything that must refer to
    the same dish later (user history, learned preferences) uses this instead.
    """
    return hashlib.sha1(f"{norm(restaurant)}|{norm(dish)}".encode("utf-8")).hexdigest()[:12]


def read_csv(path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_handoff() -> list[dict]:
    """The 2,545-dish handoff CSV, each row tagged with its dish_uid."""
    rows = read_csv(paths.HANDOFF_CSV)
    for r in rows:
        r["dish_uid"] = dish_uid(r["restaurant_name"], r["dish_name"])
    return rows


def load_master() -> dict[str, dict]:
    """The sourcing project's master_menu.csv (review flags, OCR evidence), keyed by dish_uid."""
    return {dish_uid(r["restaurant_name"], r["dish_name"]): r for r in read_csv(paths.MASTER_CSV)}


def load_ocr_candidates() -> dict[str, list[dict]]:
    """Every OCR candidate from both review batches, keyed by its normalised raw OCR line."""
    by_line: dict[str, list[dict]] = {}
    for path in paths.OCR_RESULTS:
        if not path.exists():
            continue
        for folder, fd in json.loads(path.read_text(encoding="utf-8")).items():
            for image, idata in (fd.get("images") or {}).items():
                for c in (idata or {}).get("candidates") or []:
                    entry = dict(c, _folder=folder, _image=image)
                    by_line.setdefault(norm(c.get("raw_line")), []).append(entry)
    return by_line

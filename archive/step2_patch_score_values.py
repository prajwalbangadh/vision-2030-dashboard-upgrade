from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\PBA96B\OneDrive - AdventHealth\Documents\DATA LINK LAYER EXTRACTION")
SITE = ROOT / "vision2030_contemporary_site"
TEMPLATES = SITE / "templates"
NAMES = ("briefing.html", "insights.html", "data_explorer.html")

OLD = "const scoreVal={green:100,yellow:73,red:30};"
NEW = "const scoreVal={green:100,red:0};"


def main() -> None:
    paths = [TEMPLATES / name for name in NAMES]

    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Template not found: {path}")

    states: dict[Path, str] = {}

    for path in paths:
        text = path.read_text(encoding="utf-8-sig")
        old_count = text.count(OLD)
        new_count = text.count(NEW)

        if old_count == 1 and new_count == 0:
            states[path] = "patch"
        elif old_count == 0 and new_count == 1:
            states[path] = "done"
        else:
            raise RuntimeError(
                f"Unexpected score-value state in {path.name}: "
                f"old={old_count}, new={new_count}. No files changed."
            )

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup = SITE / "template_backups" / f"{stamp}_before_score_values"
    backup.mkdir(parents=True, exist_ok=False)

    for path in paths:
        shutil.copy2(path, backup / path.name)

    changed: list[Path] = []

    try:
        for path, state in states.items():
            if state == "done":
                continue

            text = path.read_text(encoding="utf-8-sig")
            updated = text.replace(OLD, NEW, 1)
            temporary = path.with_suffix(".html.tmp")
            temporary.write_text(updated, encoding="utf-8")
            temporary.replace(path)
            changed.append(path)

        for path in paths:
            installed = path.read_text(encoding="utf-8-sig")

            if installed.count(OLD) != 0 or installed.count(NEW) != 1:
                raise RuntimeError(f"Post-patch validation failed: {path}")
    except Exception:
        for path in paths:
            shutil.copy2(backup / path.name, path)
        raise

    print("PASS: Numeric status scoring now uses green and red only.")
    print(f"Templates changed: {len(changed)}")
    print(f"Rollback backup: {backup}")

    for path in paths:
        print(f"Validated: {path}")


if __name__ == "__main__":
    main()

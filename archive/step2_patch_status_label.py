from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\PBA96B\OneDrive - AdventHealth\Documents\DATA LINK LAYER EXTRACTION")
SITE = ROOT / "vision2030_contemporary_site"
TEMPLATES = SITE / "templates"
NAMES = ("briefing.html", "insights.html", "data_explorer.html")
OLD = "function txStatusLabel(st){return st==='green'?'At goal':st==='yellow'?'Approaching':st==='red'?'Below goal':'Not reported';}"
NEW = "function txStatusLabel(st){return st==='green'?'At goal':st==='red'?'Below goal':'Not reported';}"


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
                f"Unexpected status-label state in {path.name}: old={old_count}, new={new_count}. No files changed."
            )

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup = SITE / "template_backups" / f"{stamp}_before_status_label"
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
            temp = path.with_suffix(".html.tmp")
            temp.write_text(updated, encoding="utf-8")
            temp.replace(path)
            changed.append(path)

        for path in paths:
            text = path.read_text(encoding="utf-8-sig")
            if text.count(OLD) != 0 or text.count(NEW) != 1:
                raise RuntimeError(f"Validation failed: {path}")
    except Exception:
        for path in paths:
            shutil.copy2(backup / path.name, path)
        raise

    print("PASS: Status labels now use At goal, Below goal, and Not reported.")
    print(f"Templates changed: {len(changed)}")
    print(f"Rollback backup: {backup}")
    for path in paths:
        print(f"Validated: {path}")


if __name__ == "__main__":
    main()

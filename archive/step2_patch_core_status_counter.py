from __future__ import annotations

import hashlib
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\PBA96B\OneDrive - AdventHealth\Documents\DATA LINK LAYER EXTRACTION")
SITE_FOLDER = PROJECT_ROOT / "vision2030_contemporary_site"
TEMPLATE_FOLDER = SITE_FOLDER / "templates"
TEMPLATE_NAMES = ("briefing.html", "insights.html", "data_explorer.html")

OLD_TEXT = "function counts(id){const s=md(id).scores;let g=0,y=0,r=0,na=0;MK.forEach(k=>{const v=s[k];if(v==='green')g++;else if(v==='yellow')y++;else if(v==='red')r++;else na++;});return{g,y,r,na,scored:g+y+r};}"
NEW_TEXT = "function counts(id){const s=md(id).scores;let g=0,r=0,na=0;MK.forEach(k=>{const v=s[k];if(v==='green')g++;else if(v==='red')r++;else na++;});return{g,y:0,r,na,scored:g+r,total:g+r+na};}"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    templates = [TEMPLATE_FOLDER / name for name in TEMPLATE_NAMES]

    for template in templates:
        if not template.is_file():
            raise FileNotFoundError(f"Template not found: {template}")

    states: dict[Path, str] = {}
    for template in templates:
        content = template.read_text(encoding="utf-8-sig")
        old_count = content.count(OLD_TEXT)
        new_count = content.count(NEW_TEXT)

        if old_count == 1 and new_count == 0:
            states[template] = "needs_patch"
        elif old_count == 0 and new_count == 1:
            states[template] = "already_patched"
        else:
            raise RuntimeError(
                f"Unexpected counts-function state in {template.name}: "
                f"old={old_count}, new={new_count}. No files were changed."
            )

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_folder = SITE_FOLDER / "template_backups" / f"{timestamp}_before_core_status_counter"
    backup_folder.mkdir(parents=True, exist_ok=False)

    original_hashes: dict[Path, str] = {}
    for template in templates:
        backup = backup_folder / template.name
        shutil.copy2(template, backup)
        original_hashes[template] = sha256(template)
        if sha256(backup) != original_hashes[template]:
            raise RuntimeError(f"Backup hash verification failed: {backup}")

    changed: list[Path] = []
    try:
        for template, state in states.items():
            if state == "already_patched":
                continue

            content = template.read_text(encoding="utf-8-sig")
            updated = content.replace(OLD_TEXT, NEW_TEXT, 1)
            temporary = template.with_suffix(".html.tmp")
            temporary.write_text(updated, encoding="utf-8")
            temporary.replace(template)
            changed.append(template)

        for template in templates:
            installed = template.read_text(encoding="utf-8-sig")
            if installed.count(OLD_TEXT) != 0 or installed.count(NEW_TEXT) != 1:
                raise RuntimeError(f"Post-patch validation failed: {template}")
    except Exception:
        for template in templates:
            shutil.copy2(backup_folder / template.name, template)
        raise

    print("PASS: Core status counter is installed in all three templates.")
    print(f"Templates changed: {len(changed)}")
    print(f"Rollback backup: {backup_folder}")
    for template in templates:
        print(f"Validated: {template}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

SITE = Path(r"C:\Users\PBA96B\OneDrive - AdventHealth\Documents\DATA LINK LAYER EXTRACTION\vision2030_contemporary_site")
RUNNER = SITE / "run_vision2030.py"
TEMPLATES = SITE / "templates"
PAGES = ("briefing.html", "insights.html", "data_explorer.html")

RUNNER_OLD = "return f'{div} Region Rollup'"
RUNNER_NEW = "return f'{div} Reporting Hierarchy'"

HTML_OLD = '''    <select id="scopeSelect" aria-hidden="true" tabindex="-1" style="display:none"></select>
    <span class="scope-kind system" id="scopeKind">System</span>'''

HTML_NEW = '''    <select id="scopeSelect" aria-hidden="true" tabindex="-1" style="display:none"></select>
    <button type="button" class="reset-view-btn" id="resetViewBtn" aria-label="Reset to AdventHealth System">Reset View</button>
    <span class="scope-kind system" id="scopeKind">System</span>'''

EVENT_OLD = '''  locationSel.addEventListener('change',()=>{
    sel.value=locationSel.value;
    render(locationSel.value||'SYS');
  });
  sel.addEventListener('change',()=>selectScope(sel.value,true));'''

EVENT_NEW = '''  locationSel.addEventListener('change',()=>{
    sel.value=locationSel.value;
    render(locationSel.value||'SYS');
  });
  const resetViewBtn=document.getElementById('resetViewBtn');
  resetViewBtn.addEventListener('click',()=>selectScope('SYS',true));
  sel.addEventListener('change',()=>selectScope(sel.value,true));'''

CSS_MARKER = ".cascade-field:last-of-type .scope-select{width:100%;max-width:none;}"
CSS_ADD = '''
.reset-view-btn{font-family:inherit;font-size:12px;font-weight:700;color:var(--primary);background:var(--paper-warm);border:1px solid var(--primary);border-radius:7px;padding:9px 13px;cursor:pointer;white-space:nowrap;}
.reset-view-btn:hover{color:#fff;background:var(--primary);}
.reset-view-btn:focus{outline:2px solid var(--ah-blue-bright);outline-offset:1px;}
'''


def require_once(source: str, needle: str, label: str) -> None:
    count = source.count(needle)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}.")


def patch_runner(source: str) -> str:
    if RUNNER_NEW in source and RUNNER_OLD not in source:
        return source
    require_once(source, RUNNER_OLD, "Runner reporting-hierarchy label")
    return source.replace(RUNNER_OLD, RUNNER_NEW, 1)


def patch_template(source: str, page_name: str) -> str:
    updated = source

    if 'id="resetViewBtn"' not in updated:
        require_once(updated, HTML_OLD, f"{page_name} reset-button insertion point")
        updated = updated.replace(HTML_OLD, HTML_NEW, 1)
    elif updated.count('id="resetViewBtn"') != 1:
        raise RuntimeError(f"{page_name}: resetViewBtn must exist exactly once.")

    if ".reset-view-btn{" not in updated:
        require_once(updated, CSS_MARKER, f"{page_name} reset-button CSS marker")
        updated = updated.replace(CSS_MARKER, CSS_MARKER + CSS_ADD, 1)

    if "resetViewBtn.addEventListener('click'" not in updated:
        require_once(updated, EVENT_OLD, f"{page_name} reset-button event insertion point")
        updated = updated.replace(EVENT_OLD, EVENT_NEW, 1)

    if updated.count('id="resetViewBtn"') != 1:
        raise RuntimeError(f"{page_name}: reset button HTML validation failed.")
    if updated.count("resetViewBtn.addEventListener('click'") != 1:
        raise RuntimeError(f"{page_name}: reset button event validation failed.")
    if updated.count("selectScope('SYS',true)") < 1:
        raise RuntimeError(f"{page_name}: System reset target is missing.")

    return updated


def write_atomic(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    required = [RUNNER, *(TEMPLATES / name for name in PAGES)]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required files: " + ", ".join(missing))

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup = SITE / "reset_label_backups" / timestamp
    backup_templates = backup / "templates"
    backup_templates.mkdir(parents=True, exist_ok=False)
    shutil.copy2(RUNNER, backup / RUNNER.name)
    for name in PAGES:
        shutil.copy2(TEMPLATES / name, backup_templates / name)

    original_runner = RUNNER.read_text(encoding="utf-8")
    original_pages = {
        name: (TEMPLATES / name).read_text(encoding="utf-8")
        for name in PAGES
    }

    try:
        updated_runner = patch_runner(original_runner)
        updated_pages = {
            name: patch_template(original_pages[name], name)
            for name in PAGES
        }

        write_atomic(RUNNER, updated_runner)
        for name in PAGES:
            write_atomic(TEMPLATES / name, updated_pages[name])

        installed_runner = RUNNER.read_text(encoding="utf-8")
        if RUNNER_OLD in installed_runner or RUNNER_NEW not in installed_runner:
            raise RuntimeError("Runner label replacement validation failed.")

        for name in PAGES:
            installed = (TEMPLATES / name).read_text(encoding="utf-8")
            if installed.count('id="resetViewBtn"') != 1:
                raise RuntimeError(f"{name}: installed reset button count is invalid.")
            if installed.count("resetViewBtn.addEventListener('click'") != 1:
                raise RuntimeError(f"{name}: installed reset event count is invalid.")
    except Exception:
        shutil.copy2(backup / RUNNER.name, RUNNER)
        for name in PAGES:
            shutil.copy2(backup_templates / name, TEMPLATES / name)
        raise

    print("PASS: Reset View and reporting-hierarchy labels were installed.")
    print(f"Rollback backup: {backup}")
    print(f"Updated runner: {RUNNER}")
    for name in PAGES:
        print(f"Updated template: {TEMPLATES / name}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\PBA96B\OneDrive - AdventHealth\Documents\DATA LINK LAYER EXTRACTION")
SITE = ROOT / "vision2030_contemporary_site"
TEMPLATES = SITE / "templates"
NAMES = ("briefing.html", "insights.html", "data_explorer.html")

REPLACEMENTS = (
    (
        "const oppMs=opps.slice(0,3).map(o=>'<div class=\"ms '+(o.st==='red'?'bad':'warn')+'\"><div class=\"v\">'+o.v+'</div><div class=\"l\">'+o.k+'</div></div>').join('')||'<div class=\"ms good\"><div class=\"v\">✓</div><div class=\"l\">All metrics at goal</div></div>';",
        "const oppMs=opps.slice(0,3).map(o=>'<div class=\"ms bad\"><div class=\"v\">'+o.v+'</div><div class=\"l\">'+o.k+'</div></div>').join('')||'<div class=\"ms good\"><div class=\"v\">✓</div><div class=\"l\">No below-goal metrics</div></div>';",
        "below-goal card status",
    ),
    (
        "// near-goal (yellow) list for watch",
        "// not-reported (gray or missing) list for data coverage",
        "story comment",
    ),
    (
        "const s=md(id).scores,v=md(id).values; const yellows=MK.filter(k=>s[k]==='yellow');",
        "const s=md(id).scores,v=md(id).values; const notReported=MK.filter(k=>s[k]!=='green'&&s[k]!=='red');",
        "not-reported list",
    ),
    (
        "const watchMs=yellows.slice(0,3).map(k=>'<div class=\"ms warn\"><div class=\"v\">'+v[k]+'</div><div class=\"l\">'+k+'</div></div>').join('')||'<div class=\"ms good\"><div class=\"v\">✓</div><div class=\"l\">Nothing on the edge</div></div>';",
        "const watchMs=notReported.slice(0,3).map(k=>'<div class=\"ms\"><div class=\"v\">'+v[k]+'</div><div class=\"l\">'+k+'</div></div>').join('')||'<div class=\"ms good\"><div class=\"v\">✓</div><div class=\"l\">All metrics reported</div></div>';",
        "not-reported cards",
    ),
    (
        "cards+='<div class=\"story watch\"><span class=\"tag\">Watch · Close the gap</span><h3>The near-goal metrics are within reach.</h3><div class=\"ministat\">'+watchMs+'</div><div class=\"body\"><p>'+(yellows.length?('<b>'+yellows.length+' metric'+(yellows.length>1?'s sit':' sits')+' at yellow</b> — approaching, not failing. These are the shortest path to lifting '+nm+\"'s aspiration achievement before year-end.\"):('Nothing is sitting on the edge for '+nm+' — the board is decisively green or red.'))+'</p></div></div>';",
        "cards+='<div class=\"story watch\"><span class=\"tag\">Data coverage · Not reported</span><h3>Metrics without a reported status.</h3><div class=\"ministat\">'+watchMs+'</div><div class=\"body\"><p>'+(notReported.length?('<b>'+notReported.length+' metric'+(notReported.length>1?'s are':' is')+' not reported</b> for '+nm+'. These metrics are excluded from the scored denominator.'):('All metrics have a reported status for '+nm+'.'))+'</p></div></div>';",
        "data-coverage story",
    ),
)


def main() -> None:
    paths = [TEMPLATES / name for name in NAMES]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Template not found: {path}")

    states: dict[Path, str] = {}
    for path in paths:
        text = path.read_text(encoding="utf-8-sig")
        old_counts = [text.count(old) for old, _, _ in REPLACEMENTS]
        new_counts = [text.count(new) for _, new, _ in REPLACEMENTS]
        if all(count == 1 for count in old_counts) and all(count == 0 for count in new_counts):
            states[path] = "patch"
        elif all(count == 0 for count in old_counts) and all(count == 1 for count in new_counts):
            states[path] = "done"
        else:
            details = ", ".join(
                f"{label}:old={old_count},new={new_count}"
                for (_, _, label), old_count, new_count in zip(REPLACEMENTS, old_counts, new_counts)
            )
            raise RuntimeError(f"Unexpected story-status state in {path.name}: {details}. No files changed.")

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup = SITE / "template_backups" / f"{stamp}_before_story_statuses"
    backup.mkdir(parents=True, exist_ok=False)
    for path in paths:
        shutil.copy2(path, backup / path.name)

    changed: list[Path] = []
    try:
        for path, state in states.items():
            if state == "done":
                continue
            text = path.read_text(encoding="utf-8-sig")
            for old, new, _ in REPLACEMENTS:
                text = text.replace(old, new, 1)
            temp = path.with_suffix(".html.tmp")
            temp.write_text(text, encoding="utf-8")
            temp.replace(path)
            changed.append(path)

        for path in paths:
            text = path.read_text(encoding="utf-8-sig")
            for old, new, label in REPLACEMENTS:
                if text.count(old) != 0 or text.count(new) != 1:
                    raise RuntimeError(f"Post-patch validation failed for {label} in {path.name}")
    except Exception:
        for path in paths:
            shutil.copy2(backup / path.name, path)
        raise

    print("PASS: Story cards now use below-goal and not-reported statuses only.")
    print(f"Templates changed: {len(changed)}")
    print(f"Rollback backup: {backup}")
    for path in paths:
        print(f"Validated: {path}")


if __name__ == "__main__":
    main()

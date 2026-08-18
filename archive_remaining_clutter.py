from __future__ import annotations

import csv
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\PBA96B\OneDrive - AdventHealth\Documents\DATA LINK LAYER EXTRACTION")
ARCHIVE = ROOT / "archive"
SITE = ROOT / "vision2030_contemporary_site"
STAMP = datetime.now().strftime("%Y-%m-%d_%H%M%S")

DESTINATIONS = {
    "legacy": ARCHIVE / "legacy_sites",
    "packages": ARCHIVE / "packages",
    "rollbacks": ARCHIVE / "website_rollbacks" / STAMP,
    "development": ARCHIVE / "development_artifacts" / STAMP,
}

PROTECTED = [
    ROOT / "vision2030_extraction.py",
    ROOT / "sandbox_updated_v3.py",
    ROOT / "Vision 2030 Metrics_YTD June 2026 Report.xlsx",
    ROOT / "output" / "2026-08-17_093557" / "vision2030_business_table_2026-08-17_093557.xlsx",
    SITE / "run_vision2030.py",
    SITE / "templates" / "briefing.html",
    SITE / "templates" / "insights.html",
    SITE / "templates" / "data_explorer.html",
    SITE / "reset_label_backups" / "2026-08-17_150009" / "run_vision2030.py",
]

MOVES = [
    (ROOT / "vision2030_dynamic_site", DESTINATIONS["legacy"] / "vision2030_dynamic_site", "Legacy site"),
    (ROOT / "vision2030_static_site", DESTINATIONS["legacy"] / "vision2030_static_site", "Legacy site"),
    (ROOT / "vision2030_certified_updater", DESTINATIONS["legacy"] / "vision2030_certified_updater", "Legacy updater"),
    (ROOT / "vision2030_contemporary_site.zip", DESTINATIONS["packages"] / "vision2030_contemporary_site.zip", "Package"),
    (ROOT / "vision2030_dynamic_site.zip", DESTINATIONS["packages"] / "vision2030_dynamic_site.zip", "Package"),
    (ROOT / "vision2030_static_site.zip", DESTINATIONS["packages"] / "vision2030_static_site.zip", "Package"),
    (ROOT / "vision2030_certified_updater.zip", DESTINATIONS["packages"] / "vision2030_certified_updater.zip", "Package"),
    (SITE / "template_backups", DESTINATIONS["rollbacks"] / "template_backups", "Website rollback"),
    (SITE / "runner_backups", DESTINATIONS["rollbacks"] / "runner_backups", "Website rollback"),
    (ROOT / "GetAllMetricsWithLinks_response.txt", DESTINATIONS["development"] / "GetAllMetricsWithLinks_response.txt", "Development artifact"),
    (ROOT / "vision 2030.txt", DESTINATIONS["development"] / "vision 2030.txt", "Development artifact"),
    (ROOT / "html pages", DESTINATIONS["development"] / "html pages", "Development artifact"),
    (ROOT / "page 1.txt", DESTINATIONS["development"] / "page 1.txt", "Development artifact"),
    (ROOT / "page 2.txt", DESTINATIONS["development"] / "page 2.txt", "Development artifact"),
    (ROOT / "page 3.txt", DESTINATIONS["development"] / "page 3.txt", "Development artifact"),
    (ROOT / "create_project_inventory.py", DESTINATIONS["development"] / "create_project_inventory.py", "Inventory artifact"),
    (ROOT / "project_inventory_2026-08-17_152352.csv", DESTINATIONS["development"] / "project_inventory_2026-08-17_152352.csv", "Failed inventory artifact"),
    (ROOT / "project_tree_2026-08-17_152352.txt", DESTINATIONS["development"] / "project_tree_2026-08-17_152352.txt", "Failed inventory artifact"),
    (ROOT / "project_inventory_2026-08-17_152505.csv", DESTINATIONS["development"] / "project_inventory_2026-08-17_152505.csv", "Inventory artifact"),
    (ROOT / "project_tree_2026-08-17_152505.txt", DESTINATIONS["development"] / "project_tree_2026-08-17_152505.txt", "Inventory artifact"),
    (ROOT / "project_summary_2026-08-17_152505.txt", DESTINATIONS["development"] / "project_summary_2026-08-17_152505.txt", "Inventory artifact"),
    (SITE / "apply_reset_and_reporting_labels.py", DESTINATIONS["development"] / "apply_reset_and_reporting_labels.py", "One-time patch"),
    (SITE / "inspect_briefing_selector.py", DESTINATIONS["development"] / "inspect_briefing_selector.py", "Inspection artifact"),
    (SITE / "patch_selector_metadata.py", DESTINATIONS["development"] / "patch_selector_metadata.py", "One-time patch"),
    (SITE / "briefing_selector_sections.txt", DESTINATIONS["development"] / "briefing_selector_sections.txt", "Inspection artifact"),
]

for backup in sorted(SITE.glob("run_vision2030_backup_*.py")):
    MOVES.append((backup, DESTINATIONS["rollbacks"] / backup.name, "Website rollback"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if not ROOT.is_dir():
        raise FileNotFoundError(f"Project root not found: {ROOT}")

    for path in PROTECTED:
        if not path.is_file():
            raise FileNotFoundError(f"Protected file missing before cleanup: {path}")

    protected_hashes = {path: sha256(path) for path in PROTECTED}
    plan = [(src, dst, category) for src, dst, category in MOVES if src.exists()]

    for _, destination, _ in plan:
        if destination.exists():
            raise FileExistsError(f"Destination already exists: {destination}")

    moved: list[tuple[Path, Path, str]] = []
    try:
        for source, destination, category in plan:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            if source.exists() or not destination.exists():
                raise RuntimeError(f"Move verification failed: {source}")
            moved.append((source, destination, category))

        for path, previous_hash in protected_hashes.items():
            if not path.is_file() or sha256(path) != previous_hash:
                raise RuntimeError(f"Protected file changed or disappeared: {path}")

        active_outputs = [path.name for path in (ROOT / "output").iterdir() if path.is_dir()]
        if active_outputs != ["2026-08-17_093557"]:
            raise RuntimeError(f"Unexpected active output folders: {active_outputs}")

        manifest = ARCHIVE / f"cleanup_move_manifest_{STAMP}.csv"
        with manifest.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Category", "Source", "Destination", "Status"])
            for source, destination, category in moved:
                writer.writerow([category, source, destination, "MOVED"])
    except Exception:
        for source, destination, _ in reversed(moved):
            if destination.exists() and not source.exists():
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(destination), str(source))
        raise

    print("PASS: Remaining clutter was archived.")
    print(f"Items moved: {len(moved)}")
    print(f"Manifest: {manifest}")
    print("No files were deleted.")
    print("All protected files remain hash-identical.")


if __name__ == "__main__":
    main()

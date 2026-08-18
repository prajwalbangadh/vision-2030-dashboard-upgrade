from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(
    r"C:\Users\PBA96B\OneDrive - AdventHealth\Documents\DATA LINK LAYER EXTRACTION"
)

EXCLUDED_DIRECTORIES = {
    ".venv",
    ".git",
    "__pycache__",
}

TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H%M%S")

INVENTORY_FILE = PROJECT_ROOT / f"project_inventory_{TIMESTAMP}.csv"
TREE_FILE = PROJECT_ROOT / f"project_tree_{TIMESTAMP}.txt"
SUMMARY_FILE = PROJECT_ROOT / f"project_summary_{TIMESTAMP}.txt"


def classify(path: Path, relative_path: Path) -> str:
    relative_text = str(relative_path).replace("/", "\\")
    relative_lower = relative_text.casefold()
    name_lower = path.name.casefold()

    if path.is_dir():
        return "Directory"

    if path.name == "vision2030_extraction.py":
        return "LOCKED MAIN EXTRACTOR"

    if path.name == "sandbox_updated_v3.py":
        return "ACTIVE SANDBOX"

    if path.name == "sandbox.py":
        return "LEGACY SANDBOX - DO NOT USE"

    if (
        path.name == "run_vision2030.py"
        and "vision2030_contemporary_site" in relative_lower
    ):
        return "ACTIVE WEBSITE RUNNER"

    if "\\templates\\" in f"\\{relative_lower}\\":
        return "ACTIVE WEBSITE TEMPLATE"

    if "\\generated\\" in f"\\{relative_lower}\\":
        return "GENERATED WEBSITE ARTIFACT"

    if "\\output\\" in f"\\{relative_lower}\\":
        return "EXTRACTION OUTPUT"

    if "\\template_backups\\" in f"\\{relative_lower}\\":
        return "TEMPLATE BACKUP"

    if "\\runner_backups\\" in f"\\{relative_lower}\\":
        return "RUNNER BACKUP"

    if "\\reset_label_backups\\" in f"\\{relative_lower}\\":
        return "RESET LABEL BACKUP"

    if name_lower.startswith("run_vision2030_backup_") and path.suffix == ".py":
        return "RUNNER BACKUP"

    if name_lower.startswith("apply_") and path.suffix == ".py":
        return "ONE-TIME PATCH SCRIPT"

    if name_lower.startswith("inspect_") and path.suffix == ".py":
        return "INSPECTION SCRIPT"

    if name_lower.startswith("check_") and path.suffix == ".py":
        return "VALIDATION SCRIPT"

    if name_lower.startswith("project_inventory_") and path.suffix == ".csv":
        return "INVENTORY ARTIFACT"

    if name_lower.startswith("project_tree_") and path.suffix == ".txt":
        return "INVENTORY ARTIFACT"

    if name_lower.startswith("project_summary_") and path.suffix == ".txt":
        return "INVENTORY ARTIFACT"

    if path.name == "create_project_inventory.py":
        return "INVENTORY SCRIPT"

    if path.name.startswith("~$"):
        return "OFFICE TEMPORARY FILE"

    if name_lower.endswith(".html.tmp") or path.suffix.casefold() == ".tmp":
        return "TEMPORARY FILE"

    if path.suffix.casefold() == ".zip":
        return "ARCHIVE OR PACKAGE"

    if path.suffix.casefold() == ".xlsx":
        return "EXCEL WORKBOOK"

    if path.suffix.casefold() == ".html":
        return "HTML FILE"

    if path.suffix.casefold() == ".py":
        return "PYTHON SCRIPT"

    return "UNCLASSIFIED"


def should_exclude(path: Path) -> bool:
    try:
        relative_parts = path.relative_to(PROJECT_ROOT).parts
    except ValueError:
        return True

    return any(part in EXCLUDED_DIRECTORIES for part in relative_parts)


def collect_inventory() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    for path in sorted(
        PROJECT_ROOT.rglob("*"),
        key=lambda item: str(item).casefold(),
    ):
        if should_exclude(path):
            continue

        relative_path = path.relative_to(PROJECT_ROOT)
        is_directory = path.is_dir()
        size_bytes = 0 if is_directory else path.stat().st_size

        records.append(
            {
                "ItemType": "Directory" if is_directory else "File",
                "Classification": classify(path, relative_path),
                "Name": path.name,
                "Extension": "" if is_directory else path.suffix,
                "RelativePath": str(relative_path),
                "FullPath": str(path),
                "SizeBytes": size_bytes,
                "SizeMB": round(size_bytes / (1024 * 1024), 4),
                "Created": datetime.fromtimestamp(
                    path.stat().st_ctime
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "LastModified": datetime.fromtimestamp(
                    path.stat().st_mtime
                ).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return records


def write_inventory(records: list[dict[str, object]]) -> None:
    fieldnames = [
        "ItemType",
        "Classification",
        "Name",
        "Extension",
        "RelativePath",
        "FullPath",
        "SizeBytes",
        "SizeMB",
        "Created",
        "LastModified",
    ]

    with INVENTORY_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(records)


def write_tree(records: list[dict[str, object]]) -> None:
    lines = ["DATA LINK LAYER EXTRACTION", ""]

    for record in sorted(
        records,
        key=lambda item: str(item["RelativePath"]).casefold(),
    ):
        relative_path = Path(str(record["RelativePath"]))
        depth = max(len(relative_path.parts) - 1, 0)
        indent = "    " * depth

        if record["ItemType"] == "Directory":
            line = (
                f"{indent}[DIR] {record['Name']} "
                f"| {record['Classification']}"
            )
        else:
            line = (
                f"{indent}[FILE] {record['Name']} "
                f"[{float(record['SizeMB']):.4f} MB] "
                f"| {record['Classification']}"
            )

        lines.append(line)

    TREE_FILE.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def write_summary(records: list[dict[str, object]]) -> None:
    file_records = [
        record
        for record in records
        if record["ItemType"] == "File"
    ]

    directory_records = [
        record
        for record in records
        if record["ItemType"] == "Directory"
    ]

    total_size_bytes = sum(
        int(record["SizeBytes"])
        for record in file_records
    )

    classification_counts = Counter(
        str(record["Classification"])
        for record in file_records
    )

    classification_sizes: defaultdict[str, int] = defaultdict(int)

    for record in file_records:
        classification_sizes[str(record["Classification"])] += int(
            record["SizeBytes"]
        )

    extension_counts = Counter(
        str(record["Extension"]) or "[no extension]"
        for record in file_records
    )

    protected_paths = [
        PROJECT_ROOT / "vision2030_extraction.py",
        PROJECT_ROOT / "sandbox_updated_v3.py",
        PROJECT_ROOT
        / "vision2030_contemporary_site"
        / "run_vision2030.py",
    ]

    lines = [
        "DATA LINK LAYER EXTRACTION PROJECT INVENTORY",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Root: {PROJECT_ROOT}",
        "",
        f"Directories scanned: {len(directory_records)}",
        f"Files scanned: {len(file_records)}",
        (
            "Total file size excluding .venv, .git, and "
            f"__pycache__: {total_size_bytes / (1024 * 1024):.2f} MB"
        ),
        "",
        "CLASSIFICATION SUMMARY",
    ]

    for classification, count in sorted(
        classification_counts.items(),
        key=lambda item: (-item[1], item[0].casefold()),
    ):
        size_mb = (
            classification_sizes[classification]
            / (1024 * 1024)
        )

        lines.append(
            f"{classification:<34} "
            f"Files: {count:>6}  "
            f"Size: {size_mb:>12.2f} MB"
        )

    lines.extend(
        [
            "",
            "EXTENSION SUMMARY",
        ]
    )

    for extension, count in sorted(
        extension_counts.items(),
        key=lambda item: (-item[1], item[0].casefold()),
    ):
        lines.append(
            f"{extension:<20} Files: {count:>6}"
        )

    lines.extend(
        [
            "",
            "PROTECTED FILE CHECK",
        ]
    )

    for protected_path in protected_paths:
        lines.append(
            f"{protected_path} | Exists: {protected_path.is_file()}"
        )

    lines.extend(
        [
            "",
            "IMPORTANT",
            "This inventory operation did not move, rename, edit, archive, "
            "or delete any existing project file.",
        ]
    )

    SUMMARY_FILE.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def verify_outputs() -> None:
    for output_file in (
        INVENTORY_FILE,
        TREE_FILE,
        SUMMARY_FILE,
    ):
        if not output_file.is_file():
            raise RuntimeError(
                f"Required output was not created: {output_file}"
            )

        if output_file.stat().st_size <= 0:
            raise RuntimeError(
                f"Required output is empty: {output_file}"
            )


def main() -> None:
    if not PROJECT_ROOT.is_dir():
        raise FileNotFoundError(
            f"Project folder not found: {PROJECT_ROOT}"
        )

    records = collect_inventory()

    if not records:
        raise RuntimeError(
            "No project items were found."
        )

    write_inventory(records)
    write_tree(records)
    write_summary(records)
    verify_outputs()

    file_count = sum(
        record["ItemType"] == "File"
        for record in records
    )

    directory_count = sum(
        record["ItemType"] == "Directory"
        for record in records
    )

    total_size_mb = sum(
        int(record["SizeBytes"])
        for record in records
        if record["ItemType"] == "File"
    ) / (1024 * 1024)

    print("PASS: Read-only project inventory completed.")
    print("No existing project file was moved, renamed, edited, or deleted.")
    print(f"Inventory CSV: {INVENTORY_FILE}")
    print(f"Project tree:  {TREE_FILE}")
    print(f"Summary:       {SUMMARY_FILE}")
    print(f"Files scanned: {file_count}")
    print(f"Directories:   {directory_count}")
    print(f"Total size:    {total_size_mb:.2f} MB")


if __name__ == "__main__":
    main()

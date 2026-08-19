#!/usr/bin/env python3
"""Build a sidecar Division matching audit without modifying the source workbook."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "vision2030_contemporary_site"
sys.path.insert(0, str(SITE))
from site_builder import division_label, read_xlsx  # noqa: E402

sys.path.insert(0, str(ROOT / "reconciliation"))
from build_corrected_workbook import corrected_assignment  # noqa: E402


DETAIL_SHEETS = ("Learning", "Team", "Consumer", "Clinical", "Financial", "Risk", "WPC")


def clean(value: Any) -> str:
    return "" if value is None else " ".join(str(value).strip().split())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_stamp(path: Path) -> str:
    match = re.search(r"(\d{4}-\d{2}-\d{2}_\d{6})", path.stem)
    if not match:
        raise ValueError(f"Source workbook has no timestamp: {path}")
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT / "vision2030_business_table_2026-08-18_130253.xlsx",
    )
    parser.add_argument(
        "--rough",
        type=Path,
        default=ROOT / "output/2026-08-17_153550/vision2030_business_table_2026-08-17_153550.xlsx",
    )
    parser.add_argument(
        "--reconciliation",
        type=Path,
        default=ROOT / "reconciliation/vision2030_real_run_reconciliation_2026-08-18.csv",
    )
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    rough = args.rough.resolve()
    stamp = source_stamp(source)
    output_dir = args.output_dir or ROOT / "reconciliation" / "source_mapping" / stamp
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = output_dir / f"division_mapping_audit_{stamp}.csv"
    manifest_path = output_dir / f"source_mapping_manifest_{stamp}.json"

    source_book = read_xlsx(source)
    rough_book = read_xlsx(rough)
    with args.reconciliation.open(encoding="utf-8-sig", newline="") as handle:
        reconciliation = {
            (row["sheet"], int(row["row"])): row
            for row in csv.DictReader(handle)
        }

    audit_rows: list[dict[str, Any]] = []
    statuses: Counter[str] = Counter()
    for sheet in DETAIL_SHEETS:
        source_rows = source_book.get(sheet, [])
        rough_rows = rough_book.get(sheet, [])
        if len(source_rows) != len(rough_rows):
            raise ValueError(f"Input row mismatch on {sheet}")
        for row_number, (source_row, rough_row) in enumerate(
            zip(source_rows, rough_rows), start=2,
        ):
            matched, geography, override_status = corrected_assignment(source_row, rough_row)
            matched = division_label(matched)
            geography = division_label(geography) if geography else ""
            reference = reconciliation.get((sheet, row_number), {})
            status = override_status or clean(reference.get("mapping_status")) or "SOURCE_PRESERVED"
            confidence = clean(reference.get("confidence")) or "none"
            evidence = clean(reference.get("evidence"))
            if override_status == "ORGANIZATIONAL_PARENT_PHD":
                confidence = "high"
                evidence = clean(source_row.get("Division"))
            elif override_status == "ORGANIZATIONAL_PARENT_CORPORATE_SERVICES":
                confidence = "high"
                evidence = clean(source_row.get("Division"))
            elif override_status == "CONFIRMED_LOCATION_ALIAS":
                confidence = "high"
                evidence = "UCM AH Glen Oaks (June report MSD 2 sheet)"
            statuses[status] += 1
            audit_rows.append({
                "Workbook Sheet": sheet,
                "Workbook Row": row_number,
                "Metric": clean(source_row.get("Metric")),
                "Level": clean(source_row.get("Level")),
                "Location Type": clean(source_row.get("Location Type")),
                "Location": clean(source_row.get("Location")),
                "Original Division": clean(source_row.get("Division")) or "N/A",
                "Matched Division": matched,
                "Report Geography": geography or "N/A",
                "Mapping Status": status,
                "Confidence": confidence,
                "Matched Evidence": evidence or "N/A",
                "Hierarchy Path": clean(reference.get("hierarchy_path")) or "N/A",
            })

    if len(audit_rows) != 6824:
        raise ValueError(f"Expected 6,824 audit rows, found {len(audit_rows)}")

    source_hash_before = sha256(source)
    with audit_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)
    source_hash_after = sha256(source)
    if source_hash_before != source_hash_after:
        raise RuntimeError("Source workbook changed while creating its sidecar audit")

    manifest = {
        "schemaVersion": 1,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "sourceWorkbook": str(source.relative_to(ROOT)),
        "sourceWorkbookSha256": source_hash_after,
        "sourceWorkbookModified": False,
        "roughMappingEvidence": str(rough.relative_to(ROOT)),
        "roughMappingEvidenceSha256": sha256(rough),
        "detailRows": len(audit_rows),
        "matchedDivisionDiffersFromSourceRows": sum(
            row["Original Division"] != row["Matched Division"] for row in audit_rows
        ),
        "mappingStatusCounts": dict(statuses),
        "mappingAudit": str(audit_path.relative_to(ROOT)),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(audit_path)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

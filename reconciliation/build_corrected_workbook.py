#!/usr/bin/env python3
"""Build a corrected Vision 2030 workbook without changing source values."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "vision2030_contemporary_site"
sys.path.insert(0, str(SITE))
from site_builder import read_xlsx  # noqa: E402


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
DETAIL_SHEETS = ("Learning", "Team", "Consumer", "Clinical", "Financial", "Risk", "WPC")
PHD_PARENT = "Primary Health Division Cost Centers by Reporting Hierarchy"
CORPORATE_PARENT = "Corporate Services Division Cost Centers by Reporting Hierarchy"
REPORT_DIVISIONS = {"CFD", "EFD", "WFD", "PHD", "MSD", "MSD 1", "MSD 2"}


def clean(value: Any) -> str:
    return "" if value is None else " ".join(str(value).strip().split())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sheet_targets(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
    result = {}
    for sheet in workbook.find(f"{{{MAIN_NS}}}sheets"):
        target = targets[sheet.attrib[f"{{{REL_NS}}}id"]].lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        result[sheet.attrib["name"]] = target
    return result


def replace_cell_text(cell: ET.Element, value: str) -> None:
    for child in list(cell):
        cell.remove(child)
    cell.attrib["t"] = "inlineStr"
    inline = ET.SubElement(cell, f"{{{MAIN_NS}}}is")
    text = ET.SubElement(inline, f"{{{MAIN_NS}}}t")
    text.text = value


def patch_division_cells(source: Path, destination: Path, divisions: dict[str, list[str]]) -> None:
    ET.register_namespace("", MAIN_NS)
    with zipfile.ZipFile(source, "r") as original:
        targets = sheet_targets(original)
        replacements = {targets[sheet]: values for sheet, values in divisions.items()}
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for item in original.infolist():
                payload = original.read(item.filename)
                if item.filename in replacements:
                    root = ET.fromstring(payload)
                    expected = replacements[item.filename]
                    rows = root.findall(f".//{{{MAIN_NS}}}sheetData/{{{MAIN_NS}}}row")
                    detail_rows = [row for row in rows if int(row.attrib["r"]) >= 2]
                    if len(detail_rows) != len(expected):
                        raise ValueError(
                            f"Worksheet row mismatch for {item.filename}: "
                            f"{len(detail_rows)} vs {len(expected)}"
                        )
                    for row, division in zip(detail_rows, expected):
                        row_number = row.attrib["r"]
                        reference = f"C{row_number}"
                        cell = next(
                            (
                                candidate
                                for candidate in row.findall(f"{{{MAIN_NS}}}c")
                                if candidate.attrib.get("r") == reference
                            ),
                            None,
                        )
                        if cell is None:
                            cell = ET.Element(f"{{{MAIN_NS}}}c", {"r": reference})
                            inserted = False
                            for index, candidate in enumerate(row.findall(f"{{{MAIN_NS}}}c")):
                                letters = re.match(r"[A-Z]+", candidate.attrib["r"]).group()
                                if letters > "C":
                                    row.insert(index, cell)
                                    inserted = True
                                    break
                            if not inserted:
                                row.append(cell)
                        replace_cell_text(cell, division)
                    payload = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                output.writestr(item, payload)


def corrected_assignment(real: dict[str, str], rough: dict[str, str]) -> tuple[str, str, str]:
    original = clean(real.get("Division")) or "N/A"
    proposed = clean(rough.get("Division")) or original
    location = clean(real.get("Location"))

    if original == PHD_PARENT:
        geography = proposed if proposed in REPORT_DIVISIONS and proposed != "PHD" else ""
        return "PHD", geography, "ORGANIZATIONAL_PARENT_PHD"

    if original == CORPORATE_PARENT:
        geography = proposed if proposed in REPORT_DIVISIONS else ""
        return original, geography, "ORGANIZATIONAL_PARENT_CORPORATE_SERVICES"

    if location.casefold() == "ucm ah glenoaks hosp":
        return "MSD 2", "MSD 2", "CONFIRMED_LOCATION_ALIAS"

    return proposed, proposed if proposed in REPORT_DIVISIONS else "", ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--real",
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

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_dir = args.output_dir or ROOT / "output" / stamp
    output_dir.mkdir(parents=True, exist_ok=True)
    workbook_path = output_dir / f"vision2030_business_table_{stamp}.xlsx"
    audit_path = output_dir / f"division_mapping_audit_{stamp}.csv"
    manifest_path = output_dir / f"correction_manifest_{stamp}.json"

    real_book = read_xlsx(args.real)
    rough_book = read_xlsx(args.rough)
    with args.reconciliation.open(encoding="utf-8-sig", newline="") as handle:
        reconciliation = {
            (row["sheet"], int(row["row"])): row
            for row in csv.DictReader(handle)
        }

    divisions: dict[str, list[str]] = {}
    audit_rows = []
    restored_phd = restored_corporate = alias_matches = 0
    for sheet in DETAIL_SHEETS:
        real_rows = real_book.get(sheet, [])
        rough_rows = rough_book.get(sheet, [])
        if len(real_rows) != len(rough_rows):
            raise ValueError(f"Input row mismatch on {sheet}")
        divisions[sheet] = []
        for row_number, (real, rough) in enumerate(zip(real_rows, rough_rows), start=2):
            final, geography, override_status = corrected_assignment(real, rough)
            reference = reconciliation.get((sheet, row_number), {})
            status = override_status or clean(reference.get("mapping_status")) or "PRESERVED"
            evidence = clean(reference.get("evidence"))
            confidence = clean(reference.get("confidence")) or "none"
            if override_status == "ORGANIZATIONAL_PARENT_PHD":
                restored_phd += int(clean(rough.get("Division")) != "PHD")
                evidence = PHD_PARENT
                confidence = "high"
            elif override_status == "ORGANIZATIONAL_PARENT_CORPORATE_SERVICES":
                restored_corporate += int(clean(rough.get("Division")) != CORPORATE_PARENT)
                evidence = CORPORATE_PARENT
                confidence = "high"
            elif override_status == "CONFIRMED_LOCATION_ALIAS":
                alias_matches += 1
                evidence = "UCM AH Glen Oaks (June report MSD 2 sheet)"
                confidence = "high"
            divisions[sheet].append(final)
            audit_rows.append({
                "Workbook Sheet": sheet,
                "Workbook Row": row_number,
                "Metric": clean(real.get("Metric")),
                "Level": clean(real.get("Level")),
                "Location Type": clean(real.get("Location Type")),
                "Location": clean(real.get("Location")),
                "Original Division": clean(real.get("Division")) or "N/A",
                "Final Division": final,
                "Report Geography": geography or "N/A",
                "Mapping Status": status,
                "Confidence": confidence,
                "Matched Evidence": evidence or "N/A",
                "Hierarchy Path": clean(reference.get("hierarchy_path")) or "N/A",
            })

    patch_division_cells(args.real, workbook_path, divisions)
    corrected = read_xlsx(workbook_path)
    for sheet in DETAIL_SHEETS:
        if len(corrected[sheet]) != len(real_book[sheet]):
            raise ValueError(f"Corrected row mismatch on {sheet}")
        for row_number, (before, after) in enumerate(zip(real_book[sheet], corrected[sheet]), start=2):
            for field in before:
                if field == "Division":
                    continue
                if clean(before.get(field)) != clean(after.get(field)):
                    raise ValueError(
                        f"Unauthorized change: {sheet} row {row_number}, {field}: "
                        f"{before.get(field)!r} -> {after.get(field)!r}"
                    )

    if len(audit_rows) != 6824:
        raise ValueError(f"Expected 6,824 audit rows, found {len(audit_rows)}")
    if restored_phd != 100 or restored_corporate != 27 or alias_matches != 1:
        raise ValueError(
            "Correction regression failed: "
            f"PHD={restored_phd}, Corporate={restored_corporate}, aliases={alias_matches}"
        )

    with audit_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)

    manifest = {
        "schemaVersion": 1,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "realSource": str(args.real),
        "realSourceSha256": sha256(args.real),
        "roughMappingSource": str(args.rough),
        "roughMappingSourceSha256": sha256(args.rough),
        "outputWorkbook": str(workbook_path),
        "outputWorkbookSha256": sha256(workbook_path),
        "detailRows": len(audit_rows),
        "nonDivisionFieldsChanged": 0,
        "primaryHealthRowsRestored": restored_phd,
        "corporateServicesRowsRestored": restored_corporate,
        "locationAliasesApplied": alias_matches,
        "clinicalValueOverridesCopied": 0,
        "mappingAudit": str(audit_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(workbook_path)
    print(audit_path)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

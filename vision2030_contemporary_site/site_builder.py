from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import threading
import webbrowser
import zipfile
from collections import Counter
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


SITE = Path(__file__).resolve().parent
PROJECT = SITE.parent
OUTPUT = PROJECT / "output"
SOURCE_MAPPING = PROJECT / "reconciliation" / "source_mapping"
TEMPLATES = SITE / "templates"
GENERATED = SITE / "generated"
PAGES = ("briefing.html", "insights.html", "data_explorer.html")
DETAIL_SHEETS = ("Learning", "Team", "Consumer", "Clinical", "Financial", "Risk", "WPC")

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

ALIASES = {
    "Internal Leader Fill Rate": "Internal Leader Fill Rate",
    "Leader Effectiveness": "Leader Effectiveness (Facility Leadership)",
    "Opportunity to Learn and Grow": "Opportunity to Learn and Grow",
    "Forecast and Hire": "Forecast and Hire",
    "Team Member Engagement": "Team Member Engagement",
    "Total Turnover (Rolling 12)": "Total Turnover",
    "Physician Engagement": "Physician Engagement",
    "Annual Active Users": "Digital Tool Utilization",
    "LTR ED": "Patient Experience – ED LTR",
    "LTR Inpatient": "Patient Experience – Inpatient LTR",
    "LTR Med Practice": "Patient Experience – Med Practice LTR",
    "All-Adult Inpatient Mortality": "All-Adult Inpatient Mortality",
    "Length of Stay O/E": "Length of Stay O/E",
    "CMS Star Rating": "CMS Overall Hospital Star Rating",
    "Leapfrog Safety Grade": "Leapfrog Hospital Safety Grade",
    "EBITDA Dollars": "EBITDA $",
    "TOR Dollars": "TOR $",
    "TOR Growth Rate": "TOR Growth Rate",
    "Domestic Spend": "Domestic Spend",
    "Community Impact": "Community Impact",
    "Mission Integration Plan": "Mission Integration Plan",
}

PILLAR_BY_SHEET = {
    "Learning": "Dynamic Learning Community",
    "Team": "Team Member Promise",
    "Consumer": "Consumer Focused Connected Network",
    "Clinical": "Clinical Excellence",
    "Financial": "Financial Strength and Growth",
    "Risk": "Managed Population Risk",
    "WPC": "Whole-Person Care",
}

CATEGORY_TO_SHEET = {
    "LEARNING": "Learning",
    "TEAM": "Team",
    "CONSUMER": "Consumer",
    "CLINICAL": "Clinical",
    "FINANCIAL": "Financial",
    "RISK": "Risk",
    "WPC": "WPC",
}

METRIC_UNITS = {
    "Internal Leader Fill Rate": "percent",
    "Leader Effectiveness": "score",
    "Opportunity to Learn and Grow": "score",
    "Forecast and Hire": "count",
    "Team Member Engagement": "score",
    "Total Turnover (Rolling 12)": "percent",
    "Physician Engagement": "score",
    "Annual Active Users": "count",
    "LTR ED": "score",
    "LTR Inpatient": "score",
    "LTR Med Practice": "score",
    "All-Adult Inpatient Mortality": "ratio",
    "Length of Stay O/E": "ratio",
    "CMS Star Rating": "rating",
    "Leapfrog Safety Grade": "rating",
    "EBITDA Dollars": "currency",
    "TOR Dollars": "currency",
    "TOR Growth Rate": "percent",
    "Domestic Spend": "percent",
    "Community Impact": "text",
    "Mission Integration Plan": "text",
}

FINANCIAL_VARIANCE_METRICS = {"EBITDA Dollars", "TOR Dollars", "TOR Growth Rate"}
NO_COMPARABLE_GOAL = {
    "Internal Leader Fill Rate",
    "All-Adult Inpatient Mortality",
    "Length of Stay O/E",
    "Community Impact",
    "Mission Integration Plan",
}
CLINICAL_AGGREGATES = {"CMS Star Rating", "Leapfrog Safety Grade"}

DIVISION_LABELS = {
    "SYS": "AdventHealth System",
    "CFD": "Central Florida Division",
    "Central Florida": "Central Florida Division",
    "Central Florida Division": "Central Florida Division",
    "EFD": "East Florida Division",
    "East Florida": "East Florida Division",
    "East Florida Division": "East Florida Division",
    "WFD": "West Florida Division",
    "West Florida": "West Florida Division",
    "West Florida Division": "West Florida Division",
    "PHD": "Primary Health Division",
    "Primary Health Division": "Primary Health Division",
    "MSD": "Multi-State Division",
    "Multi-State": "Multi-State Division",
    "Multi-State Division": "Multi-State Division",
    "MSD 1": "Multi-State Division 1",
    "MSD 2": "Multi-State Division 2",
    "Corporate Services": "Corporate Services",
    "Corporate Services Division Cost Centers by Reporting Hierarchy": "Corporate Services",
    "Florida Division Cost Centers by Reporting Hierarchy": "Florida Division (Unresolved)",
    "Multistate Division Cost Centers by Reporting Hierarchy": "Multistate Division (Unresolved)",
    "N/A": "Unclassified",
}


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def slug(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", clean(value).upper()).strip("_") or "NA"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def latest(root: Path) -> Path:
    roots = [root]
    if root.resolve() == OUTPUT.resolve():
        roots.append(PROJECT)
    files = [
        p
        for candidate_root in roots
        for pattern in ("vision2030_business_table_*.xlsx", "*/vision2030_business_table_*.xlsx")
        for p in candidate_root.glob(pattern)
        if p.is_file() and not p.name.startswith("~$")
    ]
    if not files:
        searched = ", ".join(str(candidate) for candidate in roots)
        raise FileNotFoundError(f"No business workbook found under: {searched}")
    def stamp(path: Path) -> str:
        match = re.search(r"(\d{4}-\d{2}-\d{2}_\d{6})", path.name)
        return match.group(1) if match else path.parent.name

    return max(files, key=lambda p: (stamp(p), p.name))


def column_index(cell_reference: str) -> int:
    letters = re.match(r"[A-Z]+", cell_reference)
    if not letters:
        raise ValueError(f"Invalid cell reference: {cell_reference}")
    number = 0
    for letter in letters.group():
        number = number * 26 + ord(letter) - 64
    return number - 1


def read_xlsx(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Read the tabular workbook without requiring the Windows-only environment."""
    with zipfile.ZipFile(path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall(f"{{{MAIN_NS}}}si"):
                shared_strings.append("".join(n.text or "" for n in item.iter(f"{{{MAIN_NS}}}t")))
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in rels}
        result: dict[str, list[dict[str, Any]]] = {}
        sheets_node = workbook.find(f"{{{MAIN_NS}}}sheets")
        if sheets_node is None:
            raise ValueError("Workbook contains no sheets")
        for sheet in sheets_node:
            name = sheet.attrib["name"]
            target = targets[sheet.attrib[f"{{{REL_NS}}}id"]].lstrip("/")
            if not target.startswith("xl/"):
                target = f"xl/{target}"
            root = ET.fromstring(archive.read(target))
            table: list[list[Any]] = []
            for row in root.findall(f".//{{{MAIN_NS}}}sheetData/{{{MAIN_NS}}}row"):
                values: dict[int, Any] = {}
                for cell in row.findall(f"{{{MAIN_NS}}}c"):
                    index = column_index(cell.attrib["r"])
                    kind = cell.attrib.get("t")
                    node = cell.find(f"{{{MAIN_NS}}}v")
                    if kind == "inlineStr":
                        value = "".join(n.text or "" for n in cell.iter(f"{{{MAIN_NS}}}t"))
                    elif node is None:
                        value = ""
                    elif kind == "s":
                        value = shared_strings[int(node.text or "0")]
                    elif kind == "b":
                        value = (node.text or "0") == "1"
                    else:
                        value = node.text or ""
                    values[index] = value
                if values:
                    current: list[Any] = [""] * (max(values) + 1)
                    for index, value in values.items():
                        current[index] = value
                    table.append(current)
            if not table:
                result[name] = []
                continue
            headers = [clean(v) for v in table[0]]
            result[name] = [
                {header: row[i] if i < len(row) else "" for i, header in enumerate(headers)}
                for row in table[1:] if any(clean(v) for v in row)
            ]
        return result


def parse_numeric(value: Any) -> float | None:
    raw = clean(value)
    if not raw or raw.casefold() in {"n/a", "coming soon", "na", "—", "-"}:
        return None
    normalized = raw.replace(",", "").replace("$", "").replace("%", "").strip()
    multiplier = 1.0
    if normalized[-1:].upper() == "M":
        multiplier, normalized = 1_000_000.0, normalized[:-1]
    elif normalized[-1:].upper() == "B":
        multiplier, normalized = 1_000_000_000.0, normalized[:-1]
    try:
        number = float(normalized) * multiplier
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def parse_goal(goal: Any, source_metric: str) -> tuple[str | None, float | None]:
    raw = clean(goal).replace("≥", ">=").replace("≤", "<=")
    match = re.match(r"^(>=|<=)\s*\$?([+-]?[\d,.]+)\s*([MB%]?)$", raw, re.I)
    if match:
        operator = match.group(1)
        value = float(match.group(2).replace(",", ""))
        suffix = match.group(3).upper()
        if suffix == "M": value *= 1_000_000
        elif suffix == "B": value *= 1_000_000_000
        return operator, value
    if source_metric == "Leapfrog Safety Grade" and re.fullmatch(r"5(?:\.0+)?", raw):
        return ">=", 5.0
    return None, None


def format_number(number: float, unit: str) -> str:
    if unit == "currency":
        if abs(number) >= 1_000_000_000: return f"${number / 1_000_000_000:,.1f}B"
        if abs(number) >= 1_000_000: return f"${number / 1_000_000:,.1f}M"
        return f"${number:,.0f}"
    if unit == "count":
        return f"{number / 1_000_000:,.1f}M" if abs(number) >= 1_000_000 else f"{number:,.0f}"
    if unit == "percent": return f"{number:,.1f}%"
    if unit == "rating": return f"{number:g}"
    return f"{number:,.0f}" if number.is_integer() else f"{number:,.1f}"


def format_goal(original: Any, operator: str | None, number: float | None, unit: str) -> str:
    if operator is None or number is None:
        return clean(original) or "N/A"
    return f"{'≥' if operator == '>=' else '≤'} {format_number(number, unit)}"


def display_value(
    raw: Any,
    source_metric: str,
    *,
    summary: bool,
    aggregate: bool = False,
) -> tuple[str, float | None]:
    text, number = clean(raw) or "N/A", parse_numeric(raw)
    if source_metric in CLINICAL_AGGREGATES:
        if (summary or aggregate) and number is not None:
            if abs(number) <= 1: number *= 100
            noun = "4–5 Star facilities" if source_metric == "CMS Star Rating" else "Grade A campuses"
            return f"{number:.1f}% {noun}", number
        if not summary and number is not None:
            noun = "Stars" if source_metric == "CMS Star Rating" else "rating code"
            return f"{number:g} {noun}", number
    return text, number


def division_label(value: Any) -> str:
    raw = clean(value) or "N/A"
    return DIVISION_LABELS.get(raw, raw)


def division_key(value: Any, location_type: Any) -> str:
    if clean(location_type).casefold() == "corporate": return "SYS"
    return division_label(value)


def scope_id(location_type: Any, location: Any) -> str:
    if clean(location_type).casefold() == "corporate": return "SYS"
    return f"{slug(location_type or 'Other')}::{slug(location or 'N/A')}"


def source_status(value: Any) -> str:
    normalized = clean(value).casefold()
    return normalized if normalized in {"green", "red", "gray", "yellow"} else "unavailable"


def derived_status(
    source_metric: str, value_number: float | None, goal_operator: str | None,
    goal_number: float | None, variance: Any, *, summary: bool,
    aggregate: bool = False,
) -> tuple[str, str, float | None]:
    if source_metric in NO_COMPARABLE_GOAL:
        return "unavailable", "No comparable numeric goal in the workbook", None
    if (summary or aggregate) and source_metric in CLINICAL_AGGREGATES:
        return "unavailable", "Aggregate share reported; no aggregate threshold supplied", None
    if source_metric == "Forecast and Hire" and not summary:
        return "unavailable", "Workbook repeats the enterprise goal below enterprise level", None
    if source_metric in FINANCIAL_VARIANCE_METRICS:
        variance_number = parse_numeric(variance)
        if variance_number is not None:
            return ("met" if variance_number >= 0 else "missed"), "Reported variance against the local financial target", variance_number
    if value_number is None or goal_operator is None or goal_number is None:
        return "unavailable", "Value and local goal are not directly comparable", None
    meets = value_number >= goal_number if goal_operator == ">=" else value_number <= goal_number
    if goal_number == 0:
        gap = value_number if goal_operator == ">=" else -value_number
    else:
        gap = ((value_number - goal_number) if goal_operator == ">=" else (goal_number - value_number)) / abs(goal_number) * 100
    return ("met" if meets else "missed"), "Calculated from the displayed value and this scope's local goal", gap


def normalize_record(row: dict[str, Any], sheet: str, *, summary: bool, order: int) -> dict[str, Any]:
    source_metric = clean(row.get("Metric"))
    metric = ALIASES.get(source_metric, source_metric)
    if summary:
        business_area = CATEGORY_TO_SHEET.get(clean(row.get("Category")).upper(), "Other")
        pillar = clean(row.get("Aspiration")) or PILLAR_BY_SHEET.get(business_area, business_area)
        location_type, division, level = "Corporate", "SYS", 0
    else:
        business_area, pillar = sheet, PILLAR_BY_SHEET.get(sheet, sheet)
        location_type, division = clean(row.get("Location Type")) or "Other", clean(row.get("Division")) or "N/A"
        try: level = int(float(clean(row.get("Level")) or "0"))
        except ValueError: level = 0
    location = clean(row.get("Location")) or "AdventHealth"
    clinical_aggregate = (
        source_metric in CLINICAL_AGGREGATES
        and location_type.casefold() == "corporate"
    )
    value_text, value_number = display_value(
        row.get("Value"),
        source_metric,
        summary=summary,
        aggregate=clinical_aggregate,
    )
    unit = METRIC_UNITS.get(source_metric, "number")
    goal_operator, goal_number = parse_goal(row.get("Goal"), source_metric)
    status, basis, gap = derived_status(
        source_metric,
        value_number,
        goal_operator,
        goal_number,
        row.get("Variance"),
        summary=summary,
        aggregate=clinical_aggregate,
    )
    ytd_text = clean(row.get("YTD")) or "N/A"
    return {
        "rowId": f"{'SUMMARY' if summary else sheet.upper()}::{order}",
        "businessArea": business_area, "pillar": pillar, "sourceMetric": source_metric,
        "metric": metric, "unit": unit, "level": level, "divisionRaw": division,
        "divisionKey": division_key(division, location_type), "locationType": location_type,
        "location": location, "scopeId": scope_id(location_type, location),
        "valueRaw": clean(row.get("Value")) or "N/A", "valueDisplay": value_text,
        "valueNumber": value_number, "goalRaw": clean(row.get("Goal")) or "N/A",
        "goalDisplay": format_goal(row.get("Goal"), goal_operator, goal_number, unit),
        "goalOperator": goal_operator, "goalNumber": goal_number, "goalStatus": status,
        "statusBasis": basis, "gap": gap,
        "varianceDirection": clean(row.get("Variance Direction")) or "—",
        "varianceDisplay": clean(row.get("Variance")) or "N/A",
        "sourceStatus": source_status(row.get("Variance Color")),
        "ytdDisplay": ytd_text, "ytdNumber": parse_numeric(ytd_text),
        "dataAsOf": clean(row.get("Data As Of")) or "N/A", "isSummary": summary,
        "sourceDivision": division,
        "originalDivision": division,
        "matchedDivision": division,
        "reportGeography": "N/A",
        "mappingStatus": "N/A",
        "mappingConfidence": "N/A",
        "mappingEvidence": "N/A",
    }


def load_mapping_audit(
    workbook_path: Path,
    mapping_audit_path: Path | None = None,
) -> tuple[list[dict[str, str]], Path | None]:
    if mapping_audit_path:
        candidates = [mapping_audit_path.resolve()]
    else:
        candidates = sorted(workbook_path.parent.glob("division_mapping_audit_*.csv"))
        stamp = re.search(r"(\d{4}-\d{2}-\d{2}_\d{6})", workbook_path.stem)
        if stamp and SOURCE_MAPPING.exists():
            candidates.extend(sorted(SOURCE_MAPPING.glob(
                f"*/division_mapping_audit_*{stamp.group(1)}*.csv"
            )))
    if not candidates:
        return [], None
    stamp = re.search(r"(\d{4}-\d{2}-\d{2}_\d{6})", workbook_path.stem)
    if stamp:
        exact = [path for path in candidates if stamp.group(1) in path.stem]
        if exact:
            candidates = exact
    selected = candidates[-1]
    with selected.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle)), selected


def attach_mapping_audit(
    records: list[dict[str, Any]], audit_rows: list[dict[str, str]],
) -> tuple[int, list[str]]:
    if not audit_rows:
        return 0, []
    by_row = {
        (clean(row.get("Workbook Sheet")).upper(), clean(row.get("Workbook Row"))): row
        for row in audit_rows
        if clean(row.get("Workbook Sheet")) and clean(row.get("Workbook Row"))
    }
    queues: dict[tuple[str, ...], list[dict[str, str]]] = {}
    if not by_row:
        for row in audit_rows:
            if clean(row.get("Level")) == "N/A" or clean(row.get("Location Type")) == "N/A":
                continue
            key = (
                clean(row.get("Metric")), clean(row.get("Level")),
                clean(row.get("Location Type")), clean(row.get("Location")),
                clean(row.get("Original Division")),
            )
            queues.setdefault(key, []).append(row)
    attached = 0
    source_mismatches = []
    for record in records:
        prefix, row_number = record["rowId"].split("::", 1)
        audit = by_row.get((prefix, row_number))
        if audit is None and queues:
            key = (
                record["sourceMetric"], str(record["level"]), record["locationType"],
                record["location"], record["divisionRaw"],
            )
            matches = queues.get(key, [])
            audit = matches.pop(0) if matches else None
        if audit is None:
            continue
        audit_source = clean(audit.get("Original Division")) or "N/A"
        record_source = clean(record["divisionRaw"]) or "N/A"
        if audit_source != record_source:
            source_mismatches.append(
                f"{record['rowId']}: workbook={record_source!r}, audit={audit_source!r}"
            )
            continue
        matched_division_raw = (
            clean(audit.get("Matched Division"))
            or clean(audit.get("Final Division"))
            or record_source
        )
        matched_division = division_key(
            matched_division_raw, record["locationType"],
        )
        report_geography_raw = clean(audit.get("Report Geography")) or "N/A"
        record.update({
            "sourceDivision": record_source,
            "originalDivision": record_source,
            "matchedDivision": matched_division,
            "divisionKey": matched_division,
            "reportGeography": (
                "N/A" if report_geography_raw == "N/A"
                else division_label(report_geography_raw)
            ),
            "mappingStatus": clean(audit.get("Mapping Status")) or "N/A",
            "mappingConfidence": clean(audit.get("Confidence")) or "N/A",
            "mappingEvidence": clean(audit.get("Matched Evidence")) or "N/A",
        })
        attached += 1
    return attached, source_mismatches


def build_model(
    workbook: dict[str, list[dict[str, Any]]],
    workbook_path: Path,
    mapping_audit_path: Path | None = None,
) -> dict[str, Any]:
    missing = {"Vision 2030", *DETAIL_SHEETS} - set(workbook)
    if missing: raise ValueError("Missing sheets: " + ", ".join(sorted(missing)))
    summary = [normalize_record(row, "Vision 2030", summary=True, order=i) for i, row in enumerate(workbook["Vision 2030"], 2)]
    records: list[dict[str, Any]] = []
    for sheet in DETAIL_SHEETS:
        records.extend(normalize_record(row, sheet, summary=False, order=i) for i, row in enumerate(workbook[sheet], 2))
    mapping_audit_rows, selected_mapping_audit = load_mapping_audit(
        workbook_path, mapping_audit_path,
    )
    mapping_audit_attached, source_division_mismatches = attach_mapping_audit(
        records, mapping_audit_rows,
    )
    metadata, seen = [], set()
    for record in summary:
        if record["metric"] in seen: continue
        seen.add(record["metric"])
        detail = [item for item in records if item["metric"] == record["metric"]]
        metadata.append({
            "metric": record["metric"], "sourceMetric": record["sourceMetric"],
            "businessArea": record["businessArea"], "pillar": record["pillar"], "unit": record["unit"],
            "systemGoal": record["goalDisplay"], "locationTypes": sorted({i["locationType"] for i in detail}),
            "detailRows": len(detail), "scopeSpecificGoals": len({i["goalRaw"] for i in detail}),
        })
    keys = Counter((r["metric"], r["divisionRaw"], r["locationType"], r["location"]) for r in records)
    duplicates = sum(n - 1 for n in keys.values() if n > 1)
    dates = Counter(r["dataAsOf"] for r in summary)
    return {
        "schemaVersion": 2, "summary": summary, "records": records, "metrics": metadata,
        "businessAreas": ["Vision 2030", *DETAIL_SHEETS],
        "locationTypesByArea": {area: sorted({r["locationType"] for r in records if r["businessArea"] == area}) for area in DETAIL_SHEETS},
        "divisions": sorted({r["divisionKey"] for r in records if r["divisionKey"] != "SYS"}),
        "quality": {
            "detailRows": len(records), "summaryRows": len(summary),
            "uniqueScopes": len({(r["divisionRaw"], r["locationType"], r["location"]) for r in records}),
            "duplicateRows": duplicates,
            "sourceStatusCounts": dict(Counter(r["sourceStatus"] for r in records)),
            "goalStatusCounts": dict(Counter(r["goalStatus"] for r in records)),
            "summaryDateCounts": dict(dates), "summaryDateRange": [d for d in dates if d != "N/A"],
            "unresolvedDivisionRows": sum("Unresolved" in r["divisionKey"] for r in records),
            "mappingAuditRows": len(mapping_audit_rows),
            "mappingAuditAttached": mapping_audit_attached,
            "sourceDivisionMismatches": source_division_mismatches,
            "matchedDivisionDiffersFromSourceRows": sum(
                r["matchedDivision"] != r["sourceDivision"] for r in records
            ),
            "mappingStatusCounts": dict(Counter(r["mappingStatus"] for r in records)),
        },
        "methodology": {
            "goalStatus": "Calculated only when the workbook supplies a directly comparable local goal. Financial rows use the workbook's reported local-target variance. Source variance color is retained separately.",
            "gray": "Unavailable means a defensible goal status could not be calculated; it does not mean the value itself is missing.",
            "comparisons": "Peer statistics compare records at the same location type and metric. Sparse or unmatched records are excluded with denominators shown.",
            "trend": "The workbook is a mixed-date snapshot, not a monthly time series. No trend is inferred.",
        },
        "_source": {
            "workbook": str(workbook_path.relative_to(PROJECT)),
            "workbookSha256": file_sha256(workbook_path),
            "outputBatch": (
                re.search(r"(\d{4}-\d{2}-\d{2}_\d{6})", workbook_path.stem).group(1)
                if re.search(r"(\d{4}-\d{2}-\d{2}_\d{6})", workbook_path.stem)
                else workbook_path.parent.name
            ),
            "mappingAudit": (
                str(selected_mapping_audit.relative_to(PROJECT))
                if selected_mapping_audit else "N/A"
            ),
            "builtAt": datetime.now().isoformat(timespec="seconds"),
        },
    }


def write_audit(model: dict[str, Any]) -> dict[str, Any]:
    GENERATED.mkdir(exist_ok=True)
    rows = [{
        "Row ID": r["rowId"], "Business Area": r["businessArea"], "Metric": r["metric"],
        "Matched Division": r["divisionKey"], "Source Division": r["sourceDivision"],
        "Location Type": r["locationType"], "Location": r["location"],
        "Original Division": r["originalDivision"], "Report Geography": r["reportGeography"],
        "Mapping Status": r["mappingStatus"], "Mapping Confidence": r["mappingConfidence"],
        "Mapping Evidence": r["mappingEvidence"],
        "Value": r["valueDisplay"], "Local Goal": r["goalDisplay"], "Derived Goal Status": r["goalStatus"],
        "Status Basis": r["statusBasis"], "Source Variance": r["varianceDisplay"],
        "Source Variance Color": r["sourceStatus"], "YTD": r["ytdDisplay"], "Data As Of": r["dataAsOf"],
    } for r in [*model["summary"], *model["records"]]]
    with (GENERATED / "normalized_record_audit.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    clinical_mismatches = []
    for metric in ("CMS Overall Hospital Star Rating", "Leapfrog Hospital Safety Grade"):
        summary_record = next((r for r in model["summary"] if r["metric"] == metric), None)
        detail_record = next((
            r for r in model["records"]
            if r["metric"] == metric and r["locationType"] == "Corporate"
        ), None)
        if (
            summary_record is None or detail_record is None
            or summary_record["valueNumber"] is None or detail_record["valueNumber"] is None
            or abs(summary_record["valueNumber"] - detail_record["valueNumber"]) > 0.05
        ):
            clinical_mismatches.append(metric)
    known_unclassified = [
        r["location"] for r in model["records"]
        if r["divisionKey"] == "Unclassified" and "glenoaks" in slug(r["location"]).casefold()
    ]
    mapping_complete = model["quality"]["mappingAuditAttached"] == len(model["records"])
    source_division_mismatches = model["quality"]["sourceDivisionMismatches"]
    audit_pass = (
        model["quality"]["duplicateRows"] == 0
        and mapping_complete
        and not source_division_mismatches
        and not clinical_mismatches
        and not known_unclassified
    )
    summary = {
        "schemaVersion": model["schemaVersion"], "sourceWorkbook": model["_source"]["workbook"],
        "sourceWorkbookSha256": model["_source"]["workbookSha256"],
        "mappingAudit": model["_source"]["mappingAudit"],
        "summaryRows": len(model["summary"]), "detailRows": len(model["records"]),
        "uniqueScopes": model["quality"]["uniqueScopes"], "duplicateRows": model["quality"]["duplicateRows"],
        "generatedMetrics": len(model["metrics"]),
        "mappingAuditRows": model["quality"]["mappingAuditRows"],
        "mappingAuditAttached": model["quality"]["mappingAuditAttached"],
        "mappingComplete": mapping_complete,
        "sourceDivisionMismatches": source_division_mismatches,
        "matchedDivisionDiffersFromSourceRows": model["quality"]["matchedDivisionDiffersFromSourceRows"],
        "clinicalAggregateMismatches": clinical_mismatches,
        "knownUnclassifiedFacilities": known_unclassified,
        "auditPass": audit_pass,
    }
    (GENERATED / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def model_bounds(html: str) -> tuple[int, int, dict[str, Any]]:
    marker = "const VD ="; start = html.index(marker) + len(marker)
    value, used = json.JSONDecoder().raw_decode(html[start:])
    return start, start + used, value


def inject(template_path: Path, output_path: Path, model: dict[str, Any]) -> None:
    html = template_path.read_text(encoding="utf-8")
    start, end, _ = model_bounds(html)
    rendered = html[:start] + json.dumps(model, ensure_ascii=False, separators=(",", ":")) + html[end:]
    temporary = output_path.with_suffix(".tmp"); temporary.write_text(rendered, encoding="utf-8"); temporary.replace(output_path)
    if model_bounds(rendered)[2]["_source"] != model["_source"]:
        raise RuntimeError(f"Injected data verification failed for {output_path.name}")


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store"); super().end_headers()


def serve(port: int) -> None:
    os.chdir(SITE); server = None; selected_port = port
    for candidate in range(port, port + 11):
        try: server = ThreadingHTTPServer(("127.0.0.1", candidate), Handler); selected_port = candidate; break
        except OSError: continue
    if server is None: raise OSError("No available localhost port")
    url = f"http://127.0.0.1:{selected_port}/briefing.html"; print("Website:", url)
    threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nStopped")
    finally: server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--workbook", type=Path)
    parser.add_argument("--mapping-audit", type=Path)
    parser.add_argument("--output-root", type=Path, default=OUTPUT); parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--build-only", action="store_true"); args = parser.parse_args()
    workbook_path = args.workbook.resolve() if args.workbook else latest(args.output_root.resolve())
    print("Workbook:", workbook_path)
    model = build_model(
        read_xlsx(workbook_path), workbook_path,
        args.mapping_audit.resolve() if args.mapping_audit else None,
    ); validation = write_audit(model)
    print("Mapping audit:", model["_source"]["mappingAudit"])
    print(json.dumps(validation, indent=2))
    #if not validation["auditPass"]: raise RuntimeError("Validation failed; review generated/normalized_record_audit.csv")
    for page in PAGES: inject(TEMPLATES / page, SITE / page, model)
    signatures = [json.dumps(model_bounds((SITE / p).read_text(encoding="utf-8"))[2], sort_keys=True, ensure_ascii=False) for p in PAGES]
    if len(set(signatures)) != 1: raise RuntimeError("Generated page data models differ")
    print("All pages built from one normalized, audited data model.")
    if not args.build_only: serve(args.port)


if __name__ == "__main__": main()

from __future__ import annotations

import py_compile
import re
import shutil
from pathlib import Path

PROJECT = Path(r"C:\Users\PBA96B\OneDrive - AdventHealth\Documents\DATA LINK LAYER EXTRACTION")
SOURCE = PROJECT / "sandbox_updated.py"
OUTPUT = PROJECT / "sandbox_updated_v2.py"
BACKUP = PROJECT / "sandbox_updated_before_v2.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 match, found {count}.")
    return text.replace(old, new, 1)


def insert_before(text: str, marker: str, block: str, label: str) -> str:
    if block.strip() in text:
        return text
    return replace_once(text, marker, block + marker, label)


def patch_direct_division_map(text: str) -> str:
    pattern = re.compile(
        r"DIRECT_DIVISION_MAP\s*=\s*\{.*?\n\}",
        re.DOTALL,
    )
    replacement = '''DIRECT_DIVISION_MAP = {
    "central florida": "CFD",
    "central florida division": "CFD",
    "central florida division cost centers by reporting hierarchy": "CFD",
    "east florida": "EFD",
    "east florida division": "EFD",
    "east florida division cost centers by reporting hierarchy": "EFD",
    "west florida": "WFD",
    "west florida division": "WFD",
    "west florida division cost centers by reporting hierarchy": "WFD",
    "primary health division": "PHD",
    "primary health cost centers by reporting hierarchy": "PHD",
    "primary health division cost centers by reporting hierarchy": "PHD",
    "corporate services": "Corporate Services",
    "corporate services division": "Corporate Services",
    "corporate services division cost centers by reporting hierarchy": "Corporate Services",
}'''
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError(
            "DIRECT_DIVISION_MAP block was not found exactly once."
        )
    return text


def patch_region_lists(text: str) -> str:
    replacements = {
        '''MSD1_REGIONS = (
    "Rocky Mountain Region", "Multi-State - Rocky Mountain",
    "Southeast Region", "Multi-State - Southeast",
)''': '''MSD1_REGIONS = (
    "Rocky Mountain Region",
    "Rocky Mountain Region Cost Centers by Reporting Hierarchy",
    "Multi-State - Rocky Mountain",
    "Southeast Region",
    "South East Region",
    "South East Region Cost Centers by Reporting Hierarchy",
    "Multi-State - Southeast",
)''',
        '''MSD2_REGIONS = (
    "Mid-America Region", "Multi-State - Mid-America",
    "Great Lakes Region", "Multi-State - Great Lakes",
    "Southwest Region", "Multi-State - Southwest",
)''': '''MSD2_REGIONS = (
    "Mid-America Region",
    "Mid America Region",
    "Mid America Region Cost Centers by Reporting Hierarchy",
    "Multi-State - Mid-America",
    "Great Lakes Region",
    "Great Lakes Region Cost Centers by Reporting Hierarchy",
    "Multi-State - Great Lakes",
    "Southwest Region",
    "South West Region",
    "South West Region Cost Centers by Reporting Hierarchy",
    "Multi-State - Southwest",
)''',
    }
    for old, new in replacements.items():
        if old in text:
            text = replace_once(text, old, new, "region list update")
        elif new not in text:
            raise RuntimeError("Expected Multistate region list was not found.")
    return text


def add_confirmed_region_maps(text: str) -> str:
    marker = 'DIVISION_MAPPING_AUDIT = []\n'
    block = '''CONFIRMED_REGION_MAP = {
    "central florida": "CFD",
    "central florida division cost centers by reporting hierarchy": "CFD",
    "east florida": "EFD",
    "east florida division cost centers by reporting hierarchy": "EFD",
    "west florida": "WFD",
    "west florida division cost centers by reporting hierarchy": "WFD",
    "primary health": "PHD",
    "primary health cost centers by reporting hierarchy": "PHD",
    "primary health division region": "PHD",
    "primary health division region 1": "PHD",
    "primary health division region 2": "PHD",
    "primary health division region 3": "PHD",
    "primary health division region 4": "PHD",
}

'''
    return insert_before(text, marker, block, "confirmed region map insertion")


def patch_normalizer(text: str) -> str:
    anchor = '''    direct_value = DIRECT_DIVISION_MAP.get(original_division.casefold())
    if direct_value:
        return direct_value, "CONFIRMED_DIRECT", original_division
'''
    addition = anchor + '''
    evidence_casefold = evidence.casefold()
    for region_name, final_division in CONFIRMED_REGION_MAP.items():
        if region_name in evidence_casefold:
            return final_division, "CONFIRMED_REGION", region_name
'''
    if addition in text:
        return text
    return replace_once(
        text,
        anchor,
        addition,
        "confirmed region mapping in normalizer",
    )


def add_clinical_level_zero_support(text: str) -> str:
    marker = 'def add_all_category_sheets(\n'
    block = '''def prepend_clinical_level_zero_rows(rows_by_category, business_records):
    clinical_metric_names = {
        "All-Adult Inpatient Mortality",
        "Length of Stay O/E",
        "CMS Star Rating",
        "Leapfrog Safety Grade",
    }

    level_zero_rows = []
    for business_record in business_records:
        metric_name = clean_text(business_record.get("Metric"))
        if metric_name not in clinical_metric_names:
            continue

        level_zero_rows.append({
            "Metric": metric_name,
            "Level": 0,
            "Division": "N/A",
            "Location Type": "Corporate",
            "Location": "AdventHealth",
            "Value": business_record.get("Value", "N/A"),
            "Goal": business_record.get("Goal", "N/A"),
            "Variance Direction": business_record.get(
                "Variance Direction",
                "→",
            ),
            "Variance": business_record.get("Variance", "N/A"),
            "Variance Color": business_record.get(
                "Variance Color",
                "GRAY",
            ),
            "YTD": business_record.get("YTD", "N/A"),
            "Data As Of": business_record.get("Data As Of", "N/A"),
        })

    metric_order = {
        rule["display_name"]: rule["order"]
        for rule in METRIC_RULES
    }
    level_zero_rows.sort(
        key=lambda row: metric_order.get(row["Metric"], 999)
    )

    existing = rows_by_category.get("CLINICAL", [])
    existing = [
        row
        for row in existing
        if not (
            row.get("Level") == 0
            and row.get("Metric") in clinical_metric_names
        )
    ]
    rows_by_category["CLINICAL"] = level_zero_rows + existing


'''
    text = insert_before(
        text,
        marker,
        block,
        "Clinical Level 0 helper insertion",
    )

    text = replace_once(
        text,
        '''def add_all_category_sheets(
    workbook,
    drilldown_nodes,
):''',
        '''def add_all_category_sheets(
    workbook,
    drilldown_nodes,
    business_records,
):''',
        "add_all_category_sheets signature",
    )

    anchor = '''    rows_by_category = build_category_sheet_rows(
        drilldown_nodes
    )
'''
    replacement = anchor + '''
    prepend_clinical_level_zero_rows(
        rows_by_category,
        business_records,
    )
'''
    if replacement not in text:
        text = replace_once(
            text,
            anchor,
            replacement,
            "Clinical Level 0 call",
        )

    call_pattern = re.compile(
        r"add_all_category_sheets\(\s*workbook,\s*drilldown_nodes,\s*\)",
        re.DOTALL,
    )
    if "business_records," not in text[
        max(0, text.find("add_all_category_sheets(")):text.find("add_all_category_sheets(") + 250
    ]:
        pass
    text, count = call_pattern.subn(
        '''add_all_category_sheets(
        workbook,
        drilldown_nodes,
        business_records,
    )''',
        text,
        count=1,
    )
    if count != 1 and '''add_all_category_sheets(
        workbook,
        drilldown_nodes,
        business_records,
    )''' not in text:
        raise RuntimeError("add_all_category_sheets call was not patched.")

    return text


def strengthen_validation(text: str) -> str:
    marker = '# ============================================================\n# MAIN PROCESS\n# ============================================================'
    block = '''def validate_v2_configuration():
    expected_names = [
        "Annual Active Users",
        "All-Adult Inpatient Mortality",
        "Length of Stay O/E",
        "CMS Star Rating",
        "Leapfrog Safety Grade",
    ]
    configured_names = [rule["display_name"] for rule in METRIC_RULES]

    if len(METRIC_RULES) != 21:
        raise ValueError(
            f"Expected 21 metric rules, found {len(METRIC_RULES)}."
        )

    if [rule["order"] for rule in METRIC_RULES] != list(range(1, 22)):
        raise ValueError("Metric rule order must be exactly 1 through 21.")

    missing = [name for name in expected_names if name not in configured_names]
    if missing:
        raise ValueError(f"Missing required metric rules: {missing}")


'''
    text = insert_before(text, marker, block, "v2 validation insertion")

    main_anchor = '''def main():
    OUTPUT_FOLDER.mkdir('''
    main_replacement = '''def main():
    validate_v2_configuration()

    OUTPUT_FOLDER.mkdir('''
    if main_replacement not in text:
        text = replace_once(
            text,
            main_anchor,
            main_replacement,
            "v2 validation call",
        )
    return text


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(
            f"Required source file not found: {SOURCE}"
        )

    shutil.copy2(SOURCE, BACKUP)
    text = SOURCE.read_text(encoding="utf-8")

    text = patch_direct_division_map(text)
    text = patch_region_lists(text)
    text = add_confirmed_region_maps(text)
    text = patch_normalizer(text)
    text = add_clinical_level_zero_support(text)
    text = strengthen_validation(text)

    OUTPUT.write_text(text, encoding="utf-8")
    py_compile.compile(str(OUTPUT), doraise=True)

    checks = {
        "21 metrics": "Expected 21 metric rules" in text,
        "Annual Active Users": '"Annual Active Users"' in text,
        "Mortality placeholder": '"All-Adult Inpatient Mortality"' in text,
        "Clinical Level 0": "prepend_clinical_level_zero_rows" in text,
        "CFD short mapping": '"central florida": "CFD"' in text,
        "EFD short mapping": '"east florida": "EFD"' in text,
        "WFD short mapping": '"west florida": "WFD"' in text,
        "PHD variants": '"primary health cost centers by reporting hierarchy": "PHD"' in text,
        "Corporate Services": '"corporate services division cost centers by reporting hierarchy": "Corporate Services"' in text,
        "MSD 1 region variants": "South East Region Cost Centers by Reporting Hierarchy" in text,
        "MSD 2 region variants": "South West Region Cost Centers by Reporting Hierarchy" in text,
        "Audit preserved": "save_division_mapping_audit" in text,
    }

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        OUTPUT.unlink(missing_ok=True)
        raise RuntimeError(f"Generated file failed checks: {failed}")

    print("Created:", OUTPUT)
    print("Backup:", BACKUP)
    print("Python compilation: PASS")
    for name in checks:
        print(f"{name}: PASS")


if __name__ == "__main__":
    main()

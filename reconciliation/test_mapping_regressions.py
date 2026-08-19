#!/usr/bin/env python3
"""Regression checks for governed Vision 2030 division mapping behavior."""

from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reconciliation"))
sys.path.insert(0, str(ROOT / "vision2030_contemporary_site"))

from build_corrected_workbook import (  # noqa: E402
    CORPORATE_PARENT,
    PHD_PARENT,
    corrected_assignment,
)
from site_builder import (  # noqa: E402
    OUTPUT,
    attach_mapping_audit,
    display_value,
    division_label,
    latest,
    normalize_record,
)


def extraction_normalizer():
    path = ROOT / "vision2030_extraction.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    constants = {
        "CFD_LOCATIONS", "EFD_LOCATIONS", "WFD_LOCATIONS",
        "MSD1_REGIONS", "MSD1_LOCATIONS", "MSD2_REGIONS", "MSD2_LOCATIONS",
        "DIRECT_DIVISION_MAP", "MULTISTATE_DIVISION_NAMES",
        "UNSUPPORTED_CORPORATE_SERVICES_NAMES", "FLORIDA_PARENT_NAMES",
        "MULTISTATE_PARENT_NAMES", "LOCATION_EVIDENCE_ALIASES",
    }
    functions = {
        "clean_text", "_normalized_text", "_exact_name_match",
        "_find_name_in_evidence", "normalize_division_for_output",
    }
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & constants:
                nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in functions:
            nodes.append(node)
    namespace = {"re": re}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace["normalize_division_for_output"]


class MappingRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.normalize = staticmethod(extraction_normalizer())

    def test_primary_health_parent_wins_over_city(self):
        result = self.normalize({
            "Division": PHD_PARENT,
            "Current Location": "1000417 Home Health Manchester",
            "Hierarchy Path": f"AdventHealth > {PHD_PARENT} > Home Health Manchester",
        })
        self.assertEqual(result[0], "PHD")

    def test_corporate_parent_wins_over_city(self):
        result = self.normalize({
            "Division": CORPORATE_PARENT,
            "Current Location": "117658 AIT WFD Tampa",
            "Hierarchy Path": f"AdventHealth > {CORPORATE_PARENT} > AIT WFD Tampa",
        })
        self.assertEqual(result[0], CORPORATE_PARENT)

    def test_glenoaks_alias_maps_to_msd2(self):
        result = self.normalize({
            "Division": "N/A",
            "Current Location": "UCM AH GlenOaks HOSP",
            "Hierarchy Path": "UCM AH GlenOaks HOSP",
        })
        self.assertEqual(result[0], "MSD 2")

    def test_apopka_under_broad_florida_maps_to_cfd(self):
        result = self.normalize({
            "Division": "Florida Division Cost Centers by Reporting Hierarchy",
            "Current Location": "1000141 Apopka",
            "Hierarchy Path": "AdventHealth > Florida Division Cost Centers by Reporting Hierarchy > Central Florida Division Cost Centers by Reporting Hierarchy > 1000141 Apopka",
        })
        self.assertEqual(result[0], "CFD")

    def test_corrected_assignment_retains_secondary_geography(self):
        final, geography, status = corrected_assignment(
            {"Division": PHD_PARENT, "Location": "Home Health Manchester"},
            {"Division": "MSD 1"},
        )
        self.assertEqual((final, geography, status), ("PHD", "MSD 1", "ORGANIZATIONAL_PARENT_PHD"))

    def test_clinical_corporate_fraction_displays_as_share(self):
        display, number = display_value(
            "0.65", "CMS Star Rating", summary=False, aggregate=True,
        )
        self.assertEqual(display, "65.0% 4–5 Star facilities")
        self.assertEqual(number, 65.0)

    def test_full_division_names_are_visible_labels(self):
        self.assertEqual(division_label("CFD"), "Central Florida Division")
        self.assertEqual(division_label("MSD 2"), "Multi-State Division 2")

    def test_sidecar_match_does_not_change_source_division(self):
        record = normalize_record({
            "Metric": "Team Member Engagement",
            "Level": 1,
            "Division": "Central Florida",
            "Location Type": "Division",
            "Location": "Central Florida",
            "Value": "82",
            "Goal": ">= 81",
        }, "Team", summary=False, order=2)
        attached, mismatches = attach_mapping_audit([record], [{
            "Workbook Sheet": "Team",
            "Workbook Row": "2",
            "Original Division": "Central Florida",
            "Matched Division": "CFD",
            "Mapping Status": "CONFIRMED_DIRECT_DIVISION",
            "Confidence": "high",
            "Matched Evidence": "Central Florida",
        }])
        self.assertEqual((attached, mismatches), (1, []))
        self.assertEqual(record["divisionRaw"], "Central Florida")
        self.assertEqual(record["sourceDivision"], "Central Florida")
        self.assertEqual(record["matchedDivision"], "Central Florida Division")
        self.assertEqual(record["divisionKey"], "Central Florida Division")

    def test_default_build_selects_august_18_source(self):
        self.assertEqual(
            latest(OUTPUT).name,
            "vision2030_business_table_2026-08-18_130253.xlsx",
        )


if __name__ == "__main__":
    unittest.main()

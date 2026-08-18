from __future__ import annotations

import json
from pathlib import Path

RUNNER_FILE = Path(
    r"C:\Users\PBA96B\OneDrive - AdventHealth\Documents\DATA LINK LAYER EXTRACTION\vision2030_contemporary_site\run_vision2030.py"
)


def replace_once(source: str, old: str, new: str, description: str) -> str:
    count = source.count(old)

    if count != 1:
        raise RuntimeError(
            f"{description}: expected exactly one match, found {count}."
        )

    return source.replace(old, new, 1)


source = RUNNER_FILE.read_text(encoding="utf-8")

helper_marker = """
def classify(lt):
"""

helper_code = """
def selector_group(location_type):
    location_type_text = text(location_type)
    normalized_type = location_type_text.casefold()

    if normalized_type == "corporate":
        return "System"

    if normalized_type == "division":
        return "Division Summary"

    if normalized_type == "region":
        return "Regions"

    if normalized_type == "market":
        return "Markets"

    if normalized_type == "facility":
        return "Facilities"

    return "Other"


def selector_subgroup(location_type):
    location_type_text = text(location_type)
    normalized_type = location_type_text.casefold()

    subgroup_labels = {
        "business unit": "Business Units",
        "campus": "Campuses",
        "cost center": "Cost Centers",
        "costing company": "Costing Companies",
        "frl": "FRLs",
        "hospital": "Hospitals",
    }

    return subgroup_labels.get(
        normalized_type,
        location_type_text,
    )


def normalized_division_key(division):
    division_text = text(division)

    confirmed_divisions = {
        "CFD",
        "EFD",
        "WFD",
        "PHD",
        "MSD",
        "MSD 1",
        "MSD 2",
    }

    if division_text in confirmed_divisions:
        return division_text

    if division_text == "Corporate Services":
        return "Corporate Services"

    if division_text in {
        "Corporate Services Division Cost Centers by Reporting Hierarchy",
        "Corporate Services Division",
    }:
        return "Corporate Services"

    if division_text in {
        "Florida Division Cost Centers by Reporting Hierarchy",
        "Florida Division",
    }:
        return "Florida Division (Unresolved)"

    if division_text in {
        "Multistate Division Cost Centers by Reporting Hierarchy",
        "Multi-State Division Cost Centers by Reporting Hierarchy",
        "Multistate Division",
        "Multi-State Division",
    }:
        return "Multistate Division (Unresolved)"

    return "Unclassified"


def classify(lt):
"""

if "def selector_group(location_type):" not in source:
    source = replace_once(
        source,
        helper_marker,
        helper_code,
        "Insert selector metadata helpers",
    )

old_system_scope = """scopes=[{'id':'SYS','label':'AdventHealth System','kind':'system','parent':None,'asp':0}]"""

new_system_scope = """scopes=[{
  'id':'SYS',
  'label':'AdventHealth System',
  'kind':'system',
  'parent':None,
  'asp':0,
  'divisionKey':'SYS',
  'selectorGroup':'System',
  'selectorSubgroup':'System'
 }]"""

if old_system_scope in source:
    source = replace_once(
        source,
        old_system_scope,
        new_system_scope,
        "Add selector metadata to System scope",
    )

old_division_scope = """scopes.append({'id':sid,'label':DIV_LABEL[div],'kind':'division','parent':parent,'asp':0}); seen.add(sid)"""

new_division_scope = """scopes.append({
    'id':sid,
    'label':DIV_LABEL[div],
    'kind':'division',
    'parent':parent,
    'asp':0,
    'divisionKey':normalized_division_key(div),
    'selectorGroup':'Division Summary',
    'selectorSubgroup':'Division Summary'
   })
   seen.add(sid)"""

if old_division_scope in source:
    source = replace_once(
        source,
        old_division_scope,
        new_division_scope,
        "Add selector metadata to Division scopes",
    )

old_unclassified_scope = """scopes.append({'id':'UNCLASS','label':'Unclassified / Other','kind':'division','parent':'SYS','asp':0}); seen.add('UNCLASS')"""

new_unclassified_scope = """scopes.append({
  'id':'UNCLASS',
  'label':'Unclassified / Other',
  'kind':'division',
  'parent':'SYS',
  'asp':0,
  'divisionKey':'Unclassified',
  'selectorGroup':'Division Summary',
  'selectorSubgroup':'Unclassified'
 })
 seen.add('UNCLASS')"""

if old_unclassified_scope in source:
    source = replace_once(
        source,
        old_unclassified_scope,
        new_unclassified_scope,
        "Add selector metadata to Unclassified scope",
    )

old_unclassified_type_scope = """scopes.append({'id':sid,'label':f'Unclassified {lt}','kind':'region','parent':'UNCLASS','asp':0}); seen.add(sid)"""

new_unclassified_type_scope = """scopes.append({
   'id':sid,
   'label':f'Unclassified {lt}',
   'kind':'region',
   'parent':'UNCLASS',
   'asp':0,
   'divisionKey':'Unclassified',
   'selectorGroup':selector_group(lt),
   'selectorSubgroup':selector_subgroup(lt)
  })
  seen.add(sid)"""

if old_unclassified_type_scope in source:
    source = replace_once(
        source,
        old_unclassified_type_scope,
        new_unclassified_type_scope,
        "Add selector metadata to Unclassified type scopes",
    )

old_generated_scope = """scopes.append({'id':sid,'label':friendly_scope_label(r.get('Location Type'),r.get('Location'),r.get('Division')),'kind':classify(r.get('Location Type')),'parent':parent,'asp':0,'sourceType':text(r.get('Location Type'))}); seen.add(sid)"""

new_generated_scope = """scopes.append({
    'id':sid,
    'label':friendly_scope_label(
     r.get('Location Type'),
     r.get('Location'),
     r.get('Division')
    ),
    'kind':classify(r.get('Location Type')),
    'parent':parent,
    'asp':0,
    'sourceType':text(r.get('Location Type')),
    'divisionKey':normalized_division_key(r.get('Division')),
    'selectorGroup':selector_group(r.get('Location Type')),
    'selectorSubgroup':selector_subgroup(r.get('Location Type'))
   })
   seen.add(sid)"""

if old_generated_scope in source:
    source = replace_once(
        source,
        old_generated_scope,
        new_generated_scope,
        "Add selector metadata to generated scopes",
    )

RUNNER_FILE.write_text(
    source,
    encoding="utf-8",
)

required_functions = (
    "def selector_group(location_type):",
    "def selector_subgroup(location_type):",
    "def normalized_division_key(division):",
)

updated_source = RUNNER_FILE.read_text(encoding="utf-8")

for required_function in required_functions:
    if required_function not in updated_source:
        raise RuntimeError(
            f"Required helper was not written: {required_function}"
        )

print("PASS: Selector metadata patch was applied.")

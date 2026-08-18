from pathlib import Path

SITE_FOLDER = Path(
    r"C:\Users\PBA96B\OneDrive - AdventHealth\Documents\DATA LINK LAYER EXTRACTION\vision2030_contemporary_site"
)

TEMPLATE_FILE = SITE_FOLDER / "templates" / "briefing.html"
OUTPUT_FILE = SITE_FOLDER / "briefing_selector_sections.txt"

SEARCH_TERMS = (
    "<select",
    "scope-select",
    "scopeSelect",
    "scope-picker",
    "scopePicker",
    "scope-tree",
    "scopeTree",
    "renderScope",
    "buildScope",
    "populateScope",
    "selectedScope",
    "currentScope",
    "scopeMenu",
    "scope-menu",
    "scopeBtn",
    "scope-btn",
    "addEventListener",
)

if not TEMPLATE_FILE.is_file():
    raise FileNotFoundError(
        f"Briefing template not found: {TEMPLATE_FILE}"
    )

source = TEMPLATE_FILE.read_text(encoding="utf-8")
lines = source.splitlines()

if not lines:
    raise RuntimeError(
        f"Briefing template is empty: {TEMPLATE_FILE}"
    )

match_indexes = []

for index, line in enumerate(lines):
    if any(term in line for term in SEARCH_TERMS):
        match_indexes.append(index)

if not match_indexes:
    raise RuntimeError(
        "No selector-related lines were found in briefing.html."
    )

raw_ranges = []

for match_index in match_indexes:
    start_index = max(0, match_index - 8)
    end_index = min(
        len(lines) - 1,
        match_index + 20,
    )
    raw_ranges.append(
        [start_index, end_index]
    )

raw_ranges.sort(
    key=lambda item: (
        item[0],
        item[1],
    )
)

merged_ranges = []

for start_index, end_index in raw_ranges:
    if not merged_ranges:
        merged_ranges.append(
            [start_index, end_index]
        )
        continue

    previous_range = merged_ranges[-1]

    if start_index <= previous_range[1] + 1:
        previous_range[1] = max(
            previous_range[1],
            end_index,
        )
    else:
        merged_ranges.append(
            [start_index, end_index]
        )

output_lines = []

for start_index, end_index in merged_ranges:
    start_line_number = start_index + 1
    end_line_number = end_index + 1

    header = (
        "===== briefing.html lines "
        f"{start_line_number}-{end_line_number} ====="
    )

    output_lines.append("")
    output_lines.append(header)

    for index in range(
        start_index,
        end_index + 1,
    ):
        output_lines.append(
            f"{index + 1:5}: {lines[index]}"
        )

output_text = "\n".join(output_lines).lstrip() + "\n"

OUTPUT_FILE.write_text(
    output_text,
    encoding="utf-8",
)

if not OUTPUT_FILE.is_file():
    raise RuntimeError(
        f"Output file was not created: {OUTPUT_FILE}"
    )

if OUTPUT_FILE.stat().st_size == 0:
    raise RuntimeError(
        f"Output file is empty: {OUTPUT_FILE}"
    )

print(output_text)
print(
    "PASS: Selector sections were extracted. "
    "No HTML or Python source file was modified."
)
print(f"Saved copy: {OUTPUT_FILE}")
print(f"Matches found: {len(match_indexes)}")
print(f"Merged sections: {len(merged_ranges)}")
print(f"Output bytes: {OUTPUT_FILE.stat().st_size}")

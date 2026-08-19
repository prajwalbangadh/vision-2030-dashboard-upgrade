# Vision 2030 agent instructions

Before generating, editing, or describing any analytical insight, KPI, chart, map, correlation, hierarchy comparison, or trend for this project, read and follow `vision2030_contemporary_site/LLM_INSIGHT_PLAYBOOK.md` in full.

Always rebuild from the latest immutable source workbook with `python3 vision2030_contemporary_site/run_vision2030.py --build-only`. The launcher considers the project root and `output/`, selects the newest timestamped source workbook, attaches its separate audit from `reconciliation/source_mapping/`, and publishes only when `generated/validation_summary.json` reports `auditPass: true`. Do not select a workbook from `reconciliation/corrected_output/` for normal website builds.

Never modify or rename the workbook's `Division` value. Store it as `Source Division`. A separately derived `Matched Division` may support cross-workbook filtering, but it must carry mapping status, confidence, and evidence. Treat `Report Geography` as secondary context only. Never overwrite a direct PHD or Corporate parent with Florida or Multistate geography. Do not reuse clinical value overrides from the rough workbook.

Before changing the information architecture, executive narrative, visual hierarchy, or chart selection, also read `vision2030_contemporary_site/PRESENTATION_GUIDE.txt`, especially the section titled `WHAT WE RETAINED FROM THE FORMER SITE — AND WHAT WE REJECTED`.

Preserve the three defensible structures retained from the former site:

- A deterministic executive readout grounded in the current filtered records.
- Direct-Division met/missed/unavailable composition with visible eligible denominators.
- A detailed scorecard grouped by strategic aspiration while retaining each metric's own goal, date, and status basis.

Do not restore duplicate Division rankings, unequal-denominator System-versus-Division league tables, unsupported yellow or “approaching” status, one global reporting month, promotional headlines, or the assumption that every gray record is unreported.

"""Build and optionally serve the Vision 2030 decision-support site.

The implementation lives in site_builder.py so workbook ingestion, normalization,
auditing, rendering, and localhost serving can be tested independently.
"""

from site_builder import main


if __name__ == "__main__":
    main()

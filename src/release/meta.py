"""Single source of release metadata (params/release.json): version, tag, as-of dates, workbook name. Read by the workbook builder, the tests, README/AUDIT checks."""
import json, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
META = json.load(open(os.path.join(ROOT, "params", "release.json")))


def version_label():
    return f"{META['version']} | prices as of {META['odds_as_of']} | build {META['build_date']}"

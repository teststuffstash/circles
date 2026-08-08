#!/usr/bin/env python3
"""generate-allure-report.py — Generate a simple HTML report from Allure raw results.

Since the `allure` CLI (Java) is not available in this environment, this script
generates a minimal browsable HTML report from the raw Allure result JSON files.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
from pathlib import Path


def generate_report(allure_dir: Path, output_dir: Path) -> None:
    """Generate a simple HTML report from Allure raw results."""
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    for fname in sorted(allure_dir.iterdir()):
        if fname.name.endswith("-result.json"):
            with open(allure_dir / fname) as f:
                results.append(json.load(f))

    # Group by requirement
    cir_re = re.compile(r"(CIR-[A-Z0-9]+(?:-[A-Z0-9]+)+(?:#[a-z0-9_-]+)?)")
    by_req: dict[str, list[dict]] = {}
    for r in results:
        name = r.get("name", "")
        full_name = r.get("fullName", "")
        desc = r.get("description", "") or ""
        all_text = f"{name} {full_name} {desc}"
        matches = cir_re.findall(all_text)
        matches.sort(key=lambda x: -len(x))
        if matches:
            m = matches[0]
            if "#" in m:
                req_id, _ = m.split("#", 1)
            else:
                req_id = m
            by_req.setdefault(req_id, []).append(r)

    # Generate index page
    rows: list[str] = []
    for req_id in sorted(by_req.keys()):
        cases = by_req[req_id]
        passed = sum(1 for c in cases if c.get("status") == "passed")
        total = len(cases)
        status_class = "pass" if passed == total else "fail"
        rows.append(
            f'<tr class="{status_class}">'
            f'<td><a href="#{html.escape(req_id)}">{html.escape(req_id)}</a></td>'
            f'<td>{passed}/{total}</td>'
            f'<td>{"✓" if passed == total else "✗"}</td>'
            f'</tr>'
        )

    # Generate detail sections
    details: list[str] = []
    for req_id in sorted(by_req.keys()):
        cases = by_req[req_id]
        details.append(f'<h2 id="{html.escape(req_id)}">{html.escape(req_id)}</h2>')
        details.append('<table><tr><th>Test</th><th>Case ID</th><th>Status</th><th>Duration</th></tr>')
        for c in cases:
            name = c.get("name", "")
            status = c.get("status", "unknown")
            dur = c.get("stop", 0) - c.get("start", 0)
            # Extract case id
            case_id = ""
            m2 = re.search(r"\[([^\]]*)\]", name)
            if m2:
                pv = m2.group(1)
                if "#" in pv:
                    case_id = pv.split("#", 1)[1]
                else:
                    case_id = pv
            status_icon = {"passed": "✓", "failed": "✗", "broken": "⚠", "skipped": "–"}.get(status, "?")
            details.append(
                f'<tr class="{status}">'
                f'<td>{html.escape(name)}</td>'
                f'<td><code>{html.escape(case_id)}</code></td>'
                f'<td>{status_icon} {status}</td>'
                f'<td>{dur}ms</td>'
                f'</tr>'
            )
        details.append('</table>')

    html_content = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>circles — Allure Test Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 960px; margin: 0 auto; padding: 20px; }}
h1 {{ color: #333; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #eee; }}
th {{ background: #f5f5f5; font-weight: 600; }}
tr.pass td {{ color: #00916A; }}
tr.fail td {{ color: #B22222; }}
tr.passed td {{ color: #00916A; }}
tr.failed td {{ color: #B22222; }}
tr.broken td {{ color: #cc7a00; }}
tr.skipped td {{ color: #999; }}
code {{ background: #f0f0f0; padding: 1px 4px; border-radius: 3px; font-size: 0.9em; }}
.summary {{ background: #f8f8f8; padding: 15px; border-radius: 6px; margin: 15px 0; }}
.summary .pass {{ color: #00916A; font-weight: bold; }}
.summary .fail {{ color: #B22222; font-weight: bold; }}
</style>
</head>
<body>
<h1>circles — Test Evidence Report</h1>
<div class="summary">
<p><strong>World:</strong> alex</p>
<p><strong>Total tests:</strong> {len(results)}</p>
<p><strong>Passed:</strong> <span class="pass">{sum(1 for r in results if r.get('status') == 'passed')}</span></p>
<p><strong>Failed:</strong> <span class="fail">{sum(1 for r in results if r.get('status') in ('failed', 'broken'))}</span></p>
<p><strong>Requirements with evidence:</strong> {len(by_req)}</p>
</div>
<h2>Requirements</h2>
<table>
<tr><th>Requirement</th><th>Passed/Total</th><th>Status</th></tr>
{''.join(rows)}
</table>
<hr>
{''.join(details)}
</body>
</html>"""

    index_path = output_dir / "index.html"
    index_path.write_text(html_content)
    print(f"Report generated: {index_path} ({len(results)} tests, {len(by_req)} requirements)")


if __name__ == "__main__":
    allure_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/allure-raw")
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("specs-site/evidence")
    generate_report(allure_dir, output_dir)
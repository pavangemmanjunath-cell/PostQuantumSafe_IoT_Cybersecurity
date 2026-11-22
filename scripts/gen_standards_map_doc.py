"""Write docs/release-3/standards_mapping.md from the standards map in the code.

    python scripts/gen_standards_map_doc.py

Keeps the documentation table identical to what ``GET /api/v1/standards-map`` returns.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from safeguard_pq.agents.scoring import PILLAR_DEDUCT, WEIGHTS  # noqa: E402
from safeguard_pq.knowledge import standards_map as sm  # noqa: E402

OUT = ROOT / "docs" / "release-3" / "standards_mapping.md"

PREAMBLE = f"""# Traceable mapping: findings → TIPPSS pillars → deductions → references (Release 3)

This appendix traces every finding type to the IEEE/UL 2933-2024 principles it affects (pillars in the code), the
pillar deduction, the PQ-score category and the public references, and states that pillar scores do not imply
standards compliance.

**Standard.** {sm.STANDARD_TITLE}.

**Scope of the mapping.** {sm.STANDARD_NOTE}

**How a finding changes the scores.** Each finding deducts `d(severity)` points from every pillar it maps to
(`{PILLAR_DEDUCT}`; floor 0). Findings that belong to a PQ-risk category feed the PQ risk score
`S = round(Σ_c w_c · v_c)` with weights `{WEIGHTS}`, where `v_c` is the highest severity value
(critical 100, high 75, medium 50, low 25) among the findings in category `c`; the `migration` category is 75 when
no PQ algorithm is detected and 0 otherwise. Findings without a score category (PHI, prompt injection, clinical safety,
traffic) affect the pillar scores and the SAFE / AT_RISK / UNSAFE status but not `S`.

The table is generated from `backend/src/safeguard_pq/knowledge/standards_map.py` by
`scripts/gen_standards_map_doc.py`; the same data is served at `GET /api/v1/standards-map` and shown in the web
application's Research Results tab.

"""


def main() -> int:
    cov = sm.pillar_coverage()
    coverage_lines = ["| Pillar | Finding types | Agents feeding the pillar |", "|---|---|---|"]
    coverage_lines += [f"| {p} | {v['finding_types']} | {', '.join(v['agents'])} |" for p, v in cov.items()]
    text = PREAMBLE + "## Pillar coverage\n\n" + "\n".join(coverage_lines) + "\n\n## Mapping table\n\n" + sm.markdown_table() + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"Written: {OUT} ({len(sm.STANDARDS_MAP)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

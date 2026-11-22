"""Build the Word version of the Release 3 evidence summary.

    python scripts/build_release3_docx.py [--node-dir DIR]

Reads docs/release-3/README.md and writes docs/release-3/SafeGuard-PQ_Release3_Evidence_Summary.docx: the summary
text and tables plus figures 1-4 of its figure list with numbered captions (no schematic drafts, no appendices).
Layout: A4, Calibri 10.5 pt, shaded table headers, double-column figures at the 16 cm text width and single-column
figures at their printed width, page numbers in the footer.

Rendering uses docx-js (npm package ``docx``) through scripts/build_release3_docx.cjs. The package is not a
dependency of this repository: on first use it is installed with npm into a scratch folder outside the repository
(``--node-dir``, default ``<system temp>/sgpq-docx-js``). Requires Node.js and npm.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
R3 = ROOT / "docs" / "release-3"
SRC = R3 / "README.md"
FIG = R3 / "figures"
OUT = R3 / "SafeGuard-PQ_Release3_Evidence_Summary.docx"
RENDERER = Path(__file__).with_name("build_release3_docx.cjs")
DOCX_VERSION = "9.15.3"  # docx-js release used for the committed Word file
WORD_FIGURES = 4  # figures 1-4 of the figure list go into the Word file
TEXT_WIDTH_DXA = 9070  # A4 (11 906 twips) minus 2 x 2.5 cm side margins = 16.0 cm
TEXT_WIDTH_CM = 16.0
SINGLE_COLUMN_MAX_IN = 4.0  # figures up to this printed width keep their size instead of being enlarged

_ESCAPES = {"\\|": "", "\\*": "", "\\_": "", "\\`": "", "\\[": "", "\\]": ""}
_RESTORE = {v: k[1] for k, v in _ESCAPES.items()}
_TOKEN = re.compile(r"\*\*(?P<b>.+?)\*\*|`(?P<c>[^`]+)`|\[(?P<lt>[^\]]+)\]\((?P<lu>[^)\s]+)\)|\*(?P<i>[^*\s][^*]*?)\*")


# ------------------------------------------------------------------------------------------------ Markdown subset


def _protect(text: str) -> str:
    for k, v in _ESCAPES.items():
        text = text.replace(k, v)
    return text


def _plain(text: str) -> str:
    return "".join(_RESTORE.get(ch, ch) for ch in text)


def _typeset(text: str) -> str:
    """Keep numbers with their units and operators on one line (no-break spaces)."""
    text = re.sub(r"(\d) (?=%|ms\b|USD\b|\d{3}\b)", "\\1\u00a0", text)
    return re.sub(r"\b([nSLτ]) = (?=[\d{])", "\\1\u00a0=\u00a0", text)


def repo_path(url: str) -> str:
    """Repository path of a link that is relative to docs/release-3/."""
    return posixpath.normpath(posixpath.join("docs/release-3", url.split("#")[0])).rstrip("/")


def inline(text: str, base: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Runs ({text, bold, italic, code, link}) for **bold**, *italic*, `code` and [links](...).

    Relative links become text: a code-span label is kept as it is, any other label is followed by the repository
    path in brackets. Absolute http(s) links stay hyperlinks.
    """
    base = base or {}
    runs: list[dict[str, Any]] = []
    pos = 0
    for m in _TOKEN.finditer(text):
        if m.start() > pos:
            runs.append({**base, "text": _plain(text[pos:m.start()])})
        if m.group("b") is not None:
            runs += inline(m.group("b"), {**base, "bold": True})
        elif m.group("c") is not None:
            runs.append({**base, "text": _plain(m.group("c")), "code": True})
        elif m.group("lt") is not None:
            label, url = m.group("lt"), m.group("lu")
            if re.match(r"https?://", url):
                runs += inline(label, {**base, "link": url})
            else:
                inner = inline(label, base)
                runs += inner
                if not all(r.get("code") for r in inner):
                    runs.append({**base, "text": f" ({repo_path(url)})"})
        else:
            runs += inline(m.group("i"), {**base, "italic": True})
        pos = m.end()
    if pos < len(text):
        runs.append({**base, "text": _plain(text[pos:])})
    for r in runs:
        if not r.get("code"):
            r["text"] = _typeset(r["text"])
    return [r for r in runs if r["text"]]


def _breakable(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Table cells: let long code tokens (file names) wrap after underscores (zero-width space)."""
    return [{**r, "text": r["text"].replace("_", "_​").rstrip("​")} if r.get("code") else r for r in runs]


def _cells(row: str) -> list[str]:
    return [c.strip() for c in _protect(row).strip().strip("|").split("|")]


def _align(cell: str) -> str:
    cell = cell.strip()
    if cell.startswith(":") and cell.endswith(":"):
        return "center"
    return "right" if cell.endswith(":") else "left"


def parse_blocks(md: str) -> list[dict[str, Any]]:
    """Headings, paragraphs, block quotes, bullet lists and pipe tables (with an optional docx-widths comment)."""
    lines = md.splitlines()
    blocks: list[dict[str, Any]] = []
    para: list[str] = []
    widths: list[float] | None = None

    def flush() -> None:
        if para:
            blocks.append({"type": "paragraph", "text": " ".join(para)})
            para.clear()

    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            flush()
            i += 1
        elif s.startswith("<!--"):
            flush()
            m = re.match(r"<!--\s*docx-widths:\s*([\d.,\s]+)-->", s)
            widths = [float(x) for x in m.group(1).split(",")] if m else widths
            i += 1
        elif s.startswith("#"):
            flush()
            level = len(s) - len(s.lstrip("#"))
            blocks.append({"type": "heading", "level": level, "text": s[level:].strip()})
            i += 1
        elif s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            header, sep, body = _cells(rows[0]), _cells(rows[1]), [_cells(r) for r in rows[2:]]
            blocks.append({"type": "table", "header": header, "align": [_align(c) for c in sep], "rows": body, "widths": widths})
            widths = None
        elif s.startswith("- "):
            flush()
            items: list[str] = []
            while i < len(lines) and (lines[i].strip().startswith("- ") or (items and lines[i].startswith("  ") and lines[i].strip())):
                line = lines[i].strip()
                if line.startswith("- "):
                    items.append(line[2:])
                else:
                    items[-1] += " " + line
                i += 1
            blocks.append({"type": "bullets", "items": items})
        elif s.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            blocks.append({"type": "note", "text": " ".join(quote)})
        else:
            para.append(s)
            i += 1
    flush()
    return blocks


# ----------------------------------------------------------------------------------------------------- figures


def png_size(path: Path) -> tuple[int, int, float]:
    """Pixel width, pixel height and dots per inch (pHYs chunk; 300 if absent) of a PNG file."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path.name} is not a PNG file")
    width, height = struct.unpack(">II", data[16:24])
    dpi, pos = 300.0, 8
    while pos + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        if kind == b"pHYs":
            ppx, _, unit = struct.unpack(">IIB", data[pos + 8:pos + 17])
            if unit == 1 and ppx:
                dpi = ppx * 0.0254
            break
        if kind == b"IDAT":
            break
        pos += 12 + length
    return width, height, dpi


def figure_blocks(table: dict[str, Any]) -> list[dict[str, Any]]:
    """Figures 1..WORD_FIGURES of the summary's figure table, as image blocks with numbered captions."""
    out = []
    for row in table["rows"]:
        number = int(re.sub(r"\D", "", row[0]) or 0)
        stem = re.search(r"fig_[a-z0-9_]+", row[1])
        if not stem or not 1 <= number <= WORD_FIGURES:
            continue
        png = FIG / f"{stem.group(0)}.png"
        if not png.is_file():
            raise FileNotFoundError(f"{png} is missing; run benchmarks/make_figures.py first")
        w_px, h_px, dpi = png_size(png)
        printed_cm = w_px / dpi * 2.54
        width_cm = printed_cm if printed_cm <= SINGLE_COLUMN_MAX_IN * 2.54 else TEXT_WIDTH_CM
        caption = row[2]
        out.append({"type": "figure", "number": number, "path": str(png), "widthCm": round(width_cm, 3),
                    "heightCm": round(width_cm * h_px / w_px, 3), "caption": inline(caption), "alt": _plain(caption)})
    if len(out) != WORD_FIGURES:
        raise ValueError(f"expected figures 1-{WORD_FIGURES} in the figure table, found {len(out)}")
    return out


# -------------------------------------------------------------------------------------------------------- spec


def column_widths(table: dict[str, Any]) -> list[int]:
    """Column widths in DXA summing to the text width: the docx-widths comment, else proportional to content."""
    n = len(table["header"])
    weights = table.get("widths")
    if not weights or len(weights) != n:
        texts = [table["header"], *table["rows"]]
        weights = [max(4.0, min(40.0, max(len(r[j]) for r in texts))) for j in range(n)]
    dxa = [round(TEXT_WIDTH_DXA * w / sum(weights)) for w in weights]
    dxa[-1] += TEXT_WIDTH_DXA - sum(dxa)
    return dxa


def build_spec(md: str) -> dict[str, Any]:
    blocks = parse_blocks(md)
    spec_blocks: list[dict[str, Any]] = []
    title = ""
    in_figures = False
    for k, b in enumerate(blocks):
        if b["type"] == "heading":
            in_figures = b["level"] == 2 and b["text"].lower() == "figures"
            if b["level"] == 1 and not title:
                title = b["text"]
                spec_blocks.append({"type": "title", "runs": inline(_protect(b["text"]))})
            else:
                spec_blocks.append({"type": "h1" if b["level"] <= 2 else "h2", "runs": inline(_protect(b["text"]))})
            continue
        if in_figures:  # the Word file shows the figures themselves instead of the file list
            if b["type"] == "table":
                spec_blocks += figure_blocks(b)
            continue
        if b["type"] == "paragraph":
            text = b["text"]
            if spec_blocks and spec_blocks[-1]["type"] == "title" and re.fullmatch(r"\*[^*].*\*", text):
                parts = [p for p in text[1:-1].split(" · ") if ".docx" not in p]  # the file does not cite itself
                spec_blocks.append({"type": "subtitle", "runs": inline(_protect(" · ".join(parts)))})
                continue
            nxt = blocks[k + 1]["type"] if k + 1 < len(blocks) else None
            spec_blocks.append({"type": "paragraph", "runs": inline(_protect(text)), "keepNext": nxt == "table"})
        elif b["type"] == "note":
            spec_blocks.append({"type": "note", "runs": inline(_protect(b["text"]))})
        elif b["type"] == "bullets":
            spec_blocks.append({"type": "bullets", "items": [inline(_protect(t)) for t in b["items"]]})
        elif b["type"] == "table":
            spec_blocks.append({"type": "table", "header": [_breakable(inline(c)) for c in b["header"]],
                                "rows": [[_breakable(inline(c)) for c in r] for r in b["rows"]],
                                "align": b["align"], "widths": column_widths(b)})
    return {"title": title, "footer": "SafeGuard-PQ v0.3.0 · Release 3 evidence summary", "textWidth": TEXT_WIDTH_DXA, "blocks": spec_blocks}


# --------------------------------------------------------------------------------------------------- rendering


def ensure_docx_module(node_dir: Path) -> None:
    """Install docx-js into the scratch folder unless the pinned version is already there."""
    pkg = node_dir / "node_modules" / "docx" / "package.json"
    if pkg.is_file() and json.loads(pkg.read_text(encoding="utf-8")).get("version") == DOCX_VERSION:
        return
    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("npm is required to install docx-js (https://nodejs.org)")
    node_dir.mkdir(parents=True, exist_ok=True)
    (node_dir / "package.json").write_text('{"private": true, "description": "scratch folder for scripts/build_release3_docx.py"}\n',
                                          encoding="utf-8")
    print(f"installing docx@{DOCX_VERSION} into {node_dir}")
    subprocess.run([npm, "install", "--no-audit", "--no-fund", "--loglevel=error", f"docx@{DOCX_VERSION}"], cwd=node_dir, check=True)


def drop_folder_entries(path: Path) -> None:
    """Rewrite the zip without directory entries (some Word services refuse packages that contain them)."""
    with zipfile.ZipFile(path) as z:
        items = [(info, z.read(info)) for info in z.infolist() if not info.filename.endswith("/")]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in items:
            z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--node-dir", type=Path, default=Path(tempfile.gettempdir()) / "sgpq-docx-js",
                    help="scratch folder for the docx-js npm package (outside the repository)")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    node = shutil.which("node")
    if not node:
        print("node is required (https://nodejs.org)", file=sys.stderr)
        return 1
    spec = build_spec(SRC.read_text(encoding="utf-8"))
    ensure_docx_module(args.node_dir)
    spec_file = args.node_dir / "release3_summary_spec.json"
    spec_file.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    subprocess.run([node, str(RENDERER), "--spec", str(spec_file), "--out", str(args.out), "--modules", str(args.node_dir)],
                   check=True)
    drop_folder_entries(args.out)
    figures = sum(1 for b in spec["blocks"] if b["type"] == "figure")
    tables = sum(1 for b in spec["blocks"] if b["type"] == "table")
    print(f"Written: {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out} "
          f"({args.out.stat().st_size // 1024} KB; {tables} tables, {figures} figures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

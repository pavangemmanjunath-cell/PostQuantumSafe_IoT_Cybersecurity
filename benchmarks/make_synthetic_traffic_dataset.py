"""Generate a clearly-labelled SYNTHETIC held-out traffic dataset with the project's own simulator.

    python benchmarks/make_synthetic_traffic_dataset.py --out datasets/synthetic_holdout \
        --train-seed 101 --test-seed 202 --windows-per-class 20 --window 100

For each traffic class (benign plus the five network attacks of the simulator catalogue) the
script writes one CSV per split, ``train/<class>.csv`` and ``test/<class>.csv``, holding
``--windows-per-class`` consecutive windows of ``--window`` rows. Rows come from
``Simulation._gen_row`` with the catalogue parameters (``BENIGN_TRAFFIC`` or ``Attack.traffic``),
i.e. exactly the generator the simulator uses for live telemetry. Columns are the CICIoMT2024
subset consumed by the traffic rules plus a ``window_id`` column.

Train and test use different seeds. The test split additionally applies a per-window
multiplicative jitter (default +-10 %) to the packet-size mean, the header-length mean and the
packet rate, so the two splits are not identical in distribution. Window ``w`` of every class is
generated for device ``w mod n_devices`` of the template, so benign packet rates follow the
device base rates (gateway 400/s ... wearable 10/s) instead of a single constant.

This is NOT CICIoMT2024 data and must not be presented as such. The simulator parameters imitate
the *shape* of CICIoMT2024 class statistics and were designed around the shipped rules, so any
detection figure obtained on these files only demonstrates that the evaluation protocol runs.
A README.md and a manifest.json with the exact generation parameters are written next to the data.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from safeguard_pq import __version__  # noqa: E402
from safeguard_pq.simulation import Simulation  # noqa: E402
from safeguard_pq.simulation import catalog as cat  # noqa: E402

CLASSES: tuple[str, ...] = ("benign", "syn_flood", "ddos_volumetric", "port_scan", "mqtt_malformed", "arp_spoofing")
FEATURE_COLUMNS = ["syn_flag_number", "ack_flag_number", "rst_flag_number", "fin_flag_number", "TCP", "UDP",
                   "Rate", "Tot size", "Header_Length"]
COLUMNS = [*FEATURE_COLUMNS, "window_id"]
FLAG_COLUMNS = {"syn_flag_number", "ack_flag_number", "rst_flag_number", "fin_flag_number", "TCP", "UDP"}
SPLITS = ("train", "test")


def class_params(cls: str) -> dict[str, Any]:
    """Generator parameters of a traffic class, copied from the simulator catalogue."""
    if cls == "benign":
        return dict(cat.BENIGN_TRAFFIC)
    traffic = cat.ATTACKS[cls].traffic
    if traffic is None:
        raise ValueError(f"attack '{cls}' has no traffic generator")
    return dict(traffic)


def generate_split(seed: int, windows_per_class: int, window: int, jitter: float,
                   template: str = "hospital_ward") -> dict[str, list[dict[str, Any]]]:
    """Return ``{class: rows}`` for one split; rows carry a ``window_id`` (0-based, consecutive)."""
    sim = Simulation(template=template, seed=seed)
    devices = list(sim.devices.values())
    jit = random.Random(seed * 7919 + 17)  # separate stream so jitter does not perturb the row generator

    def factor() -> float:
        return jit.uniform(1.0 - jitter, 1.0 + jitter) if jitter > 0 else 1.0

    out: dict[str, list[dict[str, Any]]] = {}
    for cls in CLASSES:
        rows: list[dict[str, Any]] = []
        for w in range(windows_per_class):
            d = devices[w % len(devices)]
            p = class_params(cls)
            size_mu, size_sd = p["size"]
            hdr_mu, hdr_sd = p["header"]
            rate = p.get("rate") or d.base_rate  # same fallback as Simulation._gen_row
            p.update(size=(size_mu * factor(), size_sd), header=(hdr_mu * factor(), hdr_sd), rate=rate * factor())
            for _ in range(window):
                row = sim._gen_row(d, p)  # the simulator's own row generator and RNG
                row["window_id"] = w
                rows.append(row)
        out[cls] = rows
    return out


def _fmt(column: str, value: Any) -> str:
    if column == "window_id":
        return str(int(value))
    if column in FLAG_COLUMNS:
        return f"{float(value):.1f}"
    return f"{float(value):.4f}"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(COLUMNS)
        for r in rows:
            writer.writerow([_fmt(c, r[c]) for c in COLUMNS])
    return path.stat().st_size


def _params_table() -> dict[str, dict[str, Any]]:
    table = {}
    for cls in CLASSES:
        p = class_params(cls)
        table[cls] = {
            "p_tcp": p["tcp"], "p_syn": p["syn"], "p_ack": p["ack"], "p_rst": p["rst"], "p_fin": p["fin"],
            "tot_size_mean_sd": list(p["size"]), "header_length_mean_sd": list(p["header"]),
            "rate": p.get("rate") or "device base rate (hospital_ward: 400, 20, 20, 80, 40, 10, 250, 150, 30)",
        }
    return table


def _readme(args: argparse.Namespace, sizes: dict[str, dict[str, int]], total_bytes: int) -> str:
    rows_per_file = args.windows_per_class * args.window
    jitter_pct = round(args.test_jitter * 100)
    lines = [
        "# Synthetic held-out traffic dataset (`datasets/synthetic_holdout`)",
        "",
        "**This is synthetic data generated by this project's own simulator. It is NOT CICIoMT2024 and contains",
        "no real network traffic.** It exists so that the held-out evaluation protocol in",
        "`benchmarks/traffic_rules_holdout.py` can be run end-to-end without third-party data. Detection figures",
        "obtained on these files demonstrate the *pipeline*, not detection performance: the generator parameters",
        "were designed around the shipped traffic rules, so the rules separate these classes almost perfectly.",
        "Real held-out numbers require the CICIoMT2024 train/test CSV folders (see `datasets/README.md`).",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Generator | `safeguard_pq.simulation.Simulation._gen_row` (the live-telemetry row generator), "
        f"software version {__version__} |",
        "| Script | `python benchmarks/make_synthetic_traffic_dataset.py --out datasets/synthetic_holdout "
        f"--train-seed {args.train_seed} --test-seed {args.test_seed} --windows-per-class {args.windows_per_class} "
        f"--window {args.window} --test-jitter {args.test_jitter}` |",
        f"| Template / devices | `{args.template}`; window *w* of every file is generated for device "
        "*w* mod 9 of the template (benign packet rate = device base rate) |",
        f"| Classes | {', '.join(CLASSES)} (benign + the five network attacks of the simulator catalogue) |",
        f"| Splits | `train/` (seed {args.train_seed}, no jitter) and `test/` (seed {args.test_seed}, "
        f"per-window +-{jitter_pct} % jitter on packet-size mean, header-length mean and packet rate) |",
        f"| Windows | {args.windows_per_class} consecutive non-overlapping windows of {args.window} rows per file "
        f"= {rows_per_file} rows per file; `window_id` identifies the window |",
        f"| Size | {total_bytes / 1e6:.2f} MB in total ({len(CLASSES) * len(SPLITS)} CSV files) |",
        "| License | Apache-2.0 (part of this repository) |",
        "| Type | **Synthetic**, stationary, idealised distributions; missing values: none |",
        "| Purpose | pipeline demonstration and tests only |",
        "",
        "## Columns",
        "",
        "Subset of the CICIoMT2024 column names (the features used by `knowledge/traffic_rules.py`) plus `window_id`:",
        "",
        "| Column | Meaning | Unit |",
        "|---|---|---|",
        "| `syn_flag_number`, `ack_flag_number`, `rst_flag_number`, `fin_flag_number` | TCP flag present (0/1; always 0 for UDP rows) | - |",
        "| `TCP`, `UDP` | protocol indicator (0/1, mutually exclusive) | - |",
        "| `Rate` | packet rate, log-normal around the class rate (or device base rate) | packets/s (synthetic scale) |",
        "| `Tot size` | packet size, Gaussian, floored at 40 | bytes |",
        "| `Header_Length` | header-length aggregate, Gaussian, floored at 20 | bytes (CICIoMT semantics) |",
        "| `window_id` | 0-based index of the 100-row window inside the file | - |",
        "",
        "## Generator parameters (from `backend/src/safeguard_pq/simulation/catalog.py`)",
        "",
        "| Class | P(TCP) | P(SYN) | P(ACK) | P(RST) | P(FIN) | Tot size mean (sd) | Header_Length mean (sd) | Rate |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for cls, p in _params_table().items():
        size_mu, size_sd = p["tot_size_mean_sd"]
        hdr_mu, hdr_sd = p["header_length_mean_sd"]
        rate = p["rate"] if isinstance(p["rate"], str) else f"{p['rate']:g}"
        lines.append(f"| {cls} | {p['p_tcp']:g} | {p['p_syn']:g} | {p['p_ack']:g} | {p['p_rst']:g} | {p['p_fin']:g} | "
                     f"{size_mu:g} ({size_sd:g}) | {hdr_mu:g} ({hdr_sd:g}) | {rate} |")
    lines += [
        "",
        "Flag probabilities are conditional on the row being TCP. In the test split, each window draws three",
        f"independent factors from U(1-{args.test_jitter:g}, 1+{args.test_jitter:g}) (seeded with "
        f"`{args.test_seed} * 7919 + 17`) that multiply the size mean, the header mean and the rate; standard",
        "deviations and flag probabilities are unchanged. The train split uses the parameters as shipped.",
        "",
        "## Files",
        "",
        "| Split | File | Rows | Bytes |",
        "|---|---|---|---|",
    ]
    for split in SPLITS:
        for cls in CLASSES:
            lines.append(f"| {split} | `{split}/{cls}.csv` | {rows_per_file} | {sizes[split][cls]} |")
    lines += [
        "",
        "## Usage",
        "",
        "```bash",
        "python benchmarks/traffic_rules_holdout.py --train-dir datasets/synthetic_holdout/train \\",
        "    --test-dir datasets/synthetic_holdout/test --out benchmarks/results/traffic_rules_holdout.json",
        "```",
        "",
        "Labels are taken from the file name (`benign.csv` -> benign, anything else -> attack; the class is the",
        "file stem), exactly as the holdout script does for CICIoMT2024 file names. Regenerating with the command",
        "above reproduces the files byte-for-byte (seeded `random.Random`, no timestamps).",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("datasets") / "synthetic_holdout")
    ap.add_argument("--train-seed", type=int, default=101)
    ap.add_argument("--test-seed", type=int, default=202)
    ap.add_argument("--windows-per-class", type=int, default=20)
    ap.add_argument("--window", type=int, default=100)
    ap.add_argument("--test-jitter", type=float, default=0.10,
                    help="per-window multiplicative jitter (+-fraction) on size/header means and rate, test split only")
    ap.add_argument("--template", default="hospital_ward")
    args = ap.parse_args(argv)
    if args.windows_per_class < 1 or args.window < 1 or args.test_jitter < 0 or args.test_jitter >= 1:
        print("invalid --windows-per-class / --window / --test-jitter", file=sys.stderr)
        return 2

    seeds = {"train": args.train_seed, "test": args.test_seed}
    jitter = {"train": 0.0, "test": args.test_jitter}
    sizes: dict[str, dict[str, int]] = {}
    manifest_files: dict[str, dict[str, Any]] = {}
    for split in SPLITS:
        data = generate_split(seeds[split], args.windows_per_class, args.window, jitter[split], args.template)
        sizes[split] = {}
        manifest_files[split] = {}
        for cls, rows in data.items():
            path = args.out / split / f"{cls}.csv"
            nbytes = write_csv(path, rows)
            sizes[split][cls] = nbytes
            manifest_files[split][f"{cls}.csv"] = {"class": cls, "label": "benign" if cls == "benign" else "attack",
                                                   "rows": len(rows), "windows": args.windows_per_class, "bytes": nbytes}
            print(f"{split}/{cls}.csv: {len(rows)} rows, {nbytes} bytes")
    total = sum(sum(s.values()) for s in sizes.values())

    manifest = {
        "dataset": "synthetic_holdout",
        "generator": "safeguard_pq.simulation.Simulation._gen_row",
        "software_version": __version__,
        "synthetic": True,
        "not_ciciomt2024": "This dataset is generated by the project simulator; it is not CICIoMT2024 data.",
        "license": "Apache-2.0",
        "template": args.template,
        "window_rows": args.window,
        "windows_per_class": args.windows_per_class,
        "columns": COLUMNS,
        "classes": list(CLASSES),
        "splits": {split: {"seed": seeds[split], "jitter": jitter[split], "files": manifest_files[split]} for split in SPLITS},
        "jitter_rule": "test split only: per window, size mean, header mean and rate are each multiplied by an independent "
                       "U(1-j, 1+j) factor drawn from random.Random(seed * 7919 + 17); sds and flag probabilities unchanged",
        "device_assignment": "window w of every file is generated for device w mod n_devices of the template",
        "generator_parameters": _params_table(),
        "total_bytes": total,
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (args.out / "README.md").write_text(_readme(args, sizes, total), encoding="utf-8")
    print(f"\nWritten {len(CLASSES) * len(SPLITS)} CSV files ({total / 1e6:.2f} MB), manifest.json and README.md to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

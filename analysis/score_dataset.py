"""
Experiment 3: does the FFT moire score separate REAL phone photos of
scenes from REAL phone photos of screens?

Same analysis as run_experiment.py, but on our own collected dataset
instead of simulated recaptures. Uses only photos that passed
dataset/ingest.py (status=ok in the manifest).

Usage:
    python dataset/ingest.py dataset/raw           # first, writes the manifest
    python analysis/score_dataset.py [photo_folder] [--manifest dataset/manifest.csv]

Writes: out/real_scores.csv, out/real_histogram.png
"""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from moire import moire_score  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

ap = argparse.ArgumentParser(description="Moire score on the collected real-vs-screen dataset")
ap.add_argument("folder", nargs="?", default=str(ROOT / "dataset" / "raw"),
                help="photo folder (default: dataset/raw)")
ap.add_argument("--manifest", default=str(ROOT / "dataset" / "manifest.csv"),
                help="manifest from ingest.py (default: dataset/manifest.csv)")
args = ap.parse_args()
folder = Path(args.folder)

with open(args.manifest, newline="") as f:
    reader = csv.DictReader(f)
    columns = reader.fieldnames
    manifest = [r for r in reader if r["status"] == "ok"]

# ---- 1. score every accepted photo ----
rows, missing = [], []
for r in manifest:
    path = folder / r["file"]
    if not path.is_file():
        missing.append(r["file"])
        continue
    rows.append({**r, "score": round(moire_score(path)[0], 3)})

if missing:
    print(f"warning: {len(missing)} manifest photos not found in {folder}, skipped:")
    for m in missing:
        print(f"   {m}")
if not rows:
    sys.exit("no photos to score (is the manifest for this folder?)")

with open(OUT / "real_scores.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=columns + ["score"])
    wr.writeheader()
    wr.writerows(rows)

real = np.array([r["score"] for r in rows if r["label"] == "real"])
scr = np.array([r["score"] for r in rows if r["label"] == "screen"])

# ---- 2. report ----
print("by label:")
for name, v in (("real", real), ("screen", scr)):
    if len(v):
        print(f"   {name:<7} n={len(v):3d}  score min {v.min():.2f}  mean {v.mean():.2f}  max {v.max():.2f}")
    else:
        print(f"   {name:<7} n=  0")


def mean_by(key):
    groups = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r["score"])
    for k in sorted(groups):
        print(f"   {k:<12} n={len(groups[k]):3d}  mean {np.mean(groups[k]):.2f}")


print("mean score by phone:")
mean_by("phone")
print("mean score by screen type:")
mean_by("screen")

best_t = None
if len(real) and len(scr):
    # pick the threshold with best accuracy (on this dataset, so it is optimistic)
    cands = np.unique(np.concatenate([real, scr]))
    best_acc = -1
    for t in cands:
        acc = ((real < t).sum() + (scr >= t).sum()) / (len(real) + len(scr))
        if acc > best_acc:
            best_t, best_acc = t, acc
    fp = int((real >= best_t).sum())
    fn = int((scr < best_t).sum())
    print(f"best threshold {best_t:.2f}: accuracy {best_acc*100:.1f}%  "
          f"(real flagged as screen: {fp}, screens missed: {fn})")
else:
    print("best threshold: needs both real and screen photos")

print("highest-scoring real photos (likely false alarms):")
for r in sorted([r for r in rows if r["label"] == "real"], key=lambda r: -r["score"])[:5]:
    print(f"   {r['score']:6.2f}  {r['file']}")
print("lowest-scoring screen photos (likely misses):")
for r in sorted([r for r in rows if r["label"] == "screen"], key=lambda r: r["score"])[:5]:
    print(f"   {r['score']:6.2f}  {r['file']}")

# paired check: each screen photo vs the real photo with the same phone, scene, idx
reals = {(r["phone"], r["scene"], r["idx"]): r for r in rows if r["label"] == "real"}
pairs = []
for r in rows:
    key = (r["phone"], r["scene"], r["idx"])
    if r["label"] == "screen" and key in reals:
        pairs.append((reals[key], r))
higher = sum(s["score"] > re["score"] for re, s in pairs)
print(f"paired check: screen scored higher than its real photo in {higher} of {len(pairs)} pairs")
for re, s in pairs:
    if s["score"] <= re["score"]:
        print(f"   not higher: {s['file']} {s['score']:.2f} vs {re['file']} {re['score']:.2f}")

# ---- 3. figure (same style as moire_histogram.png) ----
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

fig, ax = plt.subplots(figsize=(7.5, 3.6))
bins = np.linspace(0, max(np.concatenate([real, scr])) + 0.5, 30)
ax.hist(real, bins, alpha=0.75, label=f"Real photos (n={len(real)})", color="#3B7DD8")
ax.hist(scr, bins, alpha=0.75, label=f"Photos of screens (n={len(scr)})", color="#D9662B")
if best_t is not None:
    ax.axvline(best_t, color="#333", ls="--", lw=1)
    ax.text(best_t - 0.1, ax.get_ylim()[1] * 0.95, f"threshold {best_t:.1f}", fontsize=9, ha="right")
ax.set_xlabel("Moire score (peak strength in noise units)")
ax.set_ylabel("Number of images")
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, fontsize=9, loc="upper left")
fig.tight_layout()
fig.savefig(OUT / "real_histogram.png", dpi=130)
plt.close(fig)
print("saved", OUT / "real_scores.csv", "and", OUT / "real_histogram.png")

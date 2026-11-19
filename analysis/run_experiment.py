"""
Experiment 2: does the FFT moire score separate real photos from
(simulated) screen recaptures?

Real set:      8 public sample photos/textures, each at 4 scales,
               resized properly (anti-aliased) and JPEG compressed.
Recapture set: the same 8 images through simulate_recapture.py with
               6 different angle / distance / blur settings.

This is a pipeline check on SIMULATED data. Real numbers will come from
our own phone photos of screens (dataset collection starts next week).

Usage: python analysis/run_experiment.py
Writes: out/moire_scores.csv, out/moire_histogram.png, out/moire_examples.png
"""
import csv
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from skimage import data

sys.path.insert(0, str(Path(__file__).resolve().parent))
from moire import moire_score, load_gray, spectrum, residual_peaks, BAND  # noqa: E402
from simulate_recapture import recapture                                   # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "out"
OUT.mkdir(exist_ok=True)

IMAGES = ["astronaut", "coffee", "chelsea", "rocket", "camera", "brick", "grass", "gravel"]
REAL_SCALES = [1.0, 0.85, 0.7, 1.25]
# (angle deg, camera/screen scale, lens blur px)
RECAP_SETTINGS = [(1, 0.37, 0.6), (3, 0.41, 0.6), (-2, 0.45, 1.0),
                  (5, 0.52, 1.0), (0.5, 0.60, 1.5), (-4, 0.66, 1.5)]


def jpeg(img, q=88):
    b = io.BytesIO()
    img.convert("RGB").save(b, "JPEG", quality=q)
    return Image.open(io.BytesIO(b.getvalue()))


rows = []
for name in IMAGES:
    base = Image.fromarray(getattr(data, name)())
    for s in REAL_SCALES:
        w, h = base.size
        img = jpeg(base.resize((int(w * s), int(h * s)), Image.LANCZOS))
        rows.append({"image": name, "label": "real", "setting": f"scale={s}",
                     "score": round(moire_score(img)[0], 3)})
    for i, (ang, sc, bl) in enumerate(RECAP_SETTINGS):
        img = recapture(base, angle=ang, scale=sc, blur=bl, seed=i)
        rows.append({"image": name, "label": "recapture",
                     "setting": f"angle={ang},scale={sc},blur={bl}",
                     "score": round(moire_score(img)[0], 3)})

with open(OUT / "moire_scores.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=rows[0].keys())
    wr.writeheader()
    wr.writerows(rows)

real = np.array([r["score"] for r in rows if r["label"] == "real"])
rec = np.array([r["score"] for r in rows if r["label"] == "recapture"])

# pick the threshold with best accuracy (on this small simulated set)
cands = np.unique(np.concatenate([real, rec]))
best_t, best_acc = None, -1
for t in cands:
    acc = ((real < t).sum() + (rec >= t).sum()) / (len(real) + len(rec))
    if acc > best_acc:
        best_t, best_acc = t, acc

fp = int((real >= best_t).sum())
fn = int((rec < best_t).sum())
print(f"real photos      n={len(real):2d}  score min {real.min():.2f}  mean {real.mean():.2f}  max {real.max():.2f}")
print(f"recaptures (sim) n={len(rec):2d}  score min {rec.min():.2f}  mean {rec.mean():.2f}  max {rec.max():.2f}")
print(f"best threshold {best_t:.2f}: accuracy {best_acc*100:.1f}%  "
      f"(real flagged as screen: {fp}, screens missed: {fn})")
print("highest-scoring real photos:")
for r in sorted([r for r in rows if r["label"] == "real"], key=lambda r: -r["score"])[:3]:
    print(f"   {r['image']:10s} {r['setting']:12s} {r['score']:.2f}")
print("by blur level (recaptures):")
for bl in sorted({s[2] for s in RECAP_SETTINGS}):
    v = [r["score"] for r in rows if r["label"] == "recapture" and r["setting"].endswith(f"blur={bl}")]
    print(f"   blur {bl}: mean {np.mean(v):.2f}  min {np.min(v):.2f}")

# ---- figures ----
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

fig, ax = plt.subplots(figsize=(7.5, 3.6))
bins = np.linspace(0, max(rec.max(), real.max()) + 0.5, 30)
ax.hist(real, bins, alpha=0.75, label=f"Real photos (n={len(real)})", color="#3B7DD8")
ax.hist(rec, bins, alpha=0.75, label=f"Simulated screen recaptures (n={len(rec)})", color="#D9662B")
ax.axvline(best_t, color="#333", ls="--", lw=1)
ax.text(best_t - 0.1, ax.get_ylim()[1] * 0.95, f"threshold {best_t:.1f}", fontsize=9, ha="right")
ax.set_xlabel("Moire score (peak strength in noise units)")
ax.set_ylabel("Number of images")
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, fontsize=9, loc="upper left")
fig.tight_layout()
fig.savefig(OUT / "moire_histogram.png", dpi=130)
plt.close(fig)

# example: one real vs one recapture, image + residual peaks
base = Image.fromarray(data.coffee())
pair = [("Real photo", jpeg(base)), ("Simulated recapture", recapture(base, 3, 0.41, 0.6, seed=1))]
fig, ax = plt.subplots(2, 2, figsize=(7.5, 7.2))
for i, (title, img) in enumerate(pair):
    g = load_gray(img)
    resid, band, _ = residual_peaks(spectrum(g))
    s, _ = moire_score(img)
    ax[i, 0].imshow(g[128:384, 128:384], cmap="gray")
    ax[i, 0].set_title(f"{title} (zoomed crop)", fontsize=10)
    ax[i, 1].imshow(np.where(band, np.clip(resid, 0, None), 0), cmap="magma", vmin=0, vmax=4)
    ax[i, 1].set_title(f"Frequency peaks, score {s:.1f}", fontsize=10)
    for a in ax[i]:
        a.axis("off")
fig.tight_layout()
fig.savefig(OUT / "moire_examples.png", dpi=120)
plt.close(fig)
print("saved figures to", OUT)

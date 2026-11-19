"""
Moire detection using the 2D Fourier transform (FFT).

Idea: when a camera photographs a screen, the screen's regular pixel grid
interferes with the camera's sensor grid. In the frequency domain this
shows up as sharp, isolated bright peaks away from the centre. Natural
scenes have a smooth spectrum that falls off with frequency.

So we:
  1. take a grayscale centre crop and apply a window (to avoid edge effects)
  2. compute the log-magnitude spectrum
  3. subtract the "expected" smooth level at each radius (radial median)
  4. look for strong leftover peaks in the mid-to-high frequency band

Usage:
    python analysis/moire.py <image.jpg> [--plot out.png]
"""
import argparse

import numpy as np
from PIL import Image

CROP = 512                 # analysis size in pixels
BAND = (0.15, 0.95)        # frequency band to search, as fraction of Nyquist


def load_gray(path_or_img, crop=CROP):
    img = path_or_img if isinstance(path_or_img, Image.Image) else Image.open(path_or_img)
    g = np.asarray(img.convert("L"), dtype=np.float64)
    h, w = g.shape
    s = min(crop, h, w)
    top, left = (h - s) // 2, (w - s) // 2
    return g[top:top + s, left:left + s]


def spectrum(gray):
    g = gray - gray.mean()
    win = np.outer(np.hanning(g.shape[0]), np.hanning(g.shape[1]))
    f = np.fft.fftshift(np.fft.fft2(g * win))
    return np.log1p(np.abs(f))


def residual_peaks(spec):
    """Spectrum minus its radial median: what stands out above 'normal'."""
    h, w = spec.shape
    yy, xx = np.indices(spec.shape)
    r = np.hypot(yy - h / 2, xx - w / 2) / (min(h, w) / 2)   # 0 = centre, 1 = Nyquist
    rbin = np.round(r * 200).astype(int)
    med = np.zeros(rbin.max() + 1)
    for b in np.unique(rbin):
        med[b] = np.median(spec[rbin == b])
    resid = spec - med[rbin]
    band = (r >= BAND[0]) & (r <= BAND[1])
    return resid, band, r


def moire_score(path_or_img):
    """Higher = more screen-like. Returns (score, details)."""
    spec = spectrum(load_gray(path_or_img))
    resid, band, _ = residual_peaks(spec)
    vals = resid[band]
    noise = np.median(np.abs(vals - np.median(vals))) * 1.4826 + 1e-9   # robust std
    top = np.sort(vals)[-20:]                    # 20 strongest points (peaks come in pairs)
    score = float(np.mean(top) / noise)          # peak strength in "noise units"
    return score, {"peak_mean": float(np.mean(top)), "noise": float(noise)}


def plot(path, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    gray = load_gray(path)
    spec = spectrum(gray)
    resid, band, _ = residual_peaks(spec)
    score, _ = moire_score(path)
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.4))
    ax[0].imshow(gray, cmap="gray"); ax[0].set_title("Centre crop")
    ax[1].imshow(spec, cmap="magma"); ax[1].set_title("Log spectrum")
    ax[2].imshow(np.where(band, np.clip(resid, 0, None), 0), cmap="magma")
    ax[2].set_title(f"Peaks above normal (score {score:.1f})")
    for a in ax:
        a.axis("off")
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("image")
    p.add_argument("--plot")
    a = p.parse_args()
    s, d = moire_score(a.image)
    print(f"moire score: {s:.2f}   {d}")
    if a.plot:
        plot(a.image, a.plot)
        print("saved", a.plot)

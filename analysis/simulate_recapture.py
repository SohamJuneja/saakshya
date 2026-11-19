"""
Simulates photographing an image off a screen.

This is ONLY for testing the analysis code before we collect real
screen photos. It is not a substitute for the real dataset.

Steps that mimic a real recapture:
  1. "display" the image on an LCD: each pixel becomes R, G, B sub-pixel
     stripes with a thin dark gap (the screen's pixel grid)
  2. the camera sees it at a small angle and a slightly different scale
     (camera pixels do not line up with screen pixels -> aliasing)
  3. a slight lens blur, sensor noise and JPEG compression
"""
import io

import numpy as np
from PIL import Image, ImageFilter


def lcd_render(img, sub=3, gap=0.25):
    a = np.asarray(img.convert("RGB"), dtype=np.float32)
    h, w, _ = a.shape
    out = np.zeros((h * sub, w * sub, 3), np.float32)
    for c in range(3):                         # vertical R | G | B stripes
        out[:, c::sub, c] = np.repeat(a[:, :, c], sub, axis=0)
    rows = np.ones(h * sub, np.float32)
    rows[sub - 1::sub] = 1 - gap               # dark line between pixel rows
    out *= rows[:, None, None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def recapture(img, angle=2.0, scale=0.37, blur=0.6, noise=3.0, quality=88, seed=0):
    rng = np.random.default_rng(seed)
    screen = lcd_render(img)
    screen = screen.rotate(angle, resample=Image.BILINEAR, expand=False)
    w, h = screen.size
    # camera samples the screen without an anti-aliasing filter
    shot = screen.resize((int(w * scale), int(h * scale)), Image.NEAREST)
    shot = shot.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(shot, np.float32) + rng.normal(0, noise, (shot.size[1], shot.size[0], 3))
    shot = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    shot.save(buf, "JPEG", quality=quality)
    return Image.open(io.BytesIO(buf.getvalue()))

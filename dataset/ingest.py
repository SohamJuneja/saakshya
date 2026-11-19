"""
Checks a folder of collected photos and writes dataset/manifest.csv.

For every file in the folder it:
  1. checks the filename against <phone>_<label>_<screen>_<scene>_<nnn>.jpg
     (see dataset/README.md)
  2. reads EXIF camera make/model and the image width/height
  3. rejects photos with no EXIF or a shorter side under 1000 px,
     which usually means the photo went through WhatsApp or similar

Usage:
    python dataset/ingest.py <photo_folder> [--out dataset/manifest.csv]

Status values in the manifest:
    ok          passed every check
    bad_name    filename does not follow the scheme
    unreadable  not a valid image file
    no_exif     no camera make/model in EXIF
    too_small   shorter side under MIN_SIDE pixels
"""
import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent.parent
MIN_SIDE = 1000
LABELS = ("real", "screen")
SCREENS = ("none", "laptoplcd", "phoneoled", "monitor", "tv")
EXIF_MAKE, EXIF_MODEL = 0x010F, 0x0110

NAME_RE = re.compile(
    r"^(?P<phone>[a-z0-9]+)_(?P<label>[a-z]+)_(?P<screen>[a-z]+)_"
    r"(?P<scene>[a-z0-9]+)_(?P<idx>\d{3})\.jpg$"
)
COLUMNS = ["file", "phone", "label", "screen", "scene", "idx",
           "make", "model", "width", "height", "status"]


def parse_name(name):
    """Returns (fields, None) for a valid name, or (None, reason)."""
    if name != name.lower():
        return None, "must be all lowercase"
    if " " in name:
        return None, "contains a space"
    m = NAME_RE.match(name)
    if not m:
        return None, "does not match <phone>_<label>_<screen>_<scene>_<nnn>.jpg"
    f = m.groupdict()
    if f["label"] not in LABELS:
        return None, f"label '{f['label']}' must be one of {'|'.join(LABELS)}"
    if f["screen"] not in SCREENS:
        return None, f"screen '{f['screen']}' must be one of {'|'.join(SCREENS)}"
    if f["label"] == "real" and f["screen"] != "none":
        return None, "real photos must have screen 'none'"
    if f["label"] == "screen" and f["screen"] == "none":
        return None, "screen photos need a screen type, not 'none'"
    if f["idx"] == "000":
        return None, "number must start at 001"
    return f, None


def read_image(path):
    """Returns (make, model, width, height) or raises on unreadable files."""
    with Image.open(path) as img:
        exif = img.getexif()
        make = str(exif.get(EXIF_MAKE, "")).strip("\x00 ")
        model = str(exif.get(EXIF_MODEL, "")).strip("\x00 ")
        width, height = img.size
    return make, model, width, height


def ingest(folder):
    rows, problems = [], []
    files = sorted(p for p in Path(folder).iterdir()
                   if p.is_file() and not p.name.startswith("."))
    for p in files:
        row = dict.fromkeys(COLUMNS, "")
        row["file"] = p.name
        fields, reason = parse_name(p.name)
        if fields:
            row.update(fields)
        try:
            row["make"], row["model"], row["width"], row["height"] = read_image(p)
        except (UnidentifiedImageError, OSError) as e:
            row["status"] = "unreadable"
            problems.append((p.name, "unreadable", str(e)))
            if not fields:
                problems.append((p.name, "bad_name", reason))
            rows.append(row)
            continue

        if not fields:
            row["status"] = "bad_name"
            problems.append((p.name, "bad_name", reason))
        elif not (row["make"] or row["model"]):
            row["status"] = "no_exif"
            problems.append((p.name, "no_exif", "no camera make/model (sent via WhatsApp?)"))
        elif min(row["width"], row["height"]) < MIN_SIDE:
            row["status"] = "too_small"
            problems.append((p.name, "too_small",
                             f"{row['width']}x{row['height']}, shorter side < {MIN_SIDE} px "
                             "(compressed?)"))
        else:
            row["status"] = "ok"
        rows.append(row)
    return rows, problems


def print_summary(rows, problems):
    ok = [r for r in rows if r["status"] == "ok"]
    print(f"Checked {len(rows)} files: {len(ok)} ok, {len(rows) - len(ok)} rejected\n")

    if problems:
        print("Problems:")
        for name, status, reason in problems:
            print(f"  {status:<11}{name}  ({reason})")
        print()

    counts = Counter((r["phone"], r["label"]) for r in ok)
    phones = sorted({r["phone"] for r in ok})
    print("Accepted photos by phone x label:")
    if not phones:
        print("  (none)")
        return
    w = max(len("phone"), *(len(p) for p in phones))
    print(f"  {'phone':<{w}}  {'real':>6}  {'screen':>6}  {'total':>6}")
    for ph in phones:
        r, s = counts[(ph, "real")], counts[(ph, "screen")]
        print(f"  {ph:<{w}}  {r:>6}  {s:>6}  {r + s:>6}")
    tr = sum(counts[(p, "real")] for p in phones)
    ts = sum(counts[(p, "screen")] for p in phones)
    print(f"  {'total':<{w}}  {tr:>6}  {ts:>6}  {tr + ts:>6}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("folder", help="folder of photos, e.g. dataset/raw")
    ap.add_argument("--out", default=str(ROOT / "dataset" / "manifest.csv"),
                    help="where to write the manifest (default: dataset/manifest.csv)")
    a = ap.parse_args()

    if not Path(a.folder).is_dir():
        sys.exit(f"not a folder: {a.folder}")

    rows, problems = ingest(a.folder)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=COLUMNS)
        wr.writeheader()
        wr.writerows(rows)

    print_summary(rows, problems)
    print(f"\nWrote {a.out}")


if __name__ == "__main__":
    main()

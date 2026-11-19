"""
Experiment 1: does the verifier catch edits?

Signs a photo, then makes four versions and verifies each:
  1. original signed photo                    -> expect AUTHENTIC
  2. a few pixel bytes changed in the file    -> expect TAMPERED
  3. photo opened and re-saved (manifest lost) -> expect UNSIGNED
  4. unsigned original                        -> expect UNSIGNED

Usage: python signing/tamper_test.py samples/real_scene.jpg
"""
import io
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sign import sign_photo   # noqa: E402
from verify import verify     # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "out"
OUT.mkdir(exist_ok=True)

src = Path(sys.argv[1] if len(sys.argv) > 1 else "samples/real_scene.jpg")
signed = OUT / "t1_signed.jpg"
sign_photo(str(src), str(signed))

# 2. change 16 bytes inside the compressed image data (not the manifest)
raw = bytearray(signed.read_bytes())
eoi = raw.rfind(b"\xff\xd9")
for i in range(eoi - 3000, eoi - 2984):
    if raw[i] != 0xFF and raw[i - 1] != 0xFF:
        raw[i] ^= 0x01
edited = OUT / "t2_pixels_changed.jpg"
edited.write_bytes(bytes(raw))

# 3. re-save through an image editor (strips the manifest)
buf = io.BytesIO()
Image.open(signed).save(buf, "JPEG", quality=92)
resaved = OUT / "t3_resaved.jpg"
resaved.write_bytes(buf.getvalue())

# 5. signed by an attacker who made their own certificate chain
import json, subprocess, tempfile, shutil   # noqa: E401,E402
import c2pa                                  # noqa: E402
from sign import build_manifest              # noqa: E402
rogue_dir = Path(tempfile.mkdtemp())
shutil.copytree(Path(__file__).parent, rogue_dir / "signing")
subprocess.run([sys.executable, str(rogue_dir / "signing" / "make_test_certs.py")],
               check=True, capture_output=True)
rogue_info = c2pa.C2paSignerInfo(b"es256", (rogue_dir / "certs/device_chain.pem").read_bytes(),
                                 (rogue_dir / "certs/device_key.pem").read_bytes(), None)
rogue = OUT / "t5_rogue_signed.jpg"
with c2pa.Signer.from_info(rogue_info) as s:
    c2pa.Builder(json.dumps(build_manifest())).sign_file(str(src), str(rogue), s)
shutil.rmtree(rogue_dir)

cases = [
    ("Original signed photo", signed, "AUTHENTIC"),
    ("16 bytes of image data changed", edited, "TAMPERED"),
    ("Opened and re-saved", resaved, "UNSIGNED"),
    ("Never signed", src, "UNSIGNED"),
    ("Signed with attacker's own cert", rogue, "UNTRUSTED"),
]

print(f"{'Case':<34}{'Expected':<12}{'Got':<12}{'Detail'}")
print("-" * 90)
passed = 0
for label, path, expected in cases:
    r = verify(path)
    ok = r["verdict"] == expected
    passed += ok
    detail = ", ".join(r["details"][:2]) if r["details"] else ""
    print(f"{label:<34}{expected:<12}{r['verdict']:<12}{detail}")
print(f"\n{passed}/{len(cases)} cases matched")

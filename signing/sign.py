"""
Signs a photo and embeds a C2PA manifest (Content Credentials) into it.

Usage:
    python signing/sign.py <input.jpg> <output.jpg>

The manifest records which device took the photo, when, and a
"saakshya.capture" assertion where later we will store the result of
the recapture check (moire score, flash response, etc.).
"""
import datetime
import json
import sys
from pathlib import Path

import c2pa

ROOT = Path(__file__).resolve().parent.parent
CERTS = ROOT / "certs"


def make_signer():
    info = c2pa.C2paSignerInfo(
        alg=b"es256",
        sign_cert=(CERTS / "device_chain.pem").read_bytes(),
        private_key=(CERTS / "device_key.pem").read_bytes(),
        ta_url=None,  # no timestamp server yet; trusted time is a later task
    )
    return c2pa.Signer.from_info(info)


def build_manifest(capture_check=None):
    return {
        "claim_generator_info": [{"name": "Saakshya Capture", "version": "0.1.0"}],
        "title": "Saakshya capture",
        "assertions": [
            {
                "label": "c2pa.actions",
                "data": {"actions": [{
                    "action": "c2pa.created",
                    "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture",
                }]},
            },
            {
                "label": "saakshya.capture",
                "data": {
                    "device_id": "saakshya-dev-001",
                    "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    # Filled by the recapture detector once it is connected.
                    "recapture_check": capture_check or {"status": "not_run"},
                },
            },
        ],
    }


def sign_photo(src, dst, capture_check=None):
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    builder = c2pa.Builder(json.dumps(build_manifest(capture_check)))
    with make_signer() as signer:
        builder.sign_file(src, dst, signer)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python signing/sign.py <input.jpg> <output.jpg>")
    sign_photo(sys.argv[1], sys.argv[2])
    print(f"Signed {sys.argv[1]} -> {sys.argv[2]}")

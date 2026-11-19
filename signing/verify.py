"""
Verifies a Saakshya-signed photo.

Usage:
    python signing/verify.py <photo.jpg>

Result is one of:
    AUTHENTIC   signature valid, issued by our CA, image unchanged
    TAMPERED    manifest present but image data or manifest was changed
    UNSIGNED    no Content Credentials found
    UNTRUSTED   valid signature, but not from a device we trust
"""
import json
import sys
from pathlib import Path

import c2pa

ROOT = Path(__file__).resolve().parent.parent
CA_CERT = ROOT / "certs" / "ca_cert.pem"


def verify(path):
    settings = c2pa.Settings.from_dict({
        "trust": {"trust_anchors": CA_CERT.read_text()},
        "verify": {"verify_trust": True},
    })
    try:
        reader = c2pa.Reader(str(path), context=c2pa.Context(settings=settings))
    except c2pa.C2paError as e:
        if "ManifestNotFound" in type(e).__name__ or "not found" in str(e).lower():
            return {"verdict": "UNSIGNED", "details": []}
        return {"verdict": "TAMPERED", "details": [str(e)]}

    data = json.loads(reader.json())
    state = reader.get_validation_state()
    failures = [s["code"] for s in data.get("validation_status") or []]

    active = data["manifests"][data["active_manifest"]]
    capture = next((a["data"] for a in active.get("assertions", [])
                    if a["label"] == "saakshya.capture"), {})

    if state == "Trusted" and not failures:
        verdict = "AUTHENTIC"
    elif failures == ["signingCredential.untrusted"]:
        verdict = "UNTRUSTED"
    else:
        verdict = "TAMPERED"

    return {
        "verdict": verdict,
        "state": state,
        "details": failures,
        "device": capture.get("device_id"),
        "captured_at": capture.get("captured_at"),
        "recapture_check": capture.get("recapture_check"),
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python signing/verify.py <photo.jpg>")
    print(json.dumps(verify(sys.argv[1]), indent=2))

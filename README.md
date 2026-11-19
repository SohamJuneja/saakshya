# Saakshya

A camera system that signs photos at capture time and refuses to sign
photos of screens. Final-year major project, NIT Hamirpur.

## Folder layout

| Folder | What's in it |
| --- | --- |
| `signing/` | Test certificates, photo signing (C2PA), verifier, tamper test |
| `analysis/` | Recapture detection experiments (FFT moire score) |
| `dataset/` | Our real-vs-screen photo dataset (collection starts week 2) |
| `samples/` | Sample photos for quick tests |
| `docs/` | Weekly reports and notes |
| `out/` | Generated results (safe to delete) |

## Setup

```bash
pip install -r requirements.txt
python signing/make_test_certs.py      # once, creates certs/
```

## Try it

```bash
# sign and verify a photo
python signing/sign.py samples/real_scene.jpg out/signed.jpg
python signing/verify.py out/signed.jpg

# Experiment 1: does the verifier catch edits?
python signing/tamper_test.py samples/real_scene.jpg

# Moire score on any photo, with a spectrum plot
python analysis/moire.py samples/real_scene.jpg --plot out/spectrum.png

# Experiment 2: moire score on real vs simulated screen photos
python analysis/run_experiment.py
```

## Notes

- `certs/device_key.pem` is a private key. It is in `.gitignore`; never commit it.
  Each member can generate their own test certs locally.
- The certificates are test certificates from our own "Saakshya Test CA".
  Real deployment needs keys inside the secure element (Phase 3).
- `analysis/simulate_recapture.py` fakes a screen photo for testing code only.
  All reported detection results must come from real photos in `dataset/`.

# Photo collection protocol

We are building a dataset of **real photos** and **photos of screens** so we
can test whether the moire detector works on real phone cameras, not just on
simulated data. Small mistakes in how photos are taken or transferred can ruin
the screen photos for our purpose, so please follow every step below.

## 1. Name every file like this

```
<phone>_<label>_<screen>_<scene>_<nnn>.jpg
```

All lowercase, no spaces, no extra underscores inside a field.

| Field | Allowed values | Notes |
| --- | --- | --- |
| `phone` | letters and digits, e.g. `pixel7`, `iphone13`, `redminote12` | Same name every time for the same phone |
| `label` | `real` or `screen` | `real` = photo of the actual scene, `screen` = photo of a screen showing it |
| `screen` | `none`, `laptoplcd`, `phoneoled`, `monitor`, `tv` | Must be `none` for `real`, and must **not** be `none` for `screen` |
| `scene` | letters and digits, e.g. `brick`, `fabric`, `desk` | Short word for what is in the photo |
| `nnn` | three digits, `001` to `999` | Counts up per phone and scene |

Examples of one pair:

```
pixel7_real_none_brick_001.jpg
pixel7_screen_laptoplcd_brick_001.jpg
```

The real photo and its screen photo share the same `phone`, `scene` and `nnn`.

## 2. Paired capture

For every scene:

1. Photograph the real scene. This is the `real` photo.
2. Open **that same photo** full screen on a screen (laptop, phone, monitor
   or TV) with brightness at maximum.
3. Photograph the screen so it fills about **80% of the frame**, from
   **20 to 80 cm** away. This is the `screen` photo.

You can repeat step 2 and 3 on several screen types for the same real photo.
Each one gets its own `screen` value with the same `nnn`.

## 3. Camera settings

- The phone's **default camera app**
- **1x zoom**
- **No portrait mode, no night mode, no filters, no beauty mode**
- Leave HDR and everything else on the phone's default setting

## 4. Transfer photos via Google Drive or USB only

Copy the original files using **Google Drive** (upload the original, not a
"shared" copy) or a **USB cable**.

**Never use WhatsApp**, or any other chat app. It compresses the photo
and strips the EXIF data. The compression removes the fine screen
patterns (moire) we are trying to detect, so a screen photo sent over WhatsApp
looks like a real photo and is useless to us. `ingest.py` rejects photos with
no EXIF or a short side under 1000 px for this reason.

## 5. Include hard real scenes on purpose

Some real scenes have fine repeating patterns that look like moire and can
fool the detector. We need plenty of these as `real` photos:

- brick walls
- fabric (shirts, curtains, knitwear)
- tiles
- fences and grilles
- keyboards

Mix these with ordinary scenes (people, rooms, outdoors, text).

## 6. Check your photos before handing them in

Put the photos in `dataset/raw/` (this folder is not committed to git), then run:

```bash
python dataset/ingest.py dataset/raw
```

This checks every filename, reads the EXIF, rejects photos that look
compressed, writes `dataset/manifest.csv` and prints how many photos each
phone has. Fix or retake anything it lists as a problem.

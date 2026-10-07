# Fieldnote

A private photo-library prototype built with Flask, SQLite and OpenCV. It stores labeled people and reference photos and can compare a one-face query photo against images in the library using OpenCV Zoo's pre-trained SFace model. Face processing runs locally in this app; no face service API is used.

## Run locally

1. Install Python 3.10 or newer.
2. In this folder, create and activate a virtual environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Download the YuNet and SFace model files with `python scripts/download_models.py` (internet is needed once).
5. Set a persistent random `SECRET_KEY` environment variable before running.
6. Run `python run.py`, then open `http://127.0.0.1:5000`.
7. Create a workspace account. Create people records and add reference photos; then use **Compare photos** to rank library images against a query image. The SQLite database and uploads stay under `data/`.

Example PowerShell setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/download_models.py
$env:SECRET_KEY = "replace-this-with-a-long-random-secret"
python run.py
```

## Modules

- `app/auth.py` — registration, sign-in and sign-out. Passwords are stored as Werkzeug password hashes; state-changing forms use a session CSRF token.
- `app/cases.py` — case register, case detail and authenticated photo upload.
- `app/models.py` — SQLite user, case and image records.
- `app/services/face_detection.py` — optional local Haar cascade face-region count.
- `app/services/face_matching.py` — YuNet face detection and SFace embedding comparison against the local photo library, with an AgeDB-30 benchmark cue for broad cross-age search.
- `scripts/download_models.py` — downloads the pretrained ONNX weights into the ignored `models/` folder.
- `templates/` and `static/style.css` — server-rendered pages and responsive UI.

The People page includes an **Open · missing 7+ years** review filter based on the recorded `missing_since` date. It does not change the status or infer that someone has died. Edit older records to enter a date if one is known.

The recognition weights come from OpenCV Zoo: [SFace model documentation and Apache 2.0 license](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface) and [YuNet model documentation and MIT license](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet). The SFace reference implementation uses a cosine-similarity cutoff of 0.363. The app presents this only as a review cue; it is not a probability or a universal threshold.

## Matching limits and deployment

This is a personal photo-library aid, not proof of identity. It ranks uploaded reference images by similarity, returns only results above its comparison cutoff, and lets you choose top K (default 10). If none clear the cutoff, it says no such matches were found and displays current open entries. You may tag saved photos with the subject's age and enter an age for the query photo to show known age gaps or filter by a minimum gap. Cross-age comparison uses the existing pretrained SFace model and an OpenCV AgeDB-30 benchmark threshold as a broad search cue; this is not a dedicated age-progression generator or a threshold calibrated to your photos, and matches can still be missed or false. The app does not synthesize aged portraits. A human must review every candidate. Haar cascade only detects face-like regions and does not perform identity matching.

Keep the library to photos you have permission to process, and run it only on a trusted local network. This prototype is not hardened for internet exposure: registration is open, and it does not yet provide account roles, audit logging, encrypted storage, retention controls, or rate limiting.

## Test cases

`python -m unittest discover -s tests` runs generated vector-based tests for score ordering and the reference threshold without downloading or using anyone's face photos. For a manual end-to-end check, add two reference photos for one person and one for another, compare a held-out photo, and verify that the list ranks candidates only; then try a photo with no face, multiple faces, a poor pose, and an older photo. These examples are functional checks, not accuracy validation.

## Configuration

- `SECRET_KEY` — required for stable, secure sessions. If omitted, a temporary random key is generated and sessions expire when the process restarts.
- Maximum upload size is 8 MB; accepted extensions are JPG, PNG and WebP.

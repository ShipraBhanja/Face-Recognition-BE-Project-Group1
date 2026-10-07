"""Opt-in, local photo comparison using OpenCV Zoo's SFace model."""
from pathlib import Path
from functools import lru_cache

import cv2

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
DETECTOR_FILE = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
RECOGNIZER_FILE = MODEL_DIR / "face_recognition_sface_2021dec.onnx"
COSINE_THRESHOLD = 0.363  # OpenCV Zoo SFace reference threshold; not a probability.
AGE_DB_COSINE_THRESHOLD = 0.277  # OpenCV's AgeDB-30 benchmark threshold; not app-calibrated.


class FaceMatchingError(ValueError):
    pass


@lru_cache(maxsize=1)
def _load_models():
    missing = [p.name for p in (DETECTOR_FILE, RECOGNIZER_FILE) if not p.is_file()]
    if missing:
        raise RuntimeError("Face models are missing. Run: python scripts/download_models.py")
    detector = cv2.FaceDetectorYN.create(str(DETECTOR_FILE), "", (320, 320), 0.85, 0.3, 5000)
    recognizer = cv2.FaceRecognizerSF.create(str(RECOGNIZER_FILE), "")
    return detector, recognizer


def face_feature(image_path):
    image = cv2.imread(str(image_path))
    if image is None:
        raise FaceMatchingError("The image could not be read.")
    detector, recognizer = _load_models()
    detector.setInputSize((image.shape[1], image.shape[0]))
    _, faces = detector.detect(image)
    if faces is None or len(faces) == 0:
        raise FaceMatchingError("No clear face was detected in that image.")
    if len(faces) > 1:
        raise FaceMatchingError("Use a photo with one clearly visible face.")
    aligned = recognizer.alignCrop(image, faces[0])
    return recognizer.feature(aligned)


def cosine_score(recognizer, feature_a, feature_b):
    """Return OpenCV's cosine similarity score (not a calibrated likelihood)."""
    return float(recognizer.match(feature_a, feature_b, cv2.FaceRecognizerSF_FR_COSINE))


def rank_features(query_feature, candidates):
    """Candidates contain (label, image_url, feature); result is score-sorted."""
    _, recognizer = _load_models()
    ranked = [
        {"label": label, "image_url": image_url,
         "score": cosine_score(recognizer, query_feature, feature)}
        for label, image_url, feature in candidates
    ]
    return sorted(ranked, key=lambda item: item["score"], reverse=True)


def looks_like_match(score, threshold=COSINE_THRESHOLD):
    return score >= threshold


def known_age_gap(query_age, reference_age):
    """Return the absolute age difference when both ages are known."""
    if query_age is None or reference_age is None:
        return None
    return abs(query_age - reference_age)


def select_top_matches(ranked, k=10, threshold=COSINE_THRESHOLD):
    """Keep only results above the selected similarity cue, ordered by score."""
    matches = (item for item in ranked if item["score"] >= threshold)
    return sorted(matches, key=lambda item: item["score"], reverse=True)[:k]

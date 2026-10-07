"""Non-identifying face *detection* only. No templates, embeddings or identity matching."""
from pathlib import Path

import cv2


def count_faces(image_path):
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(str(cascade_path))
    if detector.empty():
        raise RuntimeError("OpenCV Haar cascade could not be loaded")
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError("Image could not be read")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    return len(faces)

"""Fetch the small OpenCV Zoo YuNet and SFace model files for local inference."""
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "models"
MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/refs/heads/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        100_000,
    ),
    "face_recognition_sface_2021dec.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/refs/heads/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        1_000_000,
    ),
}


def download(name, url, minimum_size):
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / name
    if target.exists() and target.stat().st_size >= minimum_size:
        print(f"Already present: {target.name}")
        return
    temp = target.with_suffix(target.suffix + ".download")
    request = Request(url, headers={"User-Agent": "Fieldnote-local-photo-matcher"})
    try:
        with urlopen(request, timeout=60) as response, temp.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if temp.stat().st_size < minimum_size:
            raise RuntimeError(f"Downloaded file is unexpectedly small: {name}")
        temp.replace(target)
        print(f"Downloaded: {target.name}")
    finally:
        temp.unlink(missing_ok=True)


if __name__ == "__main__":
    for filename, (source, minimum) in MODELS.items():
        download(filename, source, minimum)

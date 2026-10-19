"""OpenCV clean-up for photographed or scanned invoices.

Steps: decode -> grayscale -> denoise -> deskew -> adaptive threshold -> PNG bytes.
"""
import cv2
import numpy as np


def _decode(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("data is not a decodable image")
    return img


def estimate_skew(gray: np.ndarray) -> float:
    """Return the rotation (degrees, counter-clockwise positive) needed to straighten the text lines.

    Uses the median angle of long line segments found on the text pixels; this is stable for
    text-heavy pages and independent of how OpenCV reports minAreaRect angles.
    """
    inverted = cv2.bitwise_not(gray)
    _, binary = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    # smear characters horizontally so each text line becomes one long blob
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    smeared = cv2.dilate(binary, kernel, iterations=1)
    lines = cv2.HoughLinesP(
        smeared, 1, np.pi / 720, threshold=100,
        minLineLength=max(gray.shape[1] // 4, 50), maxLineGap=10,
    )
    if lines is None:
        return 0.0
    angles = []
    for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4):  # shape differs between OpenCV 4 and 5
        angle = np.degrees(np.arctan2(y1 - y2, x2 - x1))  # image y grows downwards
        if abs(angle) <= 45:
            angles.append(angle)
    return float(np.median(angles)) if angles else 0.0


def _rotate(gray: np.ndarray, angle: float) -> np.ndarray:
    h, w = gray.shape
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), -angle, 1.0)
    return cv2.warpAffine(gray, matrix, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=255)


def preprocess(image_bytes: bytes) -> bytes:
    """Return a cleaned, deskewed, black-and-white PNG of the invoice."""
    gray = cv2.cvtColor(_decode(image_bytes), cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, h=10)
    angle = estimate_skew(gray)
    if abs(angle) > 0.3:
        gray = _rotate(gray, angle)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 15)
    ok, png = cv2.imencode(".png", binary)
    if not ok:
        raise ValueError("could not encode cleaned image")
    return png.tobytes()

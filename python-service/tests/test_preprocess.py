import cv2
import numpy as np
import pytest

from app.preprocess import estimate_skew, preprocess


def _page(angle: float) -> np.ndarray:
    """A white page with ten lines of text, rotated by `angle` degrees."""
    img = np.full((800, 600), 255, np.uint8)
    for i in range(10):
        cv2.putText(img, f"Invoice line number {i} total 1,180.00", (40, 80 + i * 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2, cv2.LINE_AA)
    if angle:
        m = cv2.getRotationMatrix2D((300, 400), angle, 1.0)
        img = cv2.warpAffine(img, m, (600, 800), borderValue=255)
    return img


def _png(img: np.ndarray) -> bytes:
    return cv2.imencode(".png", img)[1].tobytes()


def test_straight_page_has_no_skew():
    assert abs(estimate_skew(_page(0))) < 0.5


@pytest.mark.parametrize("angle", [4.0, -6.0])
def test_skew_is_estimated_with_the_right_magnitude(angle):
    estimated = estimate_skew(_page(angle))
    assert abs(abs(estimated) - abs(angle)) < 1.0


def test_preprocess_straightens_the_page():
    out = cv2.imdecode(np.frombuffer(preprocess(_png(_page(5.0))), np.uint8), cv2.IMREAD_GRAYSCALE)
    assert abs(estimate_skew(out)) < 1.0


def test_preprocess_returns_binary_png():
    out = cv2.imdecode(np.frombuffer(preprocess(_png(_page(0))), np.uint8), cv2.IMREAD_GRAYSCALE)
    assert set(np.unique(out)).issubset({0, 255})


def test_non_image_bytes_are_rejected():
    with pytest.raises(ValueError):
        preprocess(b"not an image")

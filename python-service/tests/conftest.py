import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SAMPLES = Path(__file__).parent / "samples"


def load_samples():
    expected = json.loads((SAMPLES / "expected.json").read_text(encoding="utf-8"))
    return {name: ((SAMPLES / name).read_text(encoding="utf-8"), exp) for name, exp in expected.items()}

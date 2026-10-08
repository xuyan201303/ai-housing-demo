import sys
import os
import json
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def regression_evidence_destination(request, monkeypatch):
    """A new phase can capture regression payloads without overwriting frozen R2."""
    destination = os.getenv('HOUSING_TEST_EVIDENCE_DIR')
    if destination and request.module.__name__ == 'test_knowledge_boundary':
        out = Path(destination).resolve()
        assert out.is_relative_to(Path(__file__).resolve().parents[2] / 'evidence')
        def capture(name, value):
            request.module.clean(value)
            out.mkdir(parents=True, exist_ok=True)
            (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2))
        monkeypatch.setattr(request.module, 'capture', capture)

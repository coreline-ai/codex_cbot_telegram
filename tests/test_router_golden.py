import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "router.py"
GOLDEN_CASES = Path(__file__).parent / "fixtures" / "router_golden_cases.json"


def _run_router(text: str, message_id: str) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(ROUTER),
            "--format",
            "json",
            "--text",
            text,
            "--message-id",
            str(message_id),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout.strip())


with GOLDEN_CASES.open("r", encoding="utf-8") as f:
    CASES = json.load(f)


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_router_payload_matches_golden_snapshot(case):
    payload = _run_router(case["text"], case["message_id"])
    assert payload == case["expected"]


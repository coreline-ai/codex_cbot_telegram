import shutil
import sys
import uuid
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def unique_project_name() -> str:
    return f"pytest_{uuid.uuid4().hex[:10]}"


@pytest.fixture
def cleanup_project():
    created = []

    def _register(project_name: str) -> Path:
        created.append(project_name)
        return ROOT / "web_projects" / project_name

    yield _register

    for project_name in created:
        shutil.rmtree(ROOT / "web_projects" / project_name, ignore_errors=True)


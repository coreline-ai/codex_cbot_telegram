import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _run(cmd, stdin_text=None, timeout=60):
    return subprocess.run(
        cmd,
        input=stdin_text,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def test_image_gen_cli_without_prompt_returns_usage():
    script = ROOT / "skills" / "image_gen" / "image_gen.py"
    result = _run([sys.executable, str(script)], timeout=20)
    combined = f"{result.stdout}\n{result.stderr}"
    assert result.returncode != 0
    assert "Usage: python image_gen.py <prompt>" in combined


def test_web_builder_cli_subprocess_creates_required_files(cleanup_project, unique_project_name):
    script = ROOT / "skills" / "web_gen" / "web_builder.py"
    project_name = unique_project_name
    project_dir = cleanup_project(project_name)

    payload = {
        "project": project_name,
        "mode": "link",
        "html": "<!doctype html><html><head><title>Smoke</title></head><body><h1>Smoke</h1></body></html>",
        "css": "body{margin:0}",
        "assets": [],
    }

    result = _run([sys.executable, str(script)], stdin_text=json.dumps(payload), timeout=40)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert (project_dir / "index.html").exists()
    assert (project_dir / "styles.css").exists()


@pytest.mark.skipif(importlib.util.find_spec("playwright") is None, reason="playwright not installed")
def test_canvas_render_cli_handles_missing_html(tmp_path):
    script = ROOT / "skills" / "image_gen" / "canvas_render.py"
    missing_html = tmp_path / "missing.html"
    output_png = tmp_path / "out.png"

    result = _run(
        [sys.executable, str(script), str(missing_html), str(output_png), "#canvas-container", "0.1"],
        timeout=20,
    )
    combined = f"{result.stdout}\n{result.stderr}".lower()

    assert result.returncode == 1
    assert "not found" in combined


import time
from pathlib import Path

from skills.web_auditor.audit_engine import AuditEngine
from skills.web_gen.web_builder import create_web_package, run_image_gen_subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_required_files_threshold_after_package_build(cleanup_project, unique_project_name):
    project_name = unique_project_name
    project_dir = cleanup_project(project_name)

    html = "<!doctype html><html><head><title>Threshold</title></head><body><h1>Threshold</h1></body></html>"
    css = "body{font-family:sans-serif}"

    create_web_package(project_name=project_name, html_content=html, css_content=css, assets=[], mode="link")

    assert (project_dir / "index.html").exists()
    assert (project_dir / "styles.css").exists()


def test_package_build_exposes_preview_url(cleanup_project, unique_project_name):
    project_name = unique_project_name
    project_dir = cleanup_project(project_name)
    html = "<!doctype html><html><head><title>Preview</title></head><body><h1>Preview</h1></body></html>"
    css = "body{font-family:sans-serif}"

    result = create_web_package(project_name=project_name, html_content=html, css_content=css, assets=[], mode="link")

    assert isinstance(result, dict)
    assert "preview_url" in result
    assert result["preview_url"].endswith(f"/web_projects/{project_name}/index.html")
    assert (project_dir / "deploy_info.json").exists()


def test_audit_score_threshold_for_valid_page(tmp_path):
    project_dir = tmp_path / "audit_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "index.html").write_text(
        "<!doctype html><html><head><title>Audit</title></head><body><h1>Audit</h1></body></html>",
        encoding="utf-8",
    )

    report = AuditEngine().audit_project(str(project_dir))
    assert report["score"] >= 95
    assert "Fatal" not in " ".join(report.get("issues", []))


def test_subprocess_timeout_threshold_for_image_gen_adapter(tmp_path):
    slow_script = tmp_path / "slow_image_gen.py"
    slow_script.write_text(
        "import time\n"
        "time.sleep(2)\n"
        "print({'ok': True, 'image_path': 'unused.png'})\n",
        encoding="utf-8",
    )

    output_png = tmp_path / "out.png"
    started = time.monotonic()
    ok = run_image_gen_subprocess(
        prompt="timeout test",
        output_path=str(output_png),
        image_gen_script=str(slow_script),
        timeout_sec=0.1,
    )
    elapsed = time.monotonic() - started

    assert ok is False
    assert elapsed < 1.5

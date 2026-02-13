#!/usr/bin/env python3
"""
Run one strict photoreal smoke test for the web pipeline.

Scope (intentionally narrow):
- Run web_master orchestrator with codex_cli + strict realism enabled.
- Verify required asset files exist on success.
- Classify common failure cause (policy/read-only) for fast diagnosis.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "skills" / "web_master" / "master_orchestrator.py"
TEST_RUNS = ROOT / "test_runs"


def _now_tag() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _classify_failure(combined_log: str, returncode: int) -> str:
    text = (combined_log or "").lower()
    if "sandbox: read-only" in text or "blocked by policy" in text:
        return "FAIL_POLICY_READ_ONLY"
    if "photorealistic asset generation failed in strict mode" in text:
        return "FAIL_STRICT_REALISM"
    if returncode == 124:
        return "FAIL_TIMEOUT"
    return "FAIL_EXEC"


def main() -> int:
    parser = argparse.ArgumentParser(description="Strict photoreal smoke runner")
    parser.add_argument("--project", default=f"live-test-shoppingmall-real-{_now_tag()}")
    parser.add_argument("--brief", default="쇼핑몰 랜더링 페이지 만들어줘")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--min-bytes", type=int, default=1024)
    args = parser.parse_args()

    TEST_RUNS.mkdir(parents=True, exist_ok=True)

    stamp = _now_tag()
    log_path = TEST_RUNS / f"realism_smoke_{stamp}.log"
    report_path = TEST_RUNS / f"realism_smoke_{stamp}.json"

    env = os.environ.copy()
    env["IMAGE_GEN_PROVIDER"] = "codex_cli"
    env["STRICT_REALISTIC_ASSETS"] = "1"
    env.setdefault("CODEX_IMAGE_TIMEOUT", "300")

    cmd = [
        sys.executable,
        str(ORCHESTRATOR),
        "--project",
        args.project,
        "--brief",
        args.brief,
    ]

    started = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.timeout,
        )
        rc = result.returncode
        stdout = result.stdout or ""
        stderr = result.stderr or ""
    except subprocess.TimeoutExpired as exc:
        rc = 124
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""

    elapsed = round(time.time() - started, 2)
    combined = (stdout + "\n" + stderr).strip()
    log_path.write_text(combined, encoding="utf-8", errors="replace")

    project_dir = ROOT / "web_projects" / args.project
    hero = project_dir / "assets" / "hero_bg.png"
    product = project_dir / "assets" / "product_feature.png"

    hero_ok = hero.exists() and hero.stat().st_size >= args.min_bytes
    product_ok = product.exists() and product.stat().st_size >= args.min_bytes

    status = "PASS" if (rc == 0 and hero_ok and product_ok) else _classify_failure(combined, rc)

    report = {
        "status": status,
        "returncode": rc,
        "elapsed_sec": elapsed,
        "project": args.project,
        "brief": args.brief,
        "env": {
            "IMAGE_GEN_PROVIDER": env.get("IMAGE_GEN_PROVIDER"),
            "STRICT_REALISTIC_ASSETS": env.get("STRICT_REALISTIC_ASSETS"),
            "CODEX_IMAGE_TIMEOUT": env.get("CODEX_IMAGE_TIMEOUT"),
        },
        "paths": {
            "project_dir": str(project_dir),
            "hero_bg": str(hero),
            "product_feature": str(product),
            "log": str(log_path),
            "report": str(report_path),
        },
        "checks": {
            "hero_ok": hero_ok,
            "product_ok": product_ok,
            "min_bytes": args.min_bytes,
        },
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"STATUS: {status}")
    print(f"RETURNCODE: {rc}")
    print(f"ELAPSED_SEC: {elapsed}")
    print(f"LOG: {log_path}")
    print(f"REPORT: {report_path}")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

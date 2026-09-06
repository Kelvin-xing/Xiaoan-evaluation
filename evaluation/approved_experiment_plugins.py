"""Approved local executors for controlled XiaoAn experiments."""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import time
from typing import Any, Mapping
from urllib.request import urlopen
import uuid

from xiaoan_eval.file_experiment import apply_capsule_ground_proposal, snapshot_workspace


REPO_ROOT = Path(__file__).resolve().parent.parent
EVALUATION_ROOT = Path(__file__).resolve().parent
PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
TARGET_ENV = {
    "router.context_turns": "XIAOAN_ROUTER_CONTEXT_TURNS",
    "state.active_capsule_ttl": "XIAOAN_ACTIVE_CAPSULE_TTL",
    "state.activation_confidence": "XIAOAN_ACTIVATION_CONFIDENCE",
    "model.reasoning_effort": "XIAOAN_MODEL_REASONING_EFFORT",
    "response.verbosity": "XIAOAN_RESPONSE_VERBOSITY",
}


def run_variant(request: Mapping[str, Any]) -> Mapping[str, Any]:
    """Start an isolated local Chatflow process and evaluate one parameter variant."""
    target = str(request.get("target", ""))
    if target not in TARGET_ENV:
        raise ValueError(f"unsupported local automatic target: {target}")
    seed = int(request["seed"])
    candidate = request["candidate"]
    case_ids = request.get("baseline_case_ids", ())
    if not isinstance(case_ids, list) or not case_ids:
        raise ValueError("baseline_case_ids must be a non-empty array")

    artifact_root = Path(os.getenv("XIAOAN_EXPERIMENT_ARTIFACT_ROOT", EVALUATION_ROOT / "runs" / "auto-variants"))
    run_dir = artifact_root / f"{target.replace('.', '-')}-{seed}-{uuid.uuid4().hex[:8]}"
    cases_dir = run_dir / "input-cases"
    cases_dir.mkdir(parents=True)
    for case_id in case_ids:
        source = EVALUATION_ROOT / "test-cases" / f"{case_id}.yaml"
        if not source.exists():
            raise ValueError(f"canonical case is missing: {case_id}")
        (cases_dir / source.name).write_bytes(source.read_bytes())

    manifest = json.loads(json.dumps(request["baseline_manifest"]))
    manifest["seed"] = seed
    manifest["run_started_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    manifest["hyperparameters"][target] = candidate
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    port = _available_port()
    env = dict(os.environ)
    env.update({
        "XIAOAN_ENABLE_DEBUG": "true", "XIAOAN_COOKIE_SECURE": "false", "XIAOAN_OFFLINE": "false",
        TARGET_ENV[target]: str(candidate), "XIAOAN_JUDGE_TIMEOUT_SECONDS": env.get("XIAOAN_JUDGE_TIMEOUT_SECONDS", "600"),
        "XIAOAN_JUDGE_MAX_RETRIES": env.get("XIAOAN_JUDGE_MAX_RETRIES", "0"),
    })
    if env.get("XIAOAN_OPENAI_BASE_URL") and not env.get("OPENAI_BASE_URL"):
        env["OPENAI_BASE_URL"] = env["XIAOAN_OPENAI_BASE_URL"]
    log_path = run_dir / "server.log"
    with log_path.open("wb") as log:
        server = subprocess.Popen([
            str(PYTHON), "-m", "uvicorn", "--app-dir", str(REPO_ROOT / "tech/chatflow/poc"),
            "server:app", "--host", "127.0.0.1", "--port", str(port),
        ], env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            _wait_ready(f"http://127.0.0.1:{port}/health/ready", server)
            output = run_dir / "result"
            command = [
                str(PYTHON), "-m", "xiaoan_eval", "run", str(cases_dir),
                "--base-url", f"http://127.0.0.1:{port}",
                "--judge-plugin", "company_eval_plugins:judge",
                "--secondary-judge-plugin", "company_eval_plugins:second_judge",
                "--context-provider", "company_eval_plugins:authoritative_context",
                "--manifest", str(manifest_path), "--rating-rule", str(EVALUATION_ROOT / "ratings rule.yml"),
                "--config", str(EVALUATION_ROOT / "evaluator-config.yml"), "--output", str(output),
                "--release-review",
            ]
            completed = subprocess.run(command, cwd=EVALUATION_ROOT, env={**env, "PYTHONPATH": "."}, timeout=3600)
            if completed.returncode not in {0, 1}:
                raise RuntimeError(f"variant evaluation exited with {completed.returncode}")
            records = [json.loads(line) for line in (output / "4.2-case-results.jsonl").read_text().splitlines()]
            generated_manifest = json.loads((output / "8.1-manifest.json").read_text())
            return {"records": records, "manifest": generated_manifest, "artifact_dir": str(output)}
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


def run_capsule_ground_variant(request: Mapping[str, Any]) -> Mapping[str, Any]:
    """Compare baseline and one allowlisted capsule ground edit from the same snapshot."""
    seed = int(request["seed"])
    proposal = request.get("proposal")
    recommendation = request.get("recommendation", {})
    if not isinstance(proposal, Mapping) or not isinstance(recommendation, Mapping):
        raise ValueError("file experiment requires proposal and recommendation objects")
    case_ids = recommendation.get("affected_cases", ())
    if not isinstance(case_ids, list) or not case_ids:
        raise ValueError("file recommendation affected_cases must be a non-empty array")
    artifact_root = Path(os.getenv("XIAOAN_EXPERIMENT_ARTIFACT_ROOT", EVALUATION_ROOT / "runs" / "auto-file-variants"))
    run_root = artifact_root / f"capsule-ground-{seed}-{uuid.uuid4().hex[:8]}"
    baseline_root = run_root / "baseline-snapshot"
    variant_root = run_root / "variant-snapshot"
    snapshot_workspace(REPO_ROOT, baseline_root)
    snapshot_workspace(REPO_ROOT, variant_root)
    change = apply_capsule_ground_proposal(variant_root, proposal)
    (run_root / "proposal.json").write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n")
    (run_root / "change.json").write_text(json.dumps(change, ensure_ascii=False, indent=2) + "\n")
    baseline = _evaluate_snapshot(baseline_root, run_root / "baseline-result", case_ids, seed)
    variant = _evaluate_snapshot(variant_root, run_root / "variant-result", case_ids, seed)
    return {
        "baseline_records": baseline["records"], "records": variant["records"],
        "baseline_artifact_dir": baseline["artifact_dir"], "artifact_dir": variant["artifact_dir"],
        "change": change,
    }


def _evaluate_snapshot(snapshot: Path, output: Path, case_ids: list[str], seed: int) -> Mapping[str, Any]:
    evaluation_root = snapshot / "evaluation"
    cases_dir = output.parent / f"{output.name}-cases"
    cases_dir.mkdir(parents=True)
    for case_id in case_ids:
        source = evaluation_root / "test-cases" / f"{case_id}.yaml"
        if not source.exists():
            raise ValueError(f"canonical case is missing in snapshot: {case_id}")
        (cases_dir / source.name).write_bytes(source.read_bytes())
    manifest = json.loads((evaluation_root / "manifest.json").read_text())
    manifest["seed"] = seed
    manifest["run_started_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    manifest["rating_rule_schema_version"] = "1.1"
    manifest_path = output.parent / f"{output.name}-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    port = _available_port()
    env = dict(os.environ)
    env.update({
        "XIAOAN_ENABLE_DEBUG": "true", "XIAOAN_COOKIE_SECURE": "false", "XIAOAN_OFFLINE": "false",
        "XIAOAN_JUDGE_TIMEOUT_SECONDS": env.get("XIAOAN_JUDGE_TIMEOUT_SECONDS", "600"),
        "XIAOAN_JUDGE_MAX_RETRIES": env.get("XIAOAN_JUDGE_MAX_RETRIES", "0"),
        "XIAOAN_CONFIG_PATH": str(output.parent / f"{output.name}-config.json"),
    })
    if env.get("XIAOAN_OPENAI_BASE_URL") and not env.get("OPENAI_BASE_URL"):
        env["OPENAI_BASE_URL"] = env["XIAOAN_OPENAI_BASE_URL"]
    log_path = output.parent / f"{output.name}-server.log"
    with log_path.open("wb") as log:
        server = subprocess.Popen([
            str(PYTHON), "-m", "uvicorn", "--app-dir", str(snapshot / "tech/chatflow/poc"),
            "server:app", "--host", "127.0.0.1", "--port", str(port),
        ], env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            _wait_ready(f"http://127.0.0.1:{port}/health/ready", server)
            completed = subprocess.run([
                str(PYTHON), "-m", "xiaoan_eval", "run", str(cases_dir),
                "--base-url", f"http://127.0.0.1:{port}",
                "--judge-plugin", "company_eval_plugins:judge",
                "--secondary-judge-plugin", "company_eval_plugins:second_judge",
                "--context-provider", "company_eval_plugins:authoritative_context",
                "--manifest", str(manifest_path), "--rating-rule", str(evaluation_root / "ratings rule.yml"),
                "--config", str(evaluation_root / "evaluator-config.yml"), "--output", str(output), "--release-review",
            ], cwd=evaluation_root, env={**env, "PYTHONPATH": "."}, timeout=3600)
            if completed.returncode not in {0, 1}:
                raise RuntimeError(f"snapshot evaluation exited with {completed.returncode}")
            records = [json.loads(line) for line in (output / "4.2-case-results.jsonl").read_text().splitlines()]
            return {"records": records, "artifact_dir": str(output)}
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


def _available_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_ready(url: str, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("local variant server exited before readiness")
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError("local variant server did not become ready within 30 seconds")

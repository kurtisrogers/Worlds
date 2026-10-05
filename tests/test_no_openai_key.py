"""CI must reject a committed OpenAI-style key and must not call the live API.

The fixture key is assembled in memory and written to a temporary file.
It is not stored in the repository: a committed key has to fail the gate.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "no_openai_key.py"
CI = ROOT / ".github" / "workflows" / "ci.yml"
PRE_COMMIT = ROOT / ".pre-commit-config.yaml"
MAKEFILE = ROOT / "Makefile"

# Shapes the gate must reject. Split so this file is not itself a key.
PROJECT_KEY = "sk-" + "proj-" + ("aB3x" * 16)
LEGACY_KEY = "sk-" + ("Ab" * 20) + "T3BlbkFJ" + ("Cd" * 20)


def _run(args, cwd=None):
    assert SCRIPT.is_file(), "scripts/no_openai_key.py is missing"
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _workflow_env(text):
    lines = []
    in_env = False
    for line in text.splitlines():
        if line.startswith("jobs:"):
            break
        if line.startswith("env:"):
            in_env = True
            lines.append(line)
            continue
        if in_env:
            if line and not line.startswith((" ", "#")):
                in_env = False
                continue
            lines.append(line)
    return "\n".join(lines)


def _jobs(text):
    """Map each job name to its body. Job keys sit at two-space indent."""
    lines = text.splitlines()
    try:
        start = lines.index("jobs:") + 1
    except ValueError:
        return {}
    jobs = {}
    name = None
    body = []
    for line in lines[start:]:
        if line and not line.startswith((" ", "#")):
            break
        if (
            line.startswith("  ")
            and not line.startswith("   ")
            and line.rstrip().endswith(":")
        ):
            if name is not None:
                jobs[name] = "\n".join(body)
            name = line.strip()[:-1]
            body = [line]
            continue
        if name is not None:
            body.append(line)
    if name is not None:
        jobs[name] = "\n".join(body)
    return jobs


def _assert_job_has_no_live_openai(name, body):
    assert not re.search(r"OPENAI_API_KEY\s*[:=]", body), name
    assert "api.openai.com" not in body, name
    assert "openai.com" not in body, name
    for value in re.findall(r"AI_ASSIST_ENABLED:\s*(\S+)", body):
        assert value.strip("\"'") in {"false", "False", "0"}, name


def test_project_and_legacy_fixtures_fail_the_gate(tmp_path):
    leaked = tmp_path / "committed.env"
    leaked.write_text(f"OPENAI_API_KEY={PROJECT_KEY}\n")
    project = _run(["--root", str(tmp_path)])
    assert project.returncode != 0
    assert "committed.env" in project.stderr
    assert PROJECT_KEY not in project.stdout
    assert PROJECT_KEY not in project.stderr

    leaked.write_text(f"OPENAI_API_KEY={LEGACY_KEY}\n")
    legacy = _run(["--root", str(tmp_path)])
    assert legacy.returncode != 0
    assert LEGACY_KEY not in legacy.stderr


def test_a_commit_that_contains_a_key_fails(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "gate@example.com"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Gate"],
        cwd=tmp_path,
        check=True,
    )
    leaked = tmp_path / "secret.env"
    leaked.write_text(f"OPENAI_API_KEY={PROJECT_KEY}\n")
    before_commit = _run(["--root", str(tmp_path)])
    assert before_commit.returncode == 0, before_commit.stderr

    subprocess.run(["git", "add", "secret.env"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "add a key"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    committed = _run(["--root", str(tmp_path)])
    assert committed.returncode != 0
    assert "secret.env" in committed.stderr
    assert PROJECT_KEY not in committed.stderr


def test_admin_and_service_account_shapes_fail(tmp_path):
    admin = "sk-" + "admin-" + ("qR9s" * 10)
    service = "sk-" + "svcacct-" + ("mN4p" * 10)
    (tmp_path / "admin.txt").write_text(admin + "\n")
    (tmp_path / "service.txt").write_text(service + "\n")
    result = _run(["--root", str(tmp_path)])
    assert result.returncode != 0
    assert "admin.txt" in result.stderr
    assert "service.txt" in result.stderr
    assert admin not in result.stderr
    assert service not in result.stderr


def test_short_test_double_and_stripe_shape_pass(tmp_path):
    sample = tmp_path / "harmless.txt"
    sample.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=",
                "STRIPE_SECRET_KEY=sk_test_" + ("a" * 40),
                'SECRET = "sk-test-not-a-real-key"',
                "https://api.openai.com/v1/chat/completions",
            ]
        )
        + "\n"
    )
    result = _run(["--root", str(tmp_path)])
    assert result.returncode == 0, result.stderr


def test_tracked_repository_passes():
    result = _run([])
    assert result.returncode == 0, result.stderr


def test_self_test_rejects_a_temporary_key_shaped_string():
    result = _run(["--self-test"])
    assert result.returncode == 0, result.stderr + result.stdout
    assert "rejected" in result.stdout.lower()
    assert PROJECT_KEY not in result.stdout
    assert LEGACY_KEY not in result.stdout


def test_workflow_does_not_set_a_key_or_call_openai():
    text = CI.read_text()
    assert not re.search(r"OPENAI_API_KEY\s*[:=]", text)
    assert "api.openai.com" not in text
    assert "openai.com" not in text


def test_workflow_keeps_the_assist_flag_off_for_every_job():
    text = CI.read_text()
    env = _workflow_env(text)
    assert re.search(r'AI_ASSIST_ENABLED:\s*"false"', env)
    jobs = _jobs(text)
    assert "test" in jobs
    for name, body in jobs.items():
        _assert_job_has_no_live_openai(name, body)


def test_key_gate_covers_the_test_job_and_review_e2e_when_present():
    """The scan is its own required job, and workflow env covers every job.

    ``review-e2e`` (``make test-review-e2e``, #27) is not on main yet.
    When that job is added to this workflow it inherits ``AI_ASSIST_ENABLED``
    and is checked here. The gate job scans the same commit either way.
    """
    text = CI.read_text()
    jobs = _jobs(text)
    assert "openai-key-gate" in jobs
    gate = jobs["openai-key-gate"]
    assert "continue-on-error" not in gate
    assert "check-openai-key" in gate
    _assert_job_has_no_live_openai("openai-key-gate", gate)

    test_job = jobs["test"]
    assert "pytest" in test_job
    assert "behave" in test_job
    _assert_job_has_no_live_openai("test", test_job)

    review = jobs.get("review-e2e")
    if review is not None:
        assert "test-review-e2e" in review
        _assert_job_has_no_live_openai("review-e2e", review)
        assert "OPENAI_API_KEY" not in review


def _make_recipe(name):
    match = re.search(
        rf"^{re.escape(name)}:[^\n]*\n((?:\t.*\n)+)",
        MAKEFILE.read_text(),
        re.M,
    )
    assert match, name
    return match.group(1)


def test_pre_commit_and_make_test_run_the_gate():
    pre_commit = PRE_COMMIT.read_text()
    assert "id: no-openai-key" in pre_commit
    assert "scripts/no_openai_key.py" in pre_commit
    recipe = _make_recipe("check-openai-key")
    assert "scripts/no_openai_key.py" in recipe
    assert "--self-test" in recipe
    assert "check-openai-key" in _make_recipe("test")

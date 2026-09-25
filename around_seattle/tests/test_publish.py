import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "publish.sh"
GIT_ENV = {"GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.org", "GIT_COMMITTER_NAME": "Test",
           "GIT_COMMITTER_EMAIL": "test@example.org", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def run(args, cwd, env, check=True):
    return subprocess.run(args, cwd=cwd, env=env, check=check, capture_output=True, text=True)


@pytest.fixture
def repos(tmp_path):
    env = {**os.environ, **GIT_ENV}
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    run(["git", "init", "--bare", "-b", "main", str(origin)], tmp_path, env)
    run(["git", "clone", str(origin), str(work)], tmp_path, env)
    (work / "README.md").write_text("main branch\n", encoding="utf-8")
    run(["git", "add", "README.md"], work, env)
    run(["git", "commit", "-m", "init"], work, env)
    run(["git", "push", "origin", "HEAD:main"], work, env)
    return origin, work, env


def git_origin(origin, env, *args):
    return run(["git", "--git-dir", str(origin), *args], origin, env).stdout


def publish(work, env, data):
    return run(["bash", str(SCRIPT), str(data)], work, env)


def test_first_publish_creates_orphan_branch_and_leaves_main_alone(repos, tmp_path):
    origin, work, env = repos
    data = tmp_path / "data.json"
    data.write_text('{"v": 1}', encoding="utf-8")
    assert "published to around-seattle-data" in publish(work, env, data).stdout
    assert git_origin(origin, env, "show", "around-seattle-data:around-seattle.json") == '{"v": 1}'
    assert sorted(git_origin(origin, env, "ls-tree", "--name-only", "around-seattle-data").split()) == [
        "README.md", "around-seattle.json"]
    assert "Generated data" in git_origin(origin, env, "show", "around-seattle-data:README.md")
    assert len(git_origin(origin, env, "log", "--format=%s", "around-seattle-data").splitlines()) == 1
    assert git_origin(origin, env, "log", "--format=%s", "main").splitlines() == ["init"]


def test_unchanged_data_is_a_no_op(repos, tmp_path):
    origin, work, env = repos
    data = tmp_path / "data.json"
    data.write_text('{"v": 1}', encoding="utf-8")
    publish(work, env, data)
    assert "no changes to publish" in publish(work, env, data).stdout
    assert len(git_origin(origin, env, "log", "--format=%s", "around-seattle-data").splitlines()) == 1


def test_changed_data_adds_one_commit(repos, tmp_path):
    origin, work, env = repos
    data = tmp_path / "data.json"
    data.write_text('{"v": 1}', encoding="utf-8")
    publish(work, env, data)
    data.write_text('{"v": 2}', encoding="utf-8")
    publish(work, env, data)
    assert git_origin(origin, env, "show", "around-seattle-data:around-seattle.json") == '{"v": 2}'
    assert len(git_origin(origin, env, "log", "--format=%s", "around-seattle-data").splitlines()) == 2


def test_missing_input_fails(repos, tmp_path):
    _, work, env = repos
    result = run(["bash", str(SCRIPT), str(tmp_path / "missing.json")], work, env, check=False)
    assert result.returncode != 0
    assert "missing or empty" in result.stderr

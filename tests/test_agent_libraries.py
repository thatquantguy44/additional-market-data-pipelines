import hashlib
import json
import shutil
import subprocess

import pytest

from scripts.verify_quantsmith import verify


def git(root, *args):
    return subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            *args,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
def library(tmp_path):
    root = tmp_path / "QuantSmith library"
    root.mkdir()
    guidance = root / "README.md"
    guidance.write_text("Fixture guidance, not QuantSmith content.\n")
    git(root, "init", "--quiet")
    git(root, "add", "README.md")
    git(root, "commit", "--quiet", "-m", "fixture")
    reference = tmp_path / "reference.json"
    reference.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "QuantSmith",
                "mode": "local_reference",
                "default_path": str(root),
                "path_env": "TEST_QUANTSMITH_PATH",
                "revision": git(root, "rev-parse", "HEAD"),
                "git_tree": git(root, "rev-parse", "HEAD^{tree}"),
                "guidance_sha256": {"README.md": hashlib.sha256(guidance.read_bytes()).hexdigest()},
            }
        )
    )
    return root, reference


def test_reference_resolves_default_environment_and_explicit_path(library, monkeypatch, tmp_path):
    root, reference = library
    monkeypatch.delenv("TEST_QUANTSMITH_PATH", raising=False)
    assert verify(reference)["path"] == str(root)
    relocated = tmp_path / "relocated library"
    shutil.copytree(root, relocated)
    monkeypatch.setenv("TEST_QUANTSMITH_PATH", str(relocated))
    assert verify(reference)["path"] == str(relocated)
    assert verify(reference, root)["path"] == str(root)
    monkeypatch.setenv("TEST_QUANTSMITH_PATH", str(tmp_path / "absent"))
    with pytest.raises(ValueError, match="unavailable"):
        verify(reference)


def test_guidance_edit_fails_even_when_git_head_matches(library):
    root, reference = library
    (root / "README.md").write_text("Changed guidance\n")
    with pytest.raises(ValueError, match="guidance differs from pin"):
        verify(reference)


def test_new_commit_requires_deliberate_reference_update(library):
    root, reference = library
    (root / "other.md").write_text("New unrelated committed work\n")
    git(root, "add", "other.md")
    git(root, "commit", "--quiet", "-m", "advance head")
    with pytest.raises(ValueError, match="revision/tree differs"):
        verify(reference)


def test_unrelated_local_changes_are_reported_without_modifying_checkout(library):
    root, reference = library
    assert verify(reference)["other_worktree_changes"] is False
    (root / "work-in-progress.md").write_text("Preserve this draft\n")
    before = git(root, "status", "--porcelain=v1")
    assert verify(reference)["other_worktree_changes"] is True
    assert git(root, "status", "--porcelain=v1") == before


def test_reference_rejects_subdirectory_and_escaping_guidance(library):
    root, reference = library
    nested = root / "nested"
    nested.mkdir()
    with pytest.raises(ValueError, match="checkout root"):
        verify(reference, nested)
    config = json.loads(reference.read_text())
    config["guidance_sha256"] = {"../outside.md": "0" * 64}
    reference.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="inventory entry"):
        verify(reference)

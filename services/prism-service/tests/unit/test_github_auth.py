"""Unit tests for app.services.github_auth.

Covers: write/read round-trip, atomic replace preserves other-host
lines, fingerprint never exposes the full token, clear_token removes
only the github.com line, and git_credential_helper_args() returns an
empty list when no creds file exists so existing tests against local
bare repos keep working.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app import config


@pytest.fixture
def isolated_data_dir(tmp_path: Path, monkeypatch):
    """Point app.config.DATA_DIR (and the github_auth CREDS_PATH derived
    from it) at a tmp dir, then reimport the module so the constant
    re-resolves. Returns the tmp data dir."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    # github_auth captures DATA_DIR at import time, so re-import in
    # this test process before the test body runs.
    import importlib
    from app.services import github_auth as gh_mod
    importlib.reload(gh_mod)
    yield tmp_path
    importlib.reload(gh_mod)  # restore for subsequent test files


def test_no_creds_file_means_not_authenticated(isolated_data_dir):
    from app.services import github_auth as gh
    assert gh.is_authenticated() is False
    assert gh.token_fingerprint() == ""
    assert gh.git_credential_helper_args() == []


def test_set_token_round_trip_and_fingerprint(isolated_data_dir):
    from app.services import github_auth as gh
    gh.set_token("ghp_supersecret_abcd1234", user="alice")
    assert gh.is_authenticated() is True
    fp = gh.token_fingerprint()
    assert fp.startswith("alice:")
    assert "•••" in fp
    assert "1234" in fp  # last 4 visible
    # Crucially: the body of the fingerprint never contains the full token.
    assert "supersecret" not in fp
    assert "abcd" not in fp.replace("1234", "")


def test_set_token_strips_default_user(isolated_data_dir):
    from app.services import github_auth as gh
    gh.set_token("ghp_x", user="")
    body = (isolated_data_dir / ".git-credentials").read_text()
    assert "x-access-token:ghp_x@github.com" in body


def test_set_token_replaces_prior_github_line(isolated_data_dir):
    from app.services import github_auth as gh
    gh.set_token("ghp_one", user="alice")
    gh.set_token("ghp_two", user="bob")
    body = (isolated_data_dir / ".git-credentials").read_text()
    assert "ghp_one" not in body
    assert "ghp_two" in body
    # Exactly one github.com line.
    assert body.count("@github.com") == 1


def test_set_token_preserves_other_host_lines(isolated_data_dir):
    from app.services import github_auth as gh
    creds = isolated_data_dir / ".git-credentials"
    creds.write_text("https://user:tok@gitlab.example.com\n", encoding="utf-8")
    gh.set_token("ghp_one")
    body = creds.read_text(encoding="utf-8")
    assert "gitlab.example.com" in body
    assert "github.com" in body


def test_clear_token_removes_github_line(isolated_data_dir):
    from app.services import github_auth as gh
    creds = isolated_data_dir / ".git-credentials"
    gh.set_token("ghp_one", user="alice")
    assert gh.clear_token() is True
    assert gh.is_authenticated() is False
    # File is removed when no other lines remain.
    assert not creds.exists()


def test_clear_token_keeps_other_hosts(isolated_data_dir):
    from app.services import github_auth as gh
    creds = isolated_data_dir / ".git-credentials"
    creds.write_text("https://user:tok@gitlab.example.com\n", encoding="utf-8")
    gh.set_token("ghp_one")
    assert gh.clear_token() is True
    body = creds.read_text(encoding="utf-8")
    assert "gitlab" in body
    assert "github.com" not in body


def test_helper_args_when_authenticated(isolated_data_dir):
    from app.services import github_auth as gh
    gh.set_token("ghp_one")
    args = gh.git_credential_helper_args()
    assert args[0] == "-c"
    assert args[1].startswith("credential.helper=store --file=")
    assert str(gh.credentials_path()) in args[1]


def test_empty_token_rejected(isolated_data_dir):
    from app.services import github_auth as gh
    with pytest.raises(ValueError):
        gh.set_token("   ")

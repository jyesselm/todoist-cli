"""ConfigManager token precedence and save behaviour."""

import json
from pathlib import Path

import pytest
import yaml

from todoist_cli import config as config_mod
from todoist_cli.config import ConfigManager


@pytest.fixture
def shared(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "shared.json"
    monkeypatch.setattr(config_mod, "SHARED_TOKEN_FILE", path)
    monkeypatch.delenv("TODOIST_API_TOKEN", raising=False)
    return path


@pytest.fixture
def cfg_path(tmp_path: Path) -> Path:
    path = tmp_path / "config.yml"
    path.write_text(yaml.dump({"api-token": "from-yaml", "shortcuts": {"labels": {"q": "quick"}}}))
    return path


def test_env_beats_shared_and_yaml(
    shared: Path, cfg_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shared.write_text(json.dumps({"token": "from-shared"}))
    monkeypatch.setenv("TODOIST_API_TOKEN", "from-env")
    assert ConfigManager(cfg_path).get_api_token() == "from-env"


def test_shared_beats_yaml(shared: Path, cfg_path: Path) -> None:
    shared.write_text(json.dumps({"token": "from-shared"}))
    assert ConfigManager(cfg_path).get_api_token() == "from-shared"


def test_yaml_fallback(shared: Path, cfg_path: Path) -> None:
    assert ConfigManager(cfg_path).get_api_token() == "from-yaml"


def test_save_omits_shared_token(shared: Path, cfg_path: Path) -> None:
    shared.write_text(json.dumps({"token": "from-shared"}))
    mgr = ConfigManager(cfg_path)
    mgr.add_shortcut("labels", "w", "waiting")
    saved = yaml.safe_load(cfg_path.read_text())
    assert "api-token" not in saved
    assert saved["shortcuts"]["labels"] == {"q": "quick", "w": "waiting"}


def test_save_omits_env_token(
    shared: Path, cfg_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TODOIST_API_TOKEN", "from-env")
    mgr = ConfigManager(cfg_path)
    mgr.add_shortcut("projects", "i", "Inbox")
    assert "api-token" not in yaml.safe_load(cfg_path.read_text())


def test_save_keeps_yaml_token(shared: Path, cfg_path: Path) -> None:
    mgr = ConfigManager(cfg_path)
    mgr.add_shortcut("priorities", "u", "p1")
    assert yaml.safe_load(cfg_path.read_text())["api-token"] == "from-yaml"


def test_token_only_without_file(shared: Path, tmp_path: Path) -> None:
    shared.write_text(json.dumps({"token": "tok"}))
    assert ConfigManager(tmp_path / "missing.yml").load().api_token == "tok"


def test_missing_everything_raises(shared: Path, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ConfigManager(tmp_path / "missing.yml").load()


def test_missing_token_in_file_raises(shared: Path, tmp_path: Path) -> None:
    path = tmp_path / "c.yml"
    path.write_text("shortcuts: {}\n")
    with pytest.raises(ValueError):
        ConfigManager(path).load()


def test_unknown_shortcut_type(shared: Path, cfg_path: Path) -> None:
    with pytest.raises(ValueError):
        ConfigManager(cfg_path).add_shortcut("bogus", "a", "b")

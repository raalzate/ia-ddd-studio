"""Unit tests for src/ui/utils/storage.py — file-based persistence helpers."""

import os


def test_save_and_load_static_json(tmp_path, monkeypatch):
    from ui.utils import storage

    monkeypatch.setattr(storage, "STATIC_DIR", str(tmp_path))
    monkeypatch.setattr(storage, "STATIC_JSON_PATH", str(tmp_path / "domain_analysis.json"))

    data = {"nombre_proyecto": "Test", "version": "1.0"}
    storage.save_static_json(data)

    loaded = storage.load_static_json()
    assert loaded == data


def test_load_static_json_returns_empty_when_missing(tmp_path, monkeypatch):
    from ui.utils import storage

    monkeypatch.setattr(storage, "STATIC_JSON_PATH", str(tmp_path / "nonexistent.json"))

    assert storage.load_static_json() == {}


def test_load_static_json_returns_empty_on_corrupt_file(tmp_path, monkeypatch):
    from ui.utils import storage

    corrupt = tmp_path / "bad.json"
    corrupt.write_text("not json {{{")
    monkeypatch.setattr(storage, "STATIC_JSON_PATH", str(corrupt))

    assert storage.load_static_json() == {}


def test_save_and_load_llm_config(tmp_path, monkeypatch):
    from ui.utils import storage

    monkeypatch.setattr(storage, "STATIC_DIR", str(tmp_path))
    monkeypatch.setattr(storage, "LLM_CONFIG_PATH", str(tmp_path / "llm_config.json"))

    config = {"model_name": "gemini-2.5-flash", "api_key": "test-key", "temperature": 0.1}
    storage.save_llm_config(config)

    loaded = storage.load_llm_config()
    assert loaded == config


def test_load_llm_config_returns_none_when_missing(tmp_path, monkeypatch):
    from ui.utils import storage

    monkeypatch.setattr(storage, "LLM_CONFIG_PATH", str(tmp_path / "nonexistent.json"))

    assert storage.load_llm_config() is None


def test_load_llm_config_returns_none_on_corrupt_file(tmp_path, monkeypatch):
    from ui.utils import storage

    corrupt = tmp_path / "bad_config.json"
    corrupt.write_text("{corrupt")
    monkeypatch.setattr(storage, "LLM_CONFIG_PATH", str(corrupt))

    assert storage.load_llm_config() is None


def test_clear_static_json(tmp_path, monkeypatch):
    from ui.utils import storage

    target = tmp_path / "domain_analysis.json"
    target.write_text("{}")
    monkeypatch.setattr(storage, "STATIC_JSON_PATH", str(target))

    storage.clear_static_json()
    assert not target.exists()


def test_clear_static_json_noop_when_missing(tmp_path, monkeypatch):
    from ui.utils import storage

    monkeypatch.setattr(storage, "STATIC_JSON_PATH", str(tmp_path / "nope.json"))
    storage.clear_static_json()  # Should not raise


def test_ensure_drafts_dir_creates_directory(tmp_path):
    from ui.utils.storage import ensure_drafts_dir

    path = str(tmp_path / "new_drafts")
    result = ensure_drafts_dir(path)
    assert os.path.isdir(result)
    assert result == path


def test_ensure_drafts_dir_uses_default(monkeypatch):
    from ui.utils import storage

    monkeypatch.setattr(storage, "DRAFTS_DIR", "/tmp/test_drafts_default")
    result = storage.ensure_drafts_dir()
    assert result == "/tmp/test_drafts_default"


def test_get_manifest_path(tmp_path):
    from ui.utils.storage import get_manifest_path

    result = get_manifest_path(str(tmp_path))
    assert result == os.path.join(str(tmp_path), "manifest.json")


def test_get_manifest_path_uses_default(monkeypatch):
    from ui.utils import storage

    monkeypatch.setattr(storage, "DRAFTS_DIR", "/tmp/drafts_test")
    result = storage.get_manifest_path()
    assert result == "/tmp/drafts_test/manifest.json"

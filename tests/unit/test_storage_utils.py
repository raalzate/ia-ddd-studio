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


def test_clear_cache_dir_removes_files_and_subdirs(tmp_path):
    from ui.utils.storage import clear_cache_dir

    (tmp_path / "a.cache.json").write_text("{}")
    (tmp_path / "b.json").write_text("{}")
    sub = tmp_path / "nested"
    sub.mkdir()
    (sub / "x.json").write_text("{}")

    removed = clear_cache_dir(str(tmp_path))
    assert removed == 3
    assert list(tmp_path.iterdir()) == []


def test_clear_cache_dir_noop_when_missing(tmp_path):
    from ui.utils.storage import clear_cache_dir

    missing = str(tmp_path / "nope")
    assert clear_cache_dir(missing) == 0


def test_clear_drafts_dir_removes_files(tmp_path):
    from ui.utils.storage import clear_drafts_dir

    (tmp_path / "d1.json").write_text("{}")
    (tmp_path / "manifest.json").write_text("{}")

    removed = clear_drafts_dir(str(tmp_path))
    assert removed == 2
    assert list(tmp_path.iterdir()) == []


def test_clear_llm_config(tmp_path, monkeypatch):
    from ui.utils import storage

    target = tmp_path / "llm_config.json"
    target.write_text("{}")
    monkeypatch.setattr(storage, "LLM_CONFIG_PATH", str(target))

    storage.clear_llm_config()
    assert not target.exists()


def test_clear_all_data_wipes_everything_except_llm_config(tmp_path, monkeypatch):
    from ui.utils import storage

    static_json = tmp_path / "domain_analysis.json"
    static_json.write_text("{}")
    llm_config = tmp_path / "llm_config.json"
    llm_config.write_text("{}")
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    (cache_dir / "a.json").write_text("{}")
    drafts_dir = tmp_path / "drafts"
    drafts_dir.mkdir()
    (drafts_dir / "d.json").write_text("{}")

    monkeypatch.setattr(storage, "STATIC_JSON_PATH", str(static_json))
    monkeypatch.setattr(storage, "LLM_CONFIG_PATH", str(llm_config))
    monkeypatch.setattr(storage, "CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(storage, "DRAFTS_DIR", str(drafts_dir))

    counts = storage.clear_all_data(include_llm_config=False)

    assert counts == {"static": 1, "cache": 1, "drafts": 1, "llm_config": 0}
    assert not static_json.exists()
    assert llm_config.exists()  # preserved
    assert list(cache_dir.iterdir()) == []
    assert list(drafts_dir.iterdir()) == []


def test_clear_all_data_includes_llm_config_when_requested(tmp_path, monkeypatch):
    from ui.utils import storage

    static_json = tmp_path / "domain_analysis.json"
    static_json.write_text("{}")
    llm_config = tmp_path / "llm_config.json"
    llm_config.write_text("{}")
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    drafts_dir = tmp_path / "drafts"
    drafts_dir.mkdir()

    monkeypatch.setattr(storage, "STATIC_JSON_PATH", str(static_json))
    monkeypatch.setattr(storage, "LLM_CONFIG_PATH", str(llm_config))
    monkeypatch.setattr(storage, "CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(storage, "DRAFTS_DIR", str(drafts_dir))

    counts = storage.clear_all_data(include_llm_config=True)

    assert counts["llm_config"] == 1
    assert not llm_config.exists()

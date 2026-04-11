"""Contract tests: import direction enforcement across layers.

Scans import statements to detect cross-layer violations:
- src/domain/ must not import external libs (except pydantic, stdlib)
- src/application/ must not import UI modules
- src/infra/ must not import src/ui/

[TS-002, TS-003]
"""

import ast
import pathlib

import pytest

SRC_ROOT = pathlib.Path("src")

ALLOWED_DOMAIN_IMPORTS = {
    "pydantic",
    "pydantic_core",
    "typing",
    "typing_extensions",
    "datetime",
    "dataclasses",
    "abc",
    "enum",
    "collections",
    "__future__",
    "domain",
    "models",
    "hashlib",
    "uuid",
}

UI_MODULES = {"streamlit", "st", "streamlit_agraph"}


def _collect_python_files(directory: pathlib.Path) -> list[pathlib.Path]:
    return list(directory.rglob("*.py"))


def _extract_imports(filepath: pathlib.Path) -> list[str]:
    """Extract all top-level import module names from a Python file."""
    source = filepath.read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module.split(".")[0])
    return modules


class TestDomainLayerImports:
    """src/domain/ must import no external libs beyond pydantic and stdlib."""

    @pytest.mark.parametrize("py_file", _collect_python_files(SRC_ROOT / "domain"), ids=str)
    def test_domain_has_no_external_imports(self, py_file: pathlib.Path):
        imports = _extract_imports(py_file)
        for imp in imports:
            py_file.read_text()
            # Check full dotted imports too
            pass
        # Re-parse for full module paths
        source = py_file.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root in ALLOWED_DOMAIN_IMPORTS, f"{py_file}: domain imports forbidden module '{alias.name}'"
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                assert root in ALLOWED_DOMAIN_IMPORTS, f"{py_file}: domain imports forbidden module '{node.module}'"


class TestApplicationLayerImports:
    """src/application/ must not import UI modules."""

    @pytest.mark.parametrize("py_file", _collect_python_files(SRC_ROOT / "application"), ids=str)
    def test_application_has_no_ui_imports(self, py_file: pathlib.Path):
        imports = _extract_imports(py_file)
        for imp in imports:
            assert imp not in UI_MODULES, f"{py_file}: application layer imports UI module '{imp}'"
        # Also check for src.ui imports
        source = py_file.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("ui.") and node.module != "ui", (
                    f"{py_file}: application layer imports from '{node.module}'"
                )


class TestInfraLayerImports:
    """src/infra/ must not import src/ui/."""

    @pytest.mark.parametrize("py_file", _collect_python_files(SRC_ROOT / "infra"), ids=str)
    def test_infra_has_no_ui_imports(self, py_file: pathlib.Path):
        imports = _extract_imports(py_file)
        for imp in imports:
            assert imp not in UI_MODULES, f"{py_file}: infra layer imports UI module '{imp}'"
        source = py_file.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("ui.") and node.module != "ui", (
                    f"{py_file}: infra layer imports from '{node.module}'"
                )

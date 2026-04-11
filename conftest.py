"""Root conftest: add src/ to sys.path so tests can import without 'src.' prefix."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Skip BDD test files whose .feature file is missing (specs/ is not tracked in git).
_UNIT_DIR = Path(__file__).resolve().parent / "tests" / "unit"
_SCENARIOS_RE = re.compile(r'scenarios\(["\'](.+?\.feature)["\']\)')

collect_ignore: list[str] = []
for _bdd_file in sorted(_UNIT_DIR.glob("test_bdd_*.py")):
    _match = _SCENARIOS_RE.search(_bdd_file.read_text())
    if _match:
        _feature = (_UNIT_DIR / _match.group(1)).resolve()
        if not _feature.exists():
            collect_ignore.append(str(_bdd_file))

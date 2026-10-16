"""Static checks of examples/ — they run against the live API, so CI can't execute them.

Each example must compile, follow the shared layout (async main() + __main__ guard), end with
a real "Expected output" block, and be listed in examples/README.md and docs/examples.md.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLES = sorted(EXAMPLES_DIR.glob("[0-9][0-9]_*.py"))


def test_examples_exist() -> None:
    assert EXAMPLES


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_layout(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    assert ast.get_docstring(tree), "module docstring explaining the example is missing"
    assert any(
        isinstance(node, ast.AsyncFunctionDef) and node.name == "main" for node in tree.body
    ), "async def main() is missing"
    assert 'if __name__ == "__main__":\n    asyncio.run(main())' in source
    assert re.search(
        r"^# Expected output \(real run against the live API, \d{4}-\d{2}-\d{2}\):\n#\n# \S",
        source,
        flags=re.MULTILINE,
    ), "the Expected output block is missing or empty"


def test_examples_readme_lists_every_example() -> None:
    readme = (EXAMPLES_DIR / "README.md").read_text(encoding="utf-8")
    for path in EXAMPLES:
        assert f"]({path.name})" in readme, f"{path.name} is not linked from examples/README.md"


def test_docs_examples_page_lists_every_example() -> None:
    page = (EXAMPLES_DIR.parent / "docs" / "examples.md").read_text(encoding="utf-8")
    for path in EXAMPLES:
        link = f"/blob/main/examples/{path.name})"
        assert link in page, f"{path.name} is not linked from docs/examples.md"

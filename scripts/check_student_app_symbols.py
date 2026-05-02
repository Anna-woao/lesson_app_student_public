from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDENT_APP = ROOT / "student_app.py"

IGNORED_BUILTINS = {
    "Exception",
    "False",
    "None",
    "True",
    "dict",
    "float",
    "int",
    "len",
    "list",
    "next",
    "range",
    "set",
    "sorted",
    "str",
}


def _public_python_files() -> list[Path]:
    files = list(ROOT.glob("*.py"))
    files.extend((ROOT / "scripts").glob("*.py"))
    return sorted(files)


def main() -> None:
    for path in _public_python_files():
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")

    source = STUDENT_APP.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(STUDENT_APP))

    defined = set()
    imported = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            defined.add(node.name)
        elif isinstance(node, ast.Import):
            imported.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(alias.asname or alias.name for alias in node.names)

    available = defined | imported
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    required_render_symbols = {name for name in called if name.startswith("_render")}
    missing = sorted(required_render_symbols - available - IGNORED_BUILTINS)
    if missing:
        raise SystemExit("student_app.py calls missing render symbols: " + ", ".join(missing))

    print("student app syntax and render symbol contract ok")


if __name__ == "__main__":
    main()

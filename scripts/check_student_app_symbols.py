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


def _local_module_path(module_name: str) -> Path | None:
    if not module_name or module_name.startswith("."):
        return None
    module_path = ROOT.joinpath(*module_name.split(".")).with_suffix(".py")
    if module_path.exists():
        return module_path
    package_init = ROOT.joinpath(*module_name.split("."), "__init__.py")
    if package_init.exists():
        return package_init
    return None


def _top_level_exports(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    exports: set[str] = set()
    explicit_all: set[str] | None = None

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            exports.add(node.name)
        elif isinstance(node, ast.Import):
            exports.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            exports.update(alias.asname or alias.name for alias in node.names if alias.name != "*")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    exports.add(target.id)
                    if target.id == "__all__" and isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                        explicit_all = {
                            item.value
                            for item in node.value.elts
                            if isinstance(item, ast.Constant) and isinstance(item.value, str)
                        }
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            exports.add(node.target.id)

    if explicit_all is not None:
        return explicit_all
    return {name for name in exports if not name.startswith("_")}


def _validate_local_imports(path: Path, tree: ast.AST) -> list[str]:
    missing: list[str] = []
    export_cache: dict[Path, set[str]] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level != 0 or not node.module:
            continue
        module_path = _local_module_path(node.module)
        if module_path is None:
            continue
        exports = export_cache.setdefault(module_path, _top_level_exports(module_path))
        for alias in node.names:
            if alias.name == "*":
                continue
            if alias.name not in exports:
                rel_path = path.relative_to(ROOT)
                rel_module_path = module_path.relative_to(ROOT)
                missing.append(f"{rel_path}: from {node.module} import {alias.name} missing in {rel_module_path}")

    return missing


def main() -> None:
    for path in _public_python_files():
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        tree = ast.parse(source, filename=str(path))
        missing_imports = _validate_local_imports(path, tree)
        if missing_imports:
            raise SystemExit("local import contract failed:\n" + "\n".join(missing_imports))

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

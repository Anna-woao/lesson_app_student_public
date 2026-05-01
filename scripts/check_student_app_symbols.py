from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDENT_APP = ROOT / "student_app.py"

REQUIRED_SYMBOLS = {
    "_render_login",
    "_render_logged_in_header",
    "_render_dashboard_styles",
    "_render_top_navigation",
    "_render_page_hero",
    "_render_page_quick_actions",
    "_render_welcome_section",
    "_render_primary_task_section",
    "_render_light_status_section",
    "_render_task_pool_section",
    "_render_section_focus_badge",
    "_render_focus_hint",
    "_render_profile_page",
    "_render_test_feedback_blocks",
}


def main() -> None:
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
    missing = sorted(REQUIRED_SYMBOLS - available)
    if missing:
        raise SystemExit("student_app.py missing required symbols: " + ", ".join(missing))

    print("student_app.py required symbols ok")


if __name__ == "__main__":
    main()

"""Compatibility exports for old student-app imports.

Printable lesson HTML rendering now lives in lesson_html_renderer.py so the
teacher and student apps share one implementation.
"""

from lesson_html_renderer import *  # noqa: F401,F403

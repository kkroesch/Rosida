"""Zentrale, über QSettings überschreibbare Einstellungen."""

from PySide6.QtCore import QSettings


MARKDOWN_CSS_KEY = "render/markdown_css"

# Qt-Rich-Text versteht nur eine Teilmenge von CSS 2.1, siehe
# https://doc.qt.io/qt-6/richtext-html-subset.html
DEFAULT_MARKDOWN_CSS = """
body, p, li, div, td, th {
    font-family: 'CMU Serif', serif;
    font-size: 16pt;
    color: #334155;
}
p { line-height: 8px; -qt-line-height-type: line-distance; margin-top: 4px; margin-bottom: 8px; }

h1, h2, h3, h4 {
    font-family: 'CMU Sans Serif', sans-serif;
    font-weight: bold;
    color: #0f172a;
}
h1 { font-size: 22pt; margin-top: 18px; margin-bottom: 6px; }
h2 { font-size: 18pt; margin-top: 14px; margin-bottom: 4px; }
h3 { font-size: 16pt; color: #334155; }
h4 { font-size: 16pt; font-style: italic; color: #334155; }

blockquote {
    font-family: 'CMU Concrete', serif;
    font-style: italic;
    color: #64748b;
    margin: 10px 0 10px 12px;
    padding-left: 12px;
}

code, pre {
    font-family: 'CMU Typewriter Text', monospace;
    font-size: 13pt;
    color: #0f172a;
    background-color: #f1f5f9;
}

table { border-collapse: collapse; margin: 8px 0; }
td, th { border: 1px solid #cbd5e1; padding: 2px 8px; }
th { font-weight: bold; background-color: #f1f5f9; }

.math-block { margin: 14px 0; }
.math-error { color: #dc2626; background-color: #fee2e2; }

.figure { margin: 10px 0 12px 0; }
.caption { font-size: 13pt; font-style: italic; color: #64748b; }

.callout-title-note, .callout-title-tip, .callout-title-warning,
.callout-title-important, .callout-title-caution { font-weight: bold; }
.callout-note { background-color: #eff6ff; }
.callout-title-note { color: #2563eb; }
.callout-tip { background-color: #f0fdf4; }
.callout-title-tip { color: #16a34a; }
.callout-warning, .callout-important { background-color: #fffbeb; }
.callout-title-warning, .callout-title-important { color: #d97706; }
.callout-caution { background-color: #fef2f2; }
.callout-title-caution { color: #dc2626; }
"""


def markdown_css() -> str:
    """Stylesheet für gerenderte Markdown-Zellen; Default, solange nichts gespeichert ist."""
    return str(QSettings().value(MARKDOWN_CSS_KEY, DEFAULT_MARKDOWN_CSS))

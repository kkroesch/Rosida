"""Tests für den Markdown-Renderer der Textzellen (widgets/math_text.py)."""

import markdown

from widgets.math_text import (
    MathTextBrowser,
    _RosidaExtension,
    render_markdown_with_math,
)


def _to_html(text: str) -> str:
    """Rendert ohne Qt-Browser; Formeln werden als Marker statt als Bild eingesetzt."""
    render_math = lambda latex, block: f"<span>MATH[{latex}|{block}]</span>"
    return markdown.markdown(
        text, extensions=["extra", "sane_lists", _RosidaExtension(render_math)]
    )


def test_math_is_protected_from_markdown():
    html = _to_html(r"Text $a_1 * b_2 * c$ und **fett**")
    assert "MATH[a_1 * b_2 * c|False]" in html
    assert "<strong>fett</strong>" in html


def test_block_math():
    html = _to_html("Vorher\n\n$$\n\\int_0^1 x\\,dx\n$$\n\nNachher")
    assert "MATH[\\int_0^1 x\\,dx|True]" in html


def test_dollar_inside_code_is_not_math():
    html = _to_html("`$x$`\n\n```\n$y$\n```")
    assert "MATH" not in html


def test_callout_with_heading_title():
    html = _to_html("::: {.callout-warning}\n## Achtung\nText mit $x$\n:::")
    assert 'class="callout-warning"' in html
    assert '<p class="callout-title-warning">Achtung</p>' in html
    assert "<h2>" not in html
    assert "MATH[x|False]" in html


def test_callout_title_attribute_and_default():
    assert "Tipp</p>" in _to_html('::: {.callout-tip title="Tipp"}\nX\n:::')
    assert "Note</p>" in _to_html("::: {.callout-note}\nX\n:::")


def test_figure_with_quarto_id():
    html = _to_html("![Eine Abbildung](bild.png){#fig-1}")
    assert 'class="figure"' in html
    assert 'id="fig-1"' in html
    assert '<p align="center" class="caption">Eine Abbildung</p>' in html
    assert "{#fig-1}" not in html


def test_render_into_browser(qtbot):
    browser = MathTextBrowser()
    qtbot.addWidget(browser)
    render_markdown_with_math("# Titel\n\nFormel $x^2$", browser)
    assert "Titel" in browser.toPlainText()
    assert len(browser._resources) == 1

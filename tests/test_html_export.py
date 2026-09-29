"""HTML-Export mit KaTeX."""

import re

import sympy as sp


def _export(win, tmp_path, wait_idle, frontmatter=""):
  win.doc.frontmatter_cell.editor.setPlainText(frontmatter)
  wait_idle(win.doc)
  out = tmp_path / "out.html"
  win.doc.export_html(str(out))
  return out.read_text(encoding="utf-8")


def test_katex_and_math_markup(rosida_win, tmp_path, wait_idle):
  doc = rosida_win.doc
  doc.cells[0].editor.setPlainText("Ungleichung $a < b$ und\n\n$$\\frac{1}{2}$$")

  page = _export(rosida_win, tmp_path, wait_idle)

  assert re.search(r'<script defer src="https://cdn\.jsdelivr\.net/npm/katex@[\d.]+/dist/katex\.min\.js" integrity="sha384-', page)
  assert '<span class="math inline">a &lt; b</span>' in page
  assert '<div class="math display">\\frac{1}{2}</div>' in page
  assert "@font-face { font-family: 'CMU Serif'" in page


def test_python_results_and_errors(rosida_win, tmp_path, wait_idle):
  doc = rosida_win.doc
  rosida_win.namespace["sp"] = sp
  ok = doc.cells[0]
  ok.set_mode("python")
  ok.editor.setPlainText("print('hallo')\nsp.sqrt(8)")
  ok.render()
  bad = doc.insert_cell(mode="python", initial_text="1/0")
  bad.render()

  page = _export(rosida_win, tmp_path, wait_idle)

  assert '<pre class="stdout">hallo</pre>' in page
  assert '<div class="math display">2 \\sqrt{2}</div>' in page
  assert '<pre class="stdout error">ZeroDivisionError: division by zero</pre>' in page


def test_templates_figures_and_header(rosida_win, tmp_path, wait_idle):
  doc = rosida_win.doc
  rosida_win.namespace["n"] = 7
  rosida_win.current_filepath = "docs/example.md"  # Bilder relativ zu docs/
  doc.cells[0].editor.setPlainText("n ist {{ n }}")
  doc.insert_cell(mode="markdown", initial_text="![Abbildung](assets/fig_1.svg){#fig-1}")

  page = _export(
    rosida_win, tmp_path, wait_idle,
    frontmatter='title: "Pendel"\ndate: 2024-04-25\nauthors:\n  - name: "Karsten"',
  )

  assert "<title>Pendel</title>" in page
  assert '<p class="meta">Karsten · 2024-04-25</p>' in page
  assert "n ist 7" in page
  assert 'src="data:image/svg+xml;base64,' in page
  assert '<p align="center" class="caption">Abbildung</p>' in page


def test_code_is_highlighted_and_copyable(rosida_win, tmp_path, wait_idle):
  doc = rosida_win.doc
  cell = doc.cells[0]
  cell.set_mode("python")
  cell.editor.setPlainText("def f(x):\n    return x < 2")
  cell.render()
  doc.insert_cell(mode="markdown", initial_text="Text\n\n```python\nimport sympy\n```")

  page = _export(rosida_win, tmp_path, wait_idle)

  assert page.count('<div class="highlight">') == 2
  assert '<span class="k">def</span>' in page  # Python-Zelle
  assert '<span class="kn">import</span>' in page  # Codeblock in Textzelle
  assert "&lt;" in page and "x < 2" not in page  # HTML-sicher escaped
  assert "navigator.clipboard.writeText" in page
  assert ".highlight .k {" in page  # Pygments-Farben eingebettet

"""Formelsatz mit ziamath und Vektor-Ausgabe im PDF."""

import sympy as sp

from widgets.math_svg import _svg_shapes, latex_to_svg, svg_to_qimage


def test_latex_constructs_mathtext_cannot_handle():
  x = sp.symbols("x")
  for latex in (
    sp.latex(sp.Matrix([[1, x], [x**2, sp.sqrt(x)]])),
    r"\begin{aligned} a &= b \\ c &= d \end{aligned}",
    r"f(x) = \begin{cases} 1 & x > 0 \\ 0 & \text{sonst} \end{cases}",
  ):
    math = latex_to_svg(latex, 21.0, True, "#1e293b")
    assert math.width > 0 and math.ascent > 0
    assert _svg_shapes(math.svg)[1], latex


def test_baseline_metrics():
  plain = latex_to_svg("x", 21.0, False, "#000000")
  subscript = latex_to_svg("x_1", 21.0, False, "#000000")
  assert subscript.descent > plain.descent


def test_rule_uses_formula_color():
  math = latex_to_svg(r"\frac{1}{2}", 21.0, False, "#1e293b")
  assert b'fill="black"' not in math.svg


def test_svg_to_qimage(qtbot):
  img = svg_to_qimage(latex_to_svg("E = mc^2", 21.0, False, "#000000"))
  assert not img.isNull()
  assert img.devicePixelRatio() == 2.0


def test_pdf_export_has_vector_formulas(rosida_win, tmp_path):
  pymupdf = __import__("pytest").importorskip("pymupdf")
  doc = rosida_win.doc
  doc.cells[0].editor.setPlainText("Formel $E = mc^2$")
  pdf = tmp_path / "out.pdf"

  doc.export_pdf(str(pdf))

  page = pymupdf.open(pdf)[0]
  assert page.get_images() == []
  fills = [d for d in page.get_drawings() if d["type"] == "f"]
  # Eine Füllung pro Glyphe (E, =, m, c, 2) – keine zusätzlichen Konturen.
  assert len(fills) == 5

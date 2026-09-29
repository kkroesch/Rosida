"""Formelsatz mit ziamath: LaTeX -> SVG, eingebettet als Vektor-Objekt in QTextDocuments.

Formeln werden nicht als Rasterbild, sondern als eigenes Text-Objekt in das
Dokument gesetzt, das beim Zeichnen die Glyphen-Pfade direkt über den QPainter
füllt. Dadurch bleiben sie im PDF-Export Vektorgrafik und sitzen auf der
Grundlinie des umgebenden Textes.

Das SVG wird bewusst nicht mit QSvgRenderer gezeichnet: Der startet mit einem
Stift ohne Pinsel, den Qts PDF-Engine dennoch als Kontur ausgibt, wodurch jede
Glyphe im PDF fett wird. ziamath erzeugt nur <path> (M/L/Q/Z, absolut) und
<rect>, das lässt sich direkt in QPainterPaths übersetzen.
"""

from dataclasses import dataclass
from functools import lru_cache
import re

import ziamath as zm

from PySide6.QtCore import QByteArray, QPointF, QRectF, QSizeF, Qt
from PySide6.QtGui import (
    QColor,
    QFontMetricsF,
    QImage,
    QPainter,
    QPainterPath,
    QPyTextObject,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
)

# SVG 1.1 schreibt jede Glyphe als eigenen <path> statt <symbol>/<use>.
zm.config.svg2 = False

MATH_OBJECT_TYPE = QTextFormat.ObjectTypes.UserObject + 1
_SVG = QTextFormat.Property.UserProperty + 1
_WIDTH = QTextFormat.Property.UserProperty + 2
_ASCENT = QTextFormat.Property.UserProperty + 3
_DESCENT = QTextFormat.Property.UserProperty + 4

_VIEWBOX_RE = re.compile(r'viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"')
_SHAPE_RE = re.compile(r"<(path|rect)\b([^>]*)>")
_ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
_PATH_TOKEN_RE = re.compile(r"[MLQZ]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?")


@dataclass(frozen=True)
class MathSvg:
    """Gerenderte Formel; Maße in Pixeln, ascent/descent relativ zur Grundlinie."""

    svg: bytes
    width: float
    ascent: float
    descent: float


def _strip_dollars(expr: str) -> str:
    expr = expr.strip()
    while expr.startswith("$") and expr.endswith("$") and len(expr) >= 2:
        expr = expr[1:-1].strip()
    return expr


@lru_cache(maxsize=512)
def latex_to_svg(latex: str, size_px: float, display: bool, color: str) -> MathSvg:
    """Renders LaTeX with ziamath; raises on syntax ziamath does not understand."""
    math = zm.Latex(
        _strip_dollars(latex), size=size_px, inline=not display, color=color
    )
    # Bruch-/Wurzelstriche kommen von ziamath immer schwarz.
    svg = math.svg().replace('fill="black"', f'fill="{color}"')
    m = _VIEWBOX_RE.search(svg)
    if not m:
        raise ValueError("SVG ohne viewBox")
    _x, y, w, h = (float(v) for v in m.groups())
    # SVG-Ursprung liegt auf der Grundlinie: y ist die (negative) Oberkante.
    return MathSvg(svg.encode(), w, -y, h + y)


def _parse_path(d: str) -> QPainterPath:
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)  # Font-Konturen: nonzero
    tokens = _PATH_TOKEN_RE.findall(d)
    i = 0

    def point() -> QPointF:
        nonlocal i
        i += 2
        return QPointF(float(tokens[i - 2]), float(tokens[i - 1]))

    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        if cmd == "M":
            path.moveTo(point())
        elif cmd == "L":
            path.lineTo(point())
        elif cmd == "Q":
            ctrl = point()
            path.quadTo(ctrl, point())
        elif cmd == "Z":
            path.closeSubpath()
        else:
            raise ValueError(f"Unerwarteter SVG-Pfadbefehl: {cmd}")
    return path


@lru_cache(maxsize=512)
def _svg_shapes(svg: bytes) -> tuple[QPointF, tuple[tuple[QPainterPath, QColor], ...]]:
    """Returns the viewBox origin and the filled shapes of a ziamath SVG."""
    text = svg.decode()
    x, y, *_ = (float(v) for v in _VIEWBOX_RE.search(text).groups())
    shapes = []
    for tag, attr_text in _SHAPE_RE.findall(text):
        attrs = dict(_ATTR_RE.findall(attr_text))
        if tag == "path":
            path = _parse_path(attrs["d"])
        else:
            path = QPainterPath()
            path.addRect(
                QRectF(
                    float(attrs.get("x", 0)),
                    float(attrs.get("y", 0)),
                    float(attrs["width"]),
                    float(attrs["height"]),
                )
            )
        shapes.append((path, QColor(attrs.get("fill", "black"))))
    return QPointF(x, y), tuple(shapes)


def _draw_svg(painter: QPainter, svg: bytes, target: QRectF, width: float) -> None:
    """Fills the formula shapes into target (width = unscaled SVG width)."""
    origin, shapes = _svg_shapes(svg)
    scale = target.width() / width if width else 1.0
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(target.topLeft())
    painter.scale(scale, scale)
    painter.translate(-origin)
    for path, color in shapes:
        painter.fillPath(path, color)
    painter.restore()


def svg_to_qimage(math: MathSvg, device_pixel_ratio: float = 2.0) -> QImage:
    """Rasterises a formula for widgets that cannot host text objects (e.g. QLabel)."""
    w, h = math.width, math.ascent + math.descent
    img = QImage(
        max(1, round(w * device_pixel_ratio)),
        max(1, round(h * device_pixel_ratio)),
        QImage.Format.Format_ARGB32_Premultiplied,
    )
    img.fill(0)
    painter = QPainter(img)
    _draw_svg(painter, math.svg, QRectF(0, 0, img.width(), img.height()), w)
    painter.end()
    img.setDevicePixelRatio(device_pixel_ratio)
    return img


class _MathObjectHandler(QPyTextObject):
    """Draws formula objects so that the formula baseline sits on the text baseline.

    Qt only knows two useful placements for inline objects: AlignBaseline puts
    the object bottom one font descent below the baseline, AlignMiddle centres
    it around half the x-height above the baseline. The SVG is padded to match
    whichever was chosen in embed_math_objects().
    """

    @staticmethod
    def _geometry(
        doc: QTextDocument, fmt: QTextFormat
    ) -> tuple[float, float, float, float, float]:
        """Returns (width, height, top padding, ascent, descent) in device units.

        Beim Drucken layoutet Qt in Geräte-Pixeln des Druckers; die in
        Bildschirm-Pixeln (96 dpi) gemessene Formel wird deshalb skaliert,
        so wie es Qt auch für Bilder macht.
        """
        device = doc.documentLayout().paintDevice()
        scale = device.logicalDpiY() / 96 if device else 1.0
        width = fmt.doubleProperty(_WIDTH) * scale
        ascent = fmt.doubleProperty(_ASCENT) * scale
        descent = fmt.doubleProperty(_DESCENT) * scale
        char_fmt = fmt.toCharFormat()
        font = char_fmt.font()
        metrics = QFontMetricsF(font, device) if device else QFontMetricsF(font)
        if (
            char_fmt.verticalAlignment()
            == QTextCharFormat.VerticalAlignment.AlignBaseline
        ):
            return width, ascent + metrics.descent(), 0.0, ascent, descent
        half_x = metrics.xHeight() / 2
        height = max(2 * ascent - half_x, 2 * descent + half_x)
        top = (height + half_x) / 2 - ascent
        return width, height, top, ascent, descent

    def intrinsicSize(self, doc, pos_in_document, fmt):
        width, height, *_ = self._geometry(doc, fmt)
        return QSizeF(width, height)

    def drawObject(self, painter, rect, doc, pos_in_document, fmt):
        width, _height, top, ascent, descent = self._geometry(doc, fmt)
        svg = fmt.property(_SVG)
        svg = svg.data() if isinstance(svg, QByteArray) else bytes(svg)
        target = QRectF(rect.x(), rect.y() + top, width, ascent + descent)
        _draw_svg(painter, svg, target, fmt.doubleProperty(_WIDTH))


_handler: _MathObjectHandler | None = None


def embed_math_objects(doc: QTextDocument, formulas: dict[str, MathSvg]) -> None:
    """Replaces <img src="name"> placeholders in doc by vector formula objects."""
    global _handler
    if _handler is None:
        _handler = _MathObjectHandler()
    doc.documentLayout().registerHandler(MATH_OBJECT_TYPE, _handler)

    hits = []
    block = doc.begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            fmt = frag.charFormat()
            if fmt.isImageFormat():
                name = fmt.toImageFormat().name()
                if name in formulas:
                    hits.append((frag.position(), frag.length(), fmt, formulas[name]))
            it += 1
        block = block.next()

    cursor = QTextCursor(doc)
    for pos, length, img_fmt, math in reversed(hits):
        fmt = QTextCharFormat(img_fmt)  # übernimmt Schrift des umgebenden Textes
        fmt.setObjectType(MATH_OBJECT_TYPE)
        # Ohne tiefe Unterlängen reicht AlignBaseline (keine zusätzliche Zeilenhöhe).
        fits = math.descent <= QFontMetricsF(fmt.font()).descent()
        fmt.setVerticalAlignment(
            QTextCharFormat.VerticalAlignment.AlignBaseline
            if fits
            else QTextCharFormat.VerticalAlignment.AlignMiddle
        )
        fmt.setProperty(_SVG, QByteArray(math.svg))
        fmt.setProperty(_WIDTH, math.width)
        fmt.setProperty(_ASCENT, math.ascent)
        fmt.setProperty(_DESCENT, math.descent)
        cursor.setPosition(pos)
        cursor.setPosition(pos + length, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText("\ufffc", fmt)
